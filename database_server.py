import json
import message_format_passer
from protocols import Protocols, Words
import threading
import os

USER_DB_FILE = 'user_db.json'
ROOM_DB_FILE = 'room_db.json'

class DatabaseServer:
    """A simple database server that handles requests from the lobby server. It connects to lobby server just like client."""
    def __init__(self) -> None:
        self.msgfmt_passer = message_format_passer.MessageFormatPasser(timeout=1.0)
        self.lobby_request_receiver_thread = threading.Thread(target=self.receive_lobby_request, daemon=True)
        self.shutdown_event = threading.Event()
        self.user_db = self.load_user_db()
        self.room_db = self.load_room_db()

    def load_user_db(self):
        if not os.path.exists(USER_DB_FILE):
            return {}
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
        
    def save_user_db(self):
        with open(USER_DB_FILE, 'w') as f:
            json.dump(self.user_db, f, indent=2)

    def load_room_db(self):
        if not os.path.exists(ROOM_DB_FILE):
            return {}
        with open(ROOM_DB_FILE, 'r') as f:
            return json.load(f)

    def save_room_db(self):
        with open(ROOM_DB_FILE, 'w') as f:
            json.dump(self.room_db, f, indent=2)

    def receive_lobby_request(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                request_id, collection, action, data = self.msgfmt_passer.receive_args(Protocols.LobbyToDB.REQUEST)
                self.process_message(request_id, collection, action, data)
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error in database server: {e}")
                break

    def start(self, host: str = "127.0.0.1", port: int = 21354) -> None:
        self.msgfmt_passer.connect(host, port)
        self.msgfmt_passer.send_args(Protocols.ConnectionToLobby.HANDSHAKE, Words.ConnectionType.DATABASE_SERVER)
        result, message = self.msgfmt_passer.receive_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE)  # Wait for handshake response
        if result != Words.Result.CONFIRMED:
            raise ConnectionError(f"Handshake failed: {message}")
        print("Database server connected to lobby server.")

        self.lobby_request_receiver_thread.start()
        while not self.shutdown_event.is_set():
            try:
                command = input("Enter 'stop' to stop database server: ")  # Keep the main thread alive
                if command.strip().lower() == "stop":
                    print("Shutting down database server.")
                    self.shutdown_event.set()
                else:
                    print("Unknown command. Type 'stop' to stop the server.")
            except KeyboardInterrupt:
                print("Shutting down database server.")
                self.shutdown_event.set()
        self.save_user_db()
        self.save_room_db()
        self.lobby_request_receiver_thread.join()
        self.msgfmt_passer.close()

    def process_message(self, request_id: str, collection: str, action: str, data: dict) -> None:
        match collection:
            case Words.Collection.USER:
                match action:
                    case Words.Action.QUERY:
                        if Words.DataParamKey.USERNAME in data:
                            username = data.get(Words.DataParamKey.USERNAME)
                            user_info = self.user_db.get(username)
                            if user_info is not None:
                                self.send_response(request_id, Words.Result.FOUND, user_info)
                            else:
                                self.send_response(request_id, Words.Result.NOT_FOUND, {})
                        else:
                            # here data may contain other filtering criteria
                            limited_user_info = {username: user_info for username, user_info in self.user_db.items() \
                                                  if not any(data.get(key) != user_info.get(key) for key in data.keys())}
                            self.send_response(request_id, Words.Result.FOUND, limited_user_info)
                    case Words.Action.CREATE:
                        username = data.get(Words.DataParamKey.USERNAME)
                        if username in self.user_db:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "Username already exists."})
                        else:
                            user_dict = {}
                            user_dict[Words.DataParamKey.PASSWORD] = data.get(Words.DataParamKey.PASSWORD)
                            user_dict[Words.DataParamKey.GAMES_PLAYED] = 0
                            user_dict[Words.DataParamKey.GAMES_WON] = 0
                            user_dict[Words.DataParamKey.ONLINE] = False
                            user_dict[Words.DataParamKey.CURRENT_ROOM_ID] = None
                            self.user_db[username] = user_dict
                            self.save_user_db()
                            self.send_response(request_id, Words.Result.SUCCESS, {Words.DataParamKey.MESSAGE: "User created successfully."})
                    case Words.Action.UPDATE:
                        username = data.get(Words.DataParamKey.USERNAME)
                        if username not in self.user_db:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "User not found."})
                        else:
                            for key, value in data.items():
                                if key != Words.DataParamKey.USERNAME:
                                    self.user_db[username][key] = value
                            self.send_response(request_id, Words.Result.SUCCESS, {Words.DataParamKey.MESSAGE: "User updated successfully."})
                        self.save_user_db()
                    case _:
                        self.send_response(request_id, Words.Result.ERROR, {Words.DataParamKey.MESSAGE: f"Unknown action: {action}"})
            case Words.Collection.ROOM:
                match action:
                    case Words.Action.QUERY:
                        all_room_info = {room_id: info for room_id, info in self.room_db.items()}
                        self.send_response(request_id, Words.Result.FOUND, all_room_info)
                    case Words.Action.CREATE:
                        owner = data.get(Words.DataParamKey.OWNER)
                        settings = data.get(Words.DataParamKey.SETTINGS, {})
                        users = [owner]
                        room_id = 0
                        while str(room_id) in self.room_db:
                            room_id += 1
                        room_id_str = str(room_id)
                        room_info = {
                            Words.DataParamKey.OWNER: owner,
                            Words.DataParamKey.SETTINGS: settings,
                            Words.DataParamKey.USERS: users
                        }
                        self.room_db[room_id_str] = room_info
                        self.save_room_db()
                        self.user_db[owner][Words.DataParamKey.CURRENT_ROOM_ID] = room_id_str
                        self.save_user_db()
                        self.send_response(request_id, Words.Result.SUCCESS, {Words.DataParamKey.ROOM_ID: room_id_str, Words.DataParamKey.MESSAGE: "Room created successfully."})
                    case Words.Action.DELETE:
                        room_id = data.get(Words.DataParamKey.ROOM_ID)
                        if room_id not in self.room_db:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "Room not found."})
                        else:
                            del self.room_db[room_id]
                            self.save_room_db()
                            self.send_response(request_id, Words.Result.SUCCESS, {Words.DataParamKey.MESSAGE: "Room deleted successfully."})
                    case Words.Action.ADD_USER:
                        room_id = data.get(Words.DataParamKey.ROOM_ID)
                        username = data.get(Words.DataParamKey.USERNAME)
                        room_info = self.room_db.get(room_id)
                        if room_info is None:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "Room not found."})
                        elif username in room_info["users"]:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "User already in room."})
                        else:
                            room_info["users"].append(username)
                            self.save_room_db()
                            self.user_db[username][Words.DataParamKey.CURRENT_ROOM_ID] = room_id
                            self.save_user_db()
                            self.send_response(request_id, Words.Result.SUCCESS, {Words.DataParamKey.MESSAGE: "User added to room successfully.", Words.DataParamKey.NOW_ROOM_INFO: room_info})

                    case Words.Action.REMOVE_USER:
                        room_id = data.get(Words.DataParamKey.ROOM_ID)
                        username = data.get(Words.DataParamKey.USERNAME)
                        room_info = self.room_db.get(room_id)
                        if room_info is None:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "Room not found."})
                        elif username not in room_info["users"]:
                            self.send_response(request_id, Words.Result.FAILURE, {Words.DataParamKey.MESSAGE: "User not in room."})
                        else:
                            room_info["users"].remove(username)
                            if room_info["owner"] == username:
                                if room_info["users"]:
                                    room_info["owner"] = room_info["users"][0]
                                else: # no users left, delete room
                                    room_info["owner"] = None
                                    del self.room_db[room_id]
                            self.save_room_db()
                            self.user_db[username][Words.DataParamKey.CURRENT_ROOM_ID] = None
                            self.save_user_db()
                            self.send_response(request_id, Words.Result.SUCCESS, {Words.DataParamKey.MESSAGE: "User removed from room successfully.", Words.DataParamKey.NOW_ROOM_INFO: room_info})
                    case _:
                        self.send_response(request_id, Words.Result.ERROR, {Words.DataParamKey.MESSAGE: f"Unknown action: {action}"})
            case _:
                self.send_response(request_id, Words.Result.ERROR, {Words.DataParamKey.MESSAGE: f"Unknown collection: {collection}"})

    def send_response(self, request_id: str, result: str, data: dict) -> None:
        self.msgfmt_passer.send_args(Protocols.DBToLobby.RESPONSE, request_id, result, data)
        print(f"Sent response: request_id={request_id}, result={result}, data={data}")
