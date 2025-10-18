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
        self.listen_thread = threading.Thread(target=self.listen_for_messages)
        self.get_event_thread = threading.Thread(target=self.listen_for_events)
        self.shutdown_event = threading.Event()
        self.fatal_error_event = threading.Event()
        self.response_queue = queue.Queue()
        self.event_queue = queue.Queue()

    def start(self, host: str = "127.0.0.1", port: int = 21354) -> None:
        self.lobby_msgfmt_passer.connect(host, port)
        
        self.lobby_msgfmt_passer.send_args(Protocols.ConnectionToLobby.HANDSHAKE, Words.ConnectionType.CLIENT)
        result, message = self.lobby_msgfmt_passer.receive_args(Protocols.LobbyToConnection.HANDSHAKE_RESPONSE)  # Wait for handshake response
        if result != Words.Result.CONFIRMED:
            raise ConnectionError(f"Handshake failed: {message}")
        self.listen_thread.start()
        self.get_event_thread.start()

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
                self.fatal_error_event.set()

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
        if event_type == Words.EventType.SERVER_SHUTDOWN:
            print("Server is shutting down. Closing client.")
            self.close()

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
        