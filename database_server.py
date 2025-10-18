import json
import message_format_passer
from protocols import Protocols, Words
import threading
import os

USER_DB_FILE = 'user_db.json'

class DatabaseServer:
    """A simple database server that handles requests from the lobby server. It connects to lobby server just like client."""
    def __init__(self) -> None:
        self.msgfmt_passer = message_format_passer.MessageFormatPasser(timeout=1.0)
        self.lobby_request_receiver_thread = threading.Thread(target=self.receive_lobby_request, daemon=True)
        self.shutdown_event = threading.Event()
        self.user_db = self.load_user_db()

    def load_user_db(self):
        if not os.path.exists(USER_DB_FILE):
            return {}
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
        
    def save_user_db(self):
        with open(USER_DB_FILE, 'w') as f:
            json.dump(self.user_db, f, indent=2)

    def receive_lobby_request(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                collection, action, data = self.msgfmt_passer.receive_args(Protocols.LobbyToDB.REQUEST)
                self.process_message(collection, action, data)
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
        self.lobby_request_receiver_thread.join()
        self.msgfmt_passer.close()

    def process_message(self, collection: str, action: str, data: dict) -> None:
        pass

    def send_response(self, result: str, data: dict) -> None:
        self.msgfmt_passer.send_args(Protocols.DBToLobby.RESPONSE, result, data)
        print(f"Sent response: result={result}, data={data}")
