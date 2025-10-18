from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
from user_info import UserInfo
import threading
import socket
import time
import queue

class LobbyServer:
    def __init__(self) -> None:
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.server_sock.bind((host, port))
        #self.server_sock.listen()
        #print(f"Lobby server listening on {host}:{port}")
        # self.clients: list[MessageFormatPasser] = []
        self.connections: list[MessageFormatPasser] = []
        self.user_infos: dict[MessageFormatPasser, UserInfo] = {}
        self.db_server_passer: MessageFormatPasser | None = None
        self.shutdown_event = threading.Event()
        self.send_to_DB_queue = queue.Queue()
        #self.accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
        #self.accept_thread.start()

    def accept_connections(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                connection_sock, addr = self.server_sock.accept()
                print(f"Accepted connection from {addr}")
                msgfmt_passer = MessageFormatPasser(connection_sock)
                #self.clients.append(msgfmt_passer)
                #self.user_infos[msgfmt_passer] = UserInfo()
                self.connections.append(msgfmt_passer)
                print(f"Active connections: {len(self.connections)}")
                # Since connection may be client, db, or game server, start a thread to handle initial handshake
                threading.Thread(target=self.handle_connections, args=(msgfmt_passer,)).start()
            except socket.timeout:
                continue

    def handle_connections(self, msgfmt_passer: MessageFormatPasser) -> None:
        """Check handshake and pass to corresponding methods."""
        try:
            connection_type, = msgfmt_passer.receive_args(Protocols.ConnectionToLobby.HANDSHAKE)
            if connection_type == Words.ConnectionType.CLIENT:
                self.handle_client(msgfmt_passer)
            elif connection_type == Words.ConnectionType.DATABASE_SERVER:
                self.handle_database_server(msgfmt_passer)
            elif connection_type == Words.ConnectionType.GAME_SERVER:
                self.handle_game_server(msgfmt_passer)
            else:
                print(f"Unknown connection type: {connection_type}")
        except Exception as e:
            print(f"Error during handshake: {e}")

        self.connections.remove(msgfmt_passer)
        print(f"Connection closed. Active connections: {len(self.connections)}")
        msgfmt_passer.close()

    def handle_database_server(self, msgfmt_passer: MessageFormatPasser) -> None:
        if self.db_server_passer is not None:
            print("A database server is already connected. Rejecting new connection.")
            msgfmt_passer.send_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE, Words.Result.ERROR, "Database server already connected.")
            return
        self.db_server_passer = msgfmt_passer
        print("Database server connected.")
        msgfmt_passer.send_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE, Words.Result.CONFIRMED, "Database server connected successfully.")
        while not self.shutdown_event.is_set():
            if not self.send_to_DB_queue.empty():
                request = self.send_to_DB_queue.get(timeout=1.0)
                try:
                    msgfmt_passer.send_args(Protocols.LobbyToDB.REQUEST, *request)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Error sending request to database server: {e}")
                    break
        self.db_server_passer = None
        print("Database server disconnected.")

    def handle_game_server(self, msgfmt_passer: MessageFormatPasser) -> None:
        pass

    def handle_client(self, msgfmt_passer: MessageFormatPasser) -> None:
        self.user_infos[msgfmt_passer] = UserInfo()
        msgfmt_passer.send_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE, Words.Result.CONFIRMED, Words.Message.WELCOME_USER)
        msgfmt_passer.settimeout(2.0)
        while not self.shutdown_event.is_set():
            try:
                msg = msgfmt_passer.receive_args(Protocols.ClientToLobby.COMMAND)
                result = self.process_message(msg, msgfmt_passer)
                if result == -1:
                    break
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error handling client {msgfmt_passer}: {e}")
                break

        if self.shutdown_event.is_set():
            msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.EVENT, "", Words.EventType.SERVER_SHUTDOWN, "", {})
            exit_msg = msgfmt_passer.receive_args(Protocols.ClientToLobby.COMMAND)[0]
            if exit_msg != Words.Command.EXIT:
                print(f"Expected EXIT command, got: {exit_msg}")
        self.remove_client(msgfmt_passer)

    def process_message(self, msg: list, msgfmt_passer: MessageFormatPasser) -> int:
        command, params = msg
        print(f"Received command: {command} with params: {params}")
        # Here you would add logic to process different commands
        match command:
            case Words.Command.EXIT:
                return -1
            case _:
                msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, command, "", Words.Result.INVALID, {})
                return 0

    def remove_client(self, msgfmt_passer: MessageFormatPasser) -> None:
        #self.clients.remove(msgfmt_passer)
        del self.user_infos[msgfmt_passer]

    def start_server(self, host: str, port: int) -> None:
        self.server_sock.bind((host, port))
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)
        print(f"Lobby server listening on {host}:{port}")
        self.accept_connections()
        self.server_sock.close()

    def start(self, host = "0.0.0.0", port = 21354) -> None:
        server_thread = threading.Thread(target=self.start_server, args=(host, port,))
        server_thread.start()
        time.sleep(0.2)
        try:
            while True:
                cmd = input("Enter 'stop' to stop the server: ")
                if cmd == 'stop':
                    self.shutdown_event.set()
                    break
                else:
                    print("invalid command.")
        except KeyboardInterrupt:
            self.shutdown_event.set()

        server_thread.join()