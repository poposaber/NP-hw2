# next objective: make help_exit be a method, make sending offline message to db be a method, design user login token(user can only login from one client at a time)

from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
import threading
import socket
import time
import queue
import uuid
import random

class LobbyServer:
    def __init__(self) -> None:
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.server_sock.bind((host, port))
        #self.server_sock.listen()
        #print(f"Lobby server listening on {host}:{port}")
        # self.clients: list[MessageFormatPasser] = []
        self.connections: list[MessageFormatPasser] = []
        #self.user_infos: dict[MessageFormatPasser, UserInfo] = {}
        self.mfpassers_username: dict[MessageFormatPasser, str] = {}
        self.db_server_passer: MessageFormatPasser | None = None
        self.shutdown_event = threading.Event()
        self.pending_db_response_dict: dict[str, tuple[bool, str, dict]] = {}
        """The dict contains all sent db_requests, after processing, received responses will be popped. {request_id: (client_msgfmt_passer, response_received, result, data)}"""
        self.pending_db_response_lock = threading.Lock()
        #self.send_to_DB_queue = queue.Queue()
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
        self.db_server_passer.settimeout(2.0)
        print("Database server connected.")
        msgfmt_passer.send_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE, Words.Result.CONFIRMED, "Database server connected successfully.")
        while not self.shutdown_event.is_set():
            try:
                response = msgfmt_passer.receive_args(Protocols.DBToLobby.RESPONSE)
                responding_request_id = response[0]
                with self.pending_db_response_lock:
                    self.pending_db_response_dict[responding_request_id] = (True, response[1], response[2])
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error receiving response from database server: {e}")
                break
        self.db_server_passer = None
        print("Database server disconnected.")

    def handle_game_server(self, msgfmt_passer: MessageFormatPasser) -> None:
        pass

    def handle_client(self, msgfmt_passer: MessageFormatPasser) -> None:
        #self.user_infos[msgfmt_passer] = UserInfo()
        self.mfpassers_username[msgfmt_passer] = None
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
                # send database to set user offline if logged in
                username = self.mfpassers_username.get(msgfmt_passer)
                if username is not None:
                    request_id = str(uuid.uuid4())
                    with self.pending_db_response_lock:
                        self.pending_db_response_dict[request_id] = (False, "", {})
                    self.send_to_database(request_id, Words.Collection.USER, Words.Action.UPDATE, {"username": username, "online": False})
                break

        if self.shutdown_event.is_set():
            msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.EVENT, "", Words.EventType.SERVER_SHUTDOWN, "", {})
            exit_msg = msgfmt_passer.receive_args(Protocols.ClientToLobby.COMMAND)[0]
            if exit_msg != Words.Command.EXIT:
                print(f"Expected EXIT command, got: {exit_msg}")

        del self.mfpassers_username[msgfmt_passer]
            
        #self.remove_client(msgfmt_passer)

    def process_message(self, msg: list, msgfmt_passer: MessageFormatPasser) -> int:
        command, params = msg
        print(f"Received command: {command} with params: {params}")
        # Here you would add logic to process different commands
        match command:
            case Words.Command.EXIT:
                # if logged in, set user offline in db
                username = self.mfpassers_username.get(msgfmt_passer)
                if username is not None:
                    request_id = str(uuid.uuid4())
                    with self.pending_db_response_lock:
                        self.pending_db_response_dict[request_id] = (False, "", {})
                    self.send_to_database(request_id, Words.Collection.USER, Words.Action.UPDATE, {"username": username, "online": False})
                    # Wait for update response
                    update_result, _ = self.receive_from_database(request_id)
                    if update_result != Words.Result.SUCCESS:
                        print(f"Warning: Failed to update user online status for {username}")
                return -1
            case Words.Command.LOGIN:
                self.help_login(params, msgfmt_passer)
            case Words.Command.CHECK_USERNAME:
                self.help_check_username(params, msgfmt_passer)
            case Words.Command.REGISTER:
                self.help_register(params, msgfmt_passer)
            case _:
                msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, command, "", Words.Result.INVALID, {})
        return 0

    def help_login(self, params: dict, msgfmt_passer: MessageFormatPasser) -> None:
        username = params.get("username")
        password = params.get("password")
        # Send request to database server to verify user
        
        # Wait for response from database server
        if self.db_server_passer is not None:
            try:
                request_id = str(uuid.uuid4())
                with self.pending_db_response_lock:
                    self.pending_db_response_dict[request_id] = (False, "", {})
                self.send_to_database(request_id, Words.Collection.USER, Words.Action.QUERY, {"username": username})
                # Wait for response
                query_result, query_data = self.receive_from_database(request_id)
                # while True:
                #     time.sleep(random.uniform(0.1, 0.3))  # Avoid busy waiting
                #     with self.pending_db_response_lock:
                #         response_received, result, data = self.pending_db_response_dict[request_id]
                #         # it seems that client_msgfmt_passer is always msgfmt_passer
                #         if not response_received:
                #             continue
                #         del self.pending_db_response_dict[request_id]
                if query_result == Words.Result.FOUND:
                    user_info = query_data
                    if user_info.get("password") == password:
                        request_id = str(uuid.uuid4())
                        with self.pending_db_response_lock:
                            self.pending_db_response_dict[request_id] = (False, "", {})
                        self.send_to_database(request_id, Words.Collection.USER, Words.Action.UPDATE, {"username": username, "online": True})
                        # Wait for update response
                        update_result, _ = self.receive_from_database(request_id)
                        if update_result != Words.Result.SUCCESS:
                            print(f"Warning: Failed to update user online status for {username}")
                        msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.LOGIN, "", Words.Result.SUCCESS, {"message": "Login successful."})
                        self.mfpassers_username[msgfmt_passer] = username
                        #self.user_infos[msgfmt_passer].name = username
                    else:
                        msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.LOGIN, "", Words.Result.FAILURE, {"message": "Incorrect username or password."})
                else:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.LOGIN, "", Words.Result.FAILURE, {"message": "Incorrect username or password."})
                    
            except Exception as e:
                print(f"Error receiving response from database server: {e}")
                msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.LOGIN, "", Words.Result.ERROR, {"message": "Database error."})
        else:
            msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.LOGIN, "", Words.Result.ERROR, {"message": "No database server connected."})

    def help_check_username(self, params: dict, msgfmt_passer: MessageFormatPasser) -> None:
        username = params.get("username")
        # Wait for response from database server
        if self.db_server_passer is not None:
            try:
                request_id = str(uuid.uuid4())
                with self.pending_db_response_lock:
                    self.pending_db_response_dict[request_id] = (False, "", {})
                self.send_to_database(request_id, Words.Collection.USER, Words.Action.QUERY, {"username": username})
                # Wait for response
                result, _ = self.receive_from_database(request_id)
                if result == Words.Result.FOUND:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.CHECK_USERNAME, "", Words.Result.INVALID, {"message": "Username already taken."})
                elif result == Words.Result.NOT_FOUND:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.CHECK_USERNAME, "", Words.Result.VALID, {"message": "Username is available."})
                else:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.CHECK_USERNAME, "", Words.Result.ERROR, {"message": "Database error."})
            except Exception as e:
                print(f"Error receiving response from database server: {e}")
                msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.CHECK_USERNAME, "", Words.Result.ERROR, {"message": "Database error."})
        else:
            msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.CHECK_USERNAME, "", Words.Result.ERROR, {"message": "No database server connected."})
    
    def help_register(self, params: dict, msgfmt_passer: MessageFormatPasser) -> None:
        username = params.get("username")
        password = params.get("password")    

        # Wait for response from database server
        if self.db_server_passer is not None:
            try:
                request_id = str(uuid.uuid4())
                with self.pending_db_response_lock:
                    self.pending_db_response_dict[request_id] = (False, "", {})
                self.send_to_database(request_id, Words.Collection.USER, Words.Action.CREATE, {"username": username, "password": password})
                # Wait for response
                result, _ = self.receive_from_database(request_id)
                if result == Words.Result.SUCCESS:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.REGISTER, "", Words.Result.SUCCESS, {"message": "Registration successful."})
                elif result == Words.Result.FAILURE:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.REGISTER, "", Words.Result.FAILURE, {"message": "Username already taken."})
                else:
                    msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.REGISTER, "", Words.Result.ERROR, {"message": "Database error."})
            except Exception as e:
                print(f"Error receiving response from database server: {e}")
                msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.REGISTER, "", Words.Result.ERROR, {"message": "Database error."})
        else:
            msgfmt_passer.send_args(Protocols.LobbyToClient.MESSAGE, Words.MessageType.RESPONSE, Words.Command.REGISTER, "", Words.Result.ERROR, {"message": "No database server connected."})

    #def remove_client(self, msgfmt_passer: MessageFormatPasser) -> None:
        #self.clients.remove(msgfmt_passer)
        #del self.user_infos[msgfmt_passer]

    def send_to_database(self, request_id: str, collection: str, action: str, data: dict) -> None:
        if self.db_server_passer is not None:
            self.db_server_passer.send_args(Protocols.LobbyToDB.REQUEST, request_id, collection, action, data)

    def receive_from_database(self, request_id: str) -> tuple[str, dict]:
        while True:
            time.sleep(random.uniform(0.1, 0.3))  # Avoid busy waiting
            with self.pending_db_response_lock:
                if request_id in self.pending_db_response_dict:
                    response_received, result, data = self.pending_db_response_dict[request_id]
                    if response_received:
                        del self.pending_db_response_dict[request_id]
                        print(f"Received response from database for request_id {request_id}: {result}, {data}")
                        return (result, data)



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