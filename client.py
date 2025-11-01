# next objective:
# 1. implement client-side handling of invitations: accept or decline.
# 2. tackle with prompt display after events are printed.

from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
from user_info import UserInfo
from tetris import Tetris
from game_window import GameWindow
import threading
import queue
import getpass
import sys
import os
import time

class Client:
    def __init__(self) -> None:
        self.host = ""
        self.lobby_msgfmt_passer = MessageFormatPasser(timeout=1.0)
        self.game_msgfmt_passer = MessageFormatPasser(timeout=1.0)
        self.temp_username: str | None = None
        self.info = UserInfo()
        self.listen_thread = threading.Thread(target=self.listen_for_messages)
        self.get_event_thread = threading.Thread(target=self.listen_for_events)
        self.listen_game_thread: threading.Thread | None = None
        self.shutdown_event = threading.Event()
        self.fatal_error_event = threading.Event()
        self.response_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.player_id: str | None = None
        self.game_connected = False
        self.game_window: GameWindow | None = None

    def print_prompt(self):
        print("\n\nCommands you can type:\n")
        if not self.info.name:
            print("register: register an account")
            print("login: log in an account")
            print("exit: exit the lobby server and close.\n\n")
            print("You are not logged in yet. Enter command: >>>>>>>>>> ", end="")
        else:
            print("logout: log out your account")
            if self.info.current_room_id is None:
                print("createroom: create a game room")
                print("joinroom: join a public game room")
                if self.info.users_inviting_me:
                    print("accept: accept an invitation to join a game room")
            else:
                print("invite: invite an online player to your current game room")
                print("leaveroom: leave the current game room")
                print("startgame: start the game (room owner only)")
                if self.game_connected:
                    print("play: play the game")
            
            print("exit: exit the lobby server and close.\n\n")
            print(f"{self.info.name}, enter command: >>>>>>>>>> ", end="")

    def register(self):
        try:
            username = ""
            password = ""
            while True:
                username = input("Enter desired username (or 'Ctrl+C' to cancel): ")
                # Send username to server to check availability
                self.send_to_lobby(Words.Command.CHECK_USERNAME, {Words.DataParamKey.USERNAME: username})
                response = self.get_response(timeout=5.0)
                if response is None:
                    print("No response from server. Registration failed.")
                    return
                responding_command, result, data = response
                if responding_command != Words.Command.CHECK_USERNAME:
                    print("Unexpected response from server. Registration failed.")
                    return
                
                if result == Words.Result.VALID:
                    #print("Registration successful.")
                    break
                elif result == Words.Result.INVALID:
                    print("Username already taken. Please try a different one.")
                else:
                    message = data.get(Words.DataParamKey.MESSAGE, "Registration failed.")
                    print(message)
                    return
                
            while True:
                password = getpass.getpass("Enter desired password (or 'Ctrl+C' to cancel): ")
                confirm_password = getpass.getpass("Confirm password: ")
                if password != confirm_password:
                    print("Passwords do not match. Please try again.")
                    continue

                self.send_to_lobby(Words.Command.REGISTER, {Words.DataParamKey.USERNAME: username, Words.DataParamKey.PASSWORD: password})
                response = self.get_response(timeout=5.0)
                if response is None:
                    print("No response from server. Registration failed.")
                    return
                responding_command, result, data = response
                if responding_command != Words.Command.REGISTER:
                    print("Unexpected response from server. Registration failed.")
                    return
                if result == Words.Result.SUCCESS:
                    print("Registration completed successfully.")
                    #self.info.name = username
                    return
        except Exception as e:
            print(f"Error during registration: {e}")

        except KeyboardInterrupt:
            print("\nRegistration cancelled.")
            return

    def login(self):
        try:
            while True:
                username = input("Enter username (or 'Ctrl+C' to cancel): ")
                password = getpass.getpass("Enter password (or 'Ctrl+C' to cancel): ")
                self.send_to_lobby(Words.Command.LOGIN, {Words.DataParamKey.USERNAME: username, Words.DataParamKey.PASSWORD: password})
                response = self.get_response(timeout=5.0)
                if response is None:
                    print("No response from server. Login failed.")
                    return
                responding_command, result, data = response
                if responding_command != Words.Command.LOGIN:
                    print("Unexpected response from server. Login failed.")
                    return
                if result == Words.Result.SUCCESS:
                    print("Login successful.")
                    self.info.name = username
                    break
                else:
                    message = data.get(Words.DataParamKey.MESSAGE, "Login failed.")
                    print(message)
                    continue
        except KeyboardInterrupt:
            print("\nLogin cancelled.")
            return
        except Exception as e:
            print(f"Error during login: {e}")

    def logout(self):
        try:
            self.send_to_lobby(Words.Command.LOGOUT, {})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Logout failed.")
                return
            responding_command, result, data = response
            if responding_command != Words.Command.LOGOUT:
                print("Unexpected response from server. Logout failed.")
                return
            if result == Words.Result.SUCCESS:
                print("Logout successful.")
                self.info.reset()
            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Logout failed.")
                print(message)
        except Exception as e:
            print(f"Error during logout: {e}")

    def create_room(self):
        try:
            privacy = ""
            while privacy not in ["public", "private"]:
                privacy = input("Enter room privacy ('public' or 'private', or press Ctrl+C to cancel): ").strip().lower()
                if privacy not in ["public", "private"]:
                    print("Invalid input. Please enter 'public' or 'private'.")
            self.send_to_lobby(Words.Command.CREATE_ROOM, {Words.DataParamKey.PRIVACY: privacy})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Create room failed.")
                return
            responding_command, result, data = response
            if responding_command != Words.Command.CREATE_ROOM:
                print("Unexpected response from server. Create room failed.")
                return
            if result == Words.Result.SUCCESS:
                room_id = data.get(Words.DataParamKey.ROOM_ID, "")
                print(f"Room created successfully. Room ID: {room_id}")
                self.info.current_room_id = room_id
                self.info.is_room_owner = True
            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Create room failed.")
                print(message)
        except KeyboardInterrupt:
            print("\nCreate room cancelled.")
            return
        except Exception as e:
            print(f"Error during create room: {e}")

    def leave_room(self):
        try:
            self.send_to_lobby(Words.Command.LEAVE_ROOM, {Words.DataParamKey.ROOM_ID: self.info.current_room_id})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Leave room failed.")
                return
            responding_command, result, data = response
            if responding_command != Words.Command.LEAVE_ROOM:
                print("Unexpected response from server. Leave room failed.")
                return
            if result == Words.Result.SUCCESS:
                print("Left room successfully.")
                self.info.current_room_id = None
                self.info.is_room_owner = False
            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Leave room failed.")
                print(message)
        except Exception as e:
            print(f"Error during leave room: {e}")

    def join_room(self):
        try:
            # first, get public room list from server
            self.send_to_lobby(Words.Command.CHECK_JOINABLE_ROOMS, {})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Join room failed.")
                return
            responding_command, result, data = response # expect data = {room_id: {room_info_dict}, ...}
            if responding_command != Words.Command.CHECK_JOINABLE_ROOMS:
                print("Unexpected response from server. Join room failed.")
                return
            if result == Words.Result.SUCCESS:
                public_rooms = data
                if not public_rooms:
                    print("No public rooms available.")
                    return
                print("Available public rooms:")
                print("Room ID\tOwner")
                for room_id, room_info in public_rooms.items():
                    owner = room_info.get(Words.DataParamKey.OWNER, "Unknown")
                    print(f"{room_id}\t{owner}")
                while True:
                    room_id = input("Enter the room ID to join (or 'Ctrl+C' to cancel): ")
                    if room_id not in public_rooms.keys():
                        print("Invalid room ID. Please try again.")
                        continue
                    self.send_to_lobby(Words.Command.JOIN_ROOM, {Words.DataParamKey.ROOM_ID: room_id})
                    response = self.get_response(timeout=5.0)
                    if response is None:
                        print("No response from server. Join room failed.")
                        return
                    responding_command, result, data = response
                    if responding_command != Words.Command.JOIN_ROOM:
                        print("Unexpected response from server. Join room failed.")
                        return
                    if result == Words.Result.SUCCESS:
                        print(f"Joined room {room_id} successfully.")
                        self.info.current_room_id = room_id
                        self.info.is_room_owner = False
                        self.info.users_inviting_me.clear()
                        break
                    else:
                        message = data.get(Words.DataParamKey.MESSAGE, "Join room failed.")
                        print(message)
                        self.info.current_room_id = None
                        self.info.is_room_owner = False

            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Join room failed.")
                print(message)
        except KeyboardInterrupt:
            print("\nJoin room cancelled.")
            return
        except Exception as e:
            print(f"Error during join room: {e}")

    def invite_player(self):
        try:
            self.send_to_lobby(Words.Command.CHECK_ONLINE_USERS, {})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Invite failed.")
                return
            responding_command, result, data = response # expect data = {users: user_list}
            if responding_command != Words.Command.CHECK_ONLINE_USERS:
                print("Unexpected response from server. Invite failed.")
                return
            if result == Words.Result.SUCCESS:
                online_users = data.get(Words.DataParamKey.USERS, [])
                try:
                    online_users.remove(self.info.name)  # Remove self from the list
                except ValueError:
                    pass
                if not online_users:
                    print("No online users available to invite.")
                    return
                print("Online users:")
                for num, user in enumerate(online_users, 1):
                    if user != self.info.name:
                        print(f"{num}. {user}")
            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Invite failed.")
                print(message)
                return
            # code checks to here
            invitee_username = ""
            while True:
                invitee_index = input("Enter the number of the user to invite (or 'Ctrl+C' to cancel): ")
                try:
                    invitee_index = int(invitee_index)
                    if invitee_index < 1 or invitee_index > len(online_users):
                        print("Invalid user number.")
                        continue
                    invitee_username = online_users[invitee_index - 1]
                    break
                except ValueError:
                    print("Invalid input. Please enter an integer.")
            
            self.send_to_lobby(Words.Command.INVITE_USER, {Words.DataParamKey.USERNAME: invitee_username})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Invite failed.")
                return
            responding_command, result, data = response
            if responding_command != Words.Command.INVITE_USER:
                print("Unexpected response from server. Invite failed.")
                return
            if result == Words.Result.SUCCESS:
                print("Invite sent successfully.")
            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Invite failed.")
                print(message)
        except KeyboardInterrupt:
            print("\nInvite cancelled.")
            return
        except Exception as e:
            print(f"Error during invite: {e}")

    def accept_invitation(self):
        print("You have invitations from the following users:")
        for i, inviter in enumerate(self.info.users_inviting_me, 1):
            print(f"{i}. {inviter}")
        while True:
            choice = input("Enter the number of the user whose invitation you want to accept (or 'Ctrl+C' to cancel): ")
            try:
                choice = int(choice)
                if choice < 1 or choice > len(self.info.users_inviting_me):
                    print("Invalid choice. Please try again.")
                    continue
                inviter_username = list(self.info.users_inviting_me)[choice - 1]
                self.info.users_inviting_me.remove(inviter_username)
                self.send_to_lobby(Words.Command.ACCEPT_INVITE, {Words.DataParamKey.USERNAME: inviter_username})
                response = self.get_response(timeout=5.0)
                if response is None:
                    print("No response from server. Accept invitation failed.")
                    return
                responding_command, result, data = response
                if responding_command != Words.Command.ACCEPT_INVITE:
                    print("Unexpected response from server. Accept invitation failed.")
                    return
                if result == Words.Result.SUCCESS:
                    print("Invitation accepted successfully.")
                    self.info.users_inviting_me.clear()
                    self.info.current_room_id = data.get(Words.DataParamKey.ROOM_ID)
                    break
                else:
                    message = data.get(Words.DataParamKey.MESSAGE, "Accept invitation failed.")
                    print(message)
                    return
            except ValueError:
                print("Invalid input. Please enter a number.")

    # def clear_stdin_buffer(self) -> None:
    #     """Best-effort 清除尚未按 Enter 的鍵盤輸入(Windows / POSIX)。"""
    #     try:
    #         if os.name == "nt":
    #             # Windows: FlushConsoleInputBuffer
    #             import ctypes
    #             STD_INPUT_HANDLE = -10
    #             h = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
    #             ctypes.windll.kernel32.FlushConsoleInputBuffer(h)
    #         else:
    #             # POSIX: tcflush on stdin
    #             import termios
    #             termios.tcflush(sys.stdin, termios.TCIFLUSH)
    #     except Exception:
    #         # fallback: consume pending chars on Windows console if possible
    #         try:
    #             if os.name == "nt":
    #                 import msvcrt
    #                 while msvcrt.kbhit():
    #                     msvcrt.getwch()
    #         except Exception:
    #             pass

    def start_game(self):
        try:
            self.send_to_lobby(Words.Command.START_GAME, {})
            response = self.get_response(timeout=5.0)
            if response is None:
                print("No response from server. Start game failed.")
                return
            responding_command, result, data = response
            if responding_command != Words.Command.START_GAME:
                print("Unexpected response from server. Start game failed.")
                return
            if result == Words.Result.SUCCESS:
                print("Game started successfully.")
            else:
                message = data.get(Words.DataParamKey.MESSAGE, "Start game failed.")
                print(message)
        except Exception as e:
            print(f"Error during start game: {e}")

    def play_game(self):
        print("playing game...")
        self.game_window = GameWindow(game_server_passer=self.game_msgfmt_passer, player_id=self.player_id)
        self.listen_game_thread = threading.Thread(target=self.listen_for_game_messages)
        self.listen_game_thread.start()
        time.sleep(0.2)  # give some time for the thread to start
        self.game_window.run()
        self.game_connected = False
        self.listen_game_thread.join()
        self.game_msgfmt_passer.close()
        self.game_msgfmt_passer = MessageFormatPasser(timeout=1.0)

    def listen_for_game_messages(self):
        player1_username, player2_username, player_health, now_piece, next_pieces, goal_score = self.game_msgfmt_passer.receive_args(Protocols.GameServerToPlayer.GAME_STARTED)
        self.game_window.init_player_info(player1_username, player2_username, player_health, now_piece, next_pieces, goal_score)
        while True:
            state1, state2, data = self.game_msgfmt_passer.receive_args(Protocols.GameServerToPlayer.GAME_UPDATE)
            with self.game_window.game_update_lock:
                self.game_window.game_update_temp['state1'] = state1
                self.game_window.game_update_temp['state2'] = state2
                self.game_window.game_update_temp['data'] = data
            if 'game_over' in data:
                break

    def get_input(self):
        while not self.shutdown_event.is_set():
            try:
                self.print_prompt()
                cmd = input().strip().lower()
                if not cmd:
                    print("Please enter a valid command.")
                    continue
                match cmd:
                    case "register":
                        if self.info.name:
                            print("Logged in users cannot register.")
                            continue
                        self.register()
                    case "login":
                        if self.info.name:
                            print("You are already logged in.")
                            continue
                        self.login()
                    case "logout":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        self.logout()
                    case "createroom":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if self.info.current_room_id is not None:
                            print("You are already in a room. Cannot create another room.")
                            continue
                        self.create_room()
                    case "leaveroom":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if self.info.current_room_id is None:
                            print("You are not in any room.")
                            continue
                        self.leave_room()
                    case "joinroom":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if self.info.current_room_id is not None:
                            print("You are already in a room. Cannot join another room.")
                            continue
                        self.join_room()
                    case "invite":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if self.info.current_room_id is None:
                            print("You are not in any room.")
                            continue
                        self.invite_player()
                    case "accept":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if not self.info.users_inviting_me:
                            print("You have no invitations to accept.")
                            continue
                        self.accept_invitation()
                    case "startgame":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if self.info.current_room_id is None:
                            print("You are not in any room.")
                            continue
                        if not self.info.is_room_owner:
                            print("Only the room owner can start the game.")
                            continue
                        self.start_game()
                    case "play":
                        if not self.info.name:
                            print("You are not logged in.")
                            continue
                        if self.info.current_room_id is None:
                            print("You are not in any room.")
                            continue
                        if not self.game_connected:
                            print("You are not connected to the game server.")
                            continue
                        self.play_game()
                    case "exit":
                        print("Exiting client.")
                        self.close()
                    case _:
                        print("Unknown command. Please try again.")
            except KeyboardInterrupt:
                print("Exiting client.")
                self.close()
            except Exception as e:
                print(f"Error getting input: {e}")

    def start(self, host: str = "127.0.0.1", port: int = 21354) -> None:
        self.host = host
        self.lobby_msgfmt_passer.connect(host, port)
        
        self.lobby_msgfmt_passer.send_args(Protocols.ConnectionToLobby.HANDSHAKE, Words.ConnectionType.CLIENT)
        result, message = self.lobby_msgfmt_passer.receive_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE)  # Wait for handshake response
        if result != Words.Result.CONFIRMED:
            raise ConnectionError(f"Handshake failed: {message}")
        self.listen_thread.start()
        self.get_event_thread.start()
        self.get_input()

    def close(self) -> None:
        self.shutdown_event.set()
        current = threading.current_thread()
        if self.listen_thread is not None and self.listen_thread.is_alive() and self.listen_thread is not current:
            self.listen_thread.join()
        if self.get_event_thread is not None and self.get_event_thread.is_alive() and self.get_event_thread is not current:
            self.get_event_thread.join()
        try:
            self.send_to_lobby(Words.Command.EXIT, {})
        except Exception:
            pass
        self.lobby_msgfmt_passer.close()
        self.game_msgfmt_passer.close()

    def send_to_lobby(self, command: str, params: dict) -> None:
        self.lobby_msgfmt_passer.send_args(Protocols.ClientToLobby.COMMAND, command, params)

    def listen_for_messages(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                msg = self.lobby_msgfmt_passer.receive_args(Protocols.LobbyToClient.MESSAGE)
                self.handle_message(msg)
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error listening for messages: {e}")
                # try:
                #     self.lobby_msgfmt_passer.close()
                # except Exception:
                #     pass
                # try:
                #     self.game_msgfmt_passer.close()
                # except Exception:
                #     pass
                self.shutdown_event.set()

    def listen_for_events(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                event_list = self.get_event(timeout=1.0)
                if event_list is not None:
                    event_type, data = event_list
                    print(f"Received event: {event_type} with data: {data}")
                    self.handle_event(event_type, data)
            except Exception as e:
                print(f"Error listening for events: {e}")
                self.fatal_error_event.set()

    def handle_event(self, event_type: str, data: dict) -> None:
        print(f"Handling event: {event_type} with data: {data}")
        # self.clear_stdin_buffer()
        match event_type:
            case Words.EventType.SERVER_SHUTDOWN:
                print("Server is shutting down. Closing client.")
                self.close()
            case Words.EventType.INVITATION_RECEIVED:
                inviter_username = data.get(Words.DataParamKey.USERNAME)
                self.info.users_inviting_me.add(inviter_username)
                print(f"Received invitation from {inviter_username}. Enter 'accept' to join the room or ignore to decline.")
                # Here you can add logic to accept or decline the invitation
            case Words.EventType.USER_JOINED:
                username = data.get(Words.DataParamKey.USERNAME)
                print(f"User {username} has joined your room.")
            case Words.EventType.USER_LEFT:
                username = data.get(Words.DataParamKey.USERNAME)
                print(f"User {username} has left your room.")
                if not self.info.is_room_owner and data.get(Words.DataParamKey.NOW_ROOM_INFO, {}).get("owner") == self.info.name:
                    print("You are now the room owner.")
                    self.info.is_room_owner = True
            case Words.EventType.CONNECT_TO_GAME_SERVER:
                host = data.get(Words.DataParamKey.HOST, self.host)
                port = data.get(Words.DataParamKey.PORT)
                if port is None:
                    print("CONNECT_TO_GAME_SERVER event missing port. Ignoring.")
                    return
                print(f"Game is starting! Connect to game server at {host}:{port}.")
                if self.game_connected:
                    print("Already connected to a game server; ignoring duplicate connect event.")
                    return
                try:
                    # close any previous game passer (best-effort)
                    try:
                        if self.game_msgfmt_passer is not None:
                            self.game_msgfmt_passer.close()
                    except Exception:
                        pass

                    # create fresh passer and connect
                    self.game_msgfmt_passer = MessageFormatPasser(timeout=2.0)
                    self.game_msgfmt_passer.connect(host, port)

                    # send client->server connect handshake (game server expects this)
                    self.game_msgfmt_passer.send_args(Protocols.ClientToGameServer.CONNECT, self.info.name, self.info.current_room_id, 'player')

                    # receive single CONNECT_RESPONSE and unpack it once
                    res = self.game_msgfmt_passer.receive_args(Protocols.GameServerToPlayer.CONNECT_RESPONSE)
                    if not res:
                        print("No response from game server. Connection failed.")
                        try:
                            self.game_msgfmt_passer.close()
                        except Exception:
                            pass
                        return

                    result, role, seed, random_mode, gravity_plan = res
                    if result != Words.Result.SUCCESS:
                        print("Failed to connect to game server.")
                        try:
                            self.game_msgfmt_passer.close()
                        except Exception:
                            pass
                        return

                    print(f"Connected to game server as {role} with seed {seed} and random mode {random_mode}.")
                    self.player_id = role
                    self.game_connected = True
                except Exception as e:
                    print(f"Error connecting to game server: {e}")
                    try:
                        if self.game_msgfmt_passer is not None:
                            self.game_msgfmt_passer.close()
                    except Exception:
                        pass
            case _:
                print(f"Unknown event type: {event_type}")
        #self.print_prompt()
    def handle_message(self, msg: list) -> None:
        message_type, responding_command, event_type, result, data = msg
        if message_type == Words.MessageType.RESPONSE:
            self.response_queue.put([responding_command, result, data])
        elif message_type == Words.MessageType.EVENT:
            self.event_queue.put([event_type, data])
        else:
            print(f"Unknown message type: {message_type}")

    def get_response(self, timeout: float | None = None) -> list | None:
        try:
            return self.response_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_event(self, timeout: float | None = None) -> list | None:
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        