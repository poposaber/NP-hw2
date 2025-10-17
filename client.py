from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
from user_info import UserInfo
import threading
import queue

class Client:
    def __init__(self) -> None:
        self.lobby_msgfmt_passer = MessageFormatPasser(timeout=1.0)
        self.game_msgfmt_passer = MessageFormatPasser(timeout=1.0)
        self.temp_username: str | None = None
        self.user_info = UserInfo()
        self.listen_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.stop_listening_event = threading.Event()
        self.response_queue = queue.Queue()
        self.event_queue = queue.Queue()

    def start(self, host: str = "127.0.0.1", port: int = 21354) -> None:
        self.lobby_msgfmt_passer.connect(host, port)
        
        self.lobby_msgfmt_passer.send_args(Protocols.ConnectionToLobby.HANDSHAKE, Words.ConnectionType.CLIENT)
        result, message = self.lobby_msgfmt_passer.receive_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE)  # Wait for handshake response
        if result != Words.Result.CONFIRMED:
            raise ConnectionError(f"Handshake failed: {message}")
        self.listen_thread.start()

    def close(self) -> None:
        self.stop_listening_event.set()
        self.listen_thread.join()
        self.send_to_lobby(Words.Command.EXIT, {})
        self.lobby_msgfmt_passer.close()
        self.game_msgfmt_passer.close()

    def send_to_lobby(self, command: str, params: dict) -> None:
        self.lobby_msgfmt_passer.send_args(Protocols.ClientToLobby.COMMAND, command, params)

    def listen_for_messages(self) -> None:
        while not self.stop_listening_event.is_set():
            try:
                msg = self.lobby_msgfmt_passer.receive_args(Protocols.LobbyToClient.MESSAGE)
                self.handle_message(msg)
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error listening for messages: {e}")
                try:
                    self.lobby_msgfmt_passer.close()
                except Exception:
                    pass
                try:
                    self.game_msgfmt_passer.close()
                except Exception:
                    pass
                break

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
        