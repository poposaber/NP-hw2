# next objective: implement a queue for incoming player actions and process them in the game loop

from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
from game import Game
from queue import Queue
import socket
import threading
import time
import random


class GameServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 22345) -> None:
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.settimeout(1.0)  # 1 second timeout for accept
        self.game_thread: threading.Thread | None = None
        self.handle_player1_thread: threading.Thread | None = None
        self.handle_player2_thread: threading.Thread | None = None
        self.player1_passer: MessageFormatPasser | None = None
        self.player2_passer: MessageFormatPasser | None = None
        self.player1_username: str | None = None
        self.player2_username: str | None = None
        self.room_id: str | None = None
        self.lock = threading.Lock()
        self.seed = random.randint(0, 1000000)
        self.game = Game(seed=self.seed)
        self.action_queue: Queue = Queue()
        self.running = threading.Event()
        self.running.set()
        self.start_accepted_event = threading.Event()
        self.player1_ready = threading.Event()
        self.player2_ready = threading.Event()

    def wait_until_started(self) -> None:
        self.start_accepted_event.wait()

    def start(self) -> None:
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Game server listening on {self.host}:{self.port}")
        while self.running.is_set():
            try:
                self.start_accepted_event.set()
                client_socket, addr = self.server_socket.accept()
                print(f"Accepted connection from {addr}")
                passer = MessageFormatPasser(client_socket)
                arg_list = passer.receive_args(Protocols.ClientToGameServer.CONNECT)
                if not arg_list:
                    print("Failed to receive connection message")
                    client_socket.close()
                    continue
                connection_type = arg_list[2]
                if self.room_id is None:
                    self.room_id = arg_list[1]
                elif self.room_id != arg_list[1]:
                    print("Mismatched room ID, rejecting connection")
                    passer.send_args(Protocols.GameServerToPlayer.CONNECT_RESPONSE, Words.Result.FAILURE, {'message': 'Mismatched room ID'})
                    client_socket.close()
                    continue

                if connection_type == 'player':
                    with self.lock:
                        if self.player1_passer is not None and self.player2_passer is not None:
                            print("Maximum players connected, rejecting new connection")
                            passer.send_args(Protocols.GameServerToPlayer.CONNECT_RESPONSE, Words.Result.FAILURE, {'message': 'Game is full'})
                            client_socket.close()
                            continue
                        if self.player1_passer is None:
                            self.player1_passer = passer
                            self.player1_username = arg_list[0]
                            passer.send_args(Protocols.GameServerToPlayer.CONNECT_RESPONSE, Words.Result.SUCCESS, 'player1', self.seed, "random-uniform", {"drop_speed": 1.0})
                        else:
                            self.player2_passer = passer
                            self.player2_username = arg_list[0]
                            passer.send_args(Protocols.GameServerToPlayer.CONNECT_RESPONSE, Words.Result.SUCCESS, 'player2', self.seed, "random-uniform", {"drop_speed": 1.0})
                    print(f"Player connected: {addr}")
                    # Since this is 2-player game, after accepting 2 players, stop accepting more
                    if self.player1_passer is not None and self.player2_passer is not None:
                        print("Two players connected, starting game session")

                        self.game_thread = threading.Thread(target=self.handle_game_session)
                        self.game_thread.start()

                        self.handle_player1_thread = threading.Thread(target=self.handle_player, args=(self.player1_passer, "player1"))
                        self.handle_player1_thread.start()

                        self.handle_player2_thread = threading.Thread(target=self.handle_player, args=(self.player2_passer, "player2"))
                        self.handle_player2_thread.start()
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error accepting connections: {e}")
        print("Game server stopping acceptance of new connections.")
        self.running.clear()


    def handle_player(self, passer: MessageFormatPasser, player_id: str) -> None:
        try:
            while self.running.is_set():
                arg_list = passer.receive_args(Protocols.PlayerToGameServer.GAME_ACTION)
                if not arg_list:
                    print("Player disconnected")
                    with self.lock:
                        if player_id == "player1":
                            self.player1_passer = None
                        else:
                            self.player2_passer = None
                    break
                action, data = arg_list
                # Process player action
                self.action_queue.put((player_id, action, data))

                print(f"Received action from {player_id}: {action} with data: {data}")
                # Here you would update the game state based on the action
        except ConnectionResetError:
            print(f"{player_id} disconnected unexpectedly")
            with self.lock:
                if player_id == "player1":
                    self.player1_passer.close()
                    self.player1_passer = None
                else:
                    self.player2_passer.close()
                    self.player2_passer = None
        except Exception as e:
            print(f"Error handling {player_id}: {e}")
            with self.lock:
                if player_id == "player1":
                    self.player1_passer.close()
                    self.player1_passer = None
                else:
                    self.player2_passer.close()
                    self.player2_passer = None

    def handle_game_session(self) -> None:
        now = time.time()
        prev = now
        try:
            while not (self.player1_ready.is_set() and self.player2_ready.is_set()):
                player_id, action, data = self.action_queue.get()
                if action == Words.GameAction.READY:
                    if player_id == "player1":
                        self.player1_ready.set()
                        print("Player 1 is ready")
                    else:
                        self.player2_ready.set()
                        print("Player 2 is ready")
                        
                else:
                    print(f"Received non-ready action {action} from {player_id} before both players were ready, ignoring.")
                time.sleep(0.1)
            self.player1_passer.send_args(Protocols.GameServerToPlayer.GAME_STARTED,
                                          self.player1_username,
                                          self.player2_username,
                                          self.game.player1.health,
                                          self.game.tetris1.now_piece.type_name if self.game.tetris1.now_piece else None,
                                          [piece.type_name for piece in self.game.tetris1.next_piece_list],
                                          self.game.goal_score)
            self.player2_passer.send_args(Protocols.GameServerToPlayer.GAME_STARTED,
                                          self.player1_username,
                                          self.player2_username,
                                          self.game.player2.health,
                                          self.game.tetris2.now_piece.type_name if self.game.tetris2.now_piece else None,
                                          [piece.type_name for piece in self.game.tetris2.next_piece_list],
                                          self.game.goal_score)
            
            print("Both players are ready. Starting the game loop.")

            while self.running.is_set():
                # Process all queued actions
                while not self.action_queue.empty():
                    player_id, action, data = self.action_queue.get()
                    self.game.handle_player_action(player_id, action, data)

                now = time.time()
                delta_time = now - prev
                self.game.update(delta_time)
                prev = now
                # Send updated game state to both players
                state1 = {
                    'board': self.game.get_board_string("player1"),
                    'now_piece': self.game.tetris1.now_piece.shape if self.game.tetris1.now_piece else None,
                    'color': self.game.tetris1.now_piece.color if self.game.tetris1.now_piece else None,
                    'position': self.game.tetris1.now_piece.position if self.game.tetris1.now_piece else None,
                    'next_pieces': [piece.type_name for piece in self.game.tetris1.next_piece_list],
                    'score': self.game.player1.score,
                    'health': self.game.player1.health,
                    'revive_time': self.game.player1.revive_time,
                }
                state2 = {
                    'board': self.game.get_board_string("player2"),
                    'now_piece': self.game.tetris2.now_piece.shape if self.game.tetris2.now_piece else None,
                    'color': self.game.tetris2.now_piece.color if self.game.tetris2.now_piece else None,
                    'position': self.game.tetris2.now_piece.position if self.game.tetris2.now_piece else None,
                    'next_pieces': [piece.type_name for piece in self.game.tetris2.next_piece_list],
                    'score': self.game.player2.score,
                    'health': self.game.player2.health,
                    'revive_time': self.game.player2.revive_time,
                }
                data = {}
                if self.game.gameover:
                    data["game_over"] = True
                    data["winner"] = self.game.winner
                    self.running.clear()  # Stop the game loop
                with self.lock:
                    if self.player1_passer is not None:
                        self.player1_passer.send_args(Protocols.GameServerToPlayer.GAME_UPDATE, state1, state2, data)
                    if self.player2_passer is not None:
                        self.player2_passer.send_args(Protocols.GameServerToPlayer.GAME_UPDATE, state1, state2, data) # send same state to player2 for simplicity

                time.sleep(0.1)  # Sleep to limit update rate
        except Exception as e:
            print(f"Error in game session: {e}")

    def stop(self) -> None:
        self.running.clear()
        self.server_socket.close()
        if self.game_thread is not None:
            self.game_thread.join()
        if self.handle_player1_thread is not None:
            self.handle_player1_thread.join()
        if self.handle_player2_thread is not None:
            self.handle_player2_thread.join()
        with self.lock:
            if self.player1_passer is not None:
                self.player1_passer.close()
            if self.player2_passer is not None:
                self.player2_passer.close()
        print("Server shut down.")
