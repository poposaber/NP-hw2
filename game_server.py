from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
import socket
import threading

class GameServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 22345) -> None:
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.players: list[MessageFormatPasser] = []
        self.lock = threading.Lock()

    def start(self) -> None:
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Game server listening on {self.host}:{self.port}")
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Accepted connection from {addr}")
            passer = MessageFormatPasser(client_socket)
            with self.lock:
                self.players.append(passer)
            # Since this is 2-player game, after accepting 2 players, stop accepting more
            if len(self.players) >= 2:
                print("Two players connected, starting game session")
                threading.Thread(target=self.handle_game_session, args=(self.players[0], self.players[1])).start()

    def handle_game_session(self, player1: MessageFormatPasser, player2: MessageFormatPasser) -> None:
        pass