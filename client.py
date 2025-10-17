from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
import threading

class Client:
    def __init__(self, host: str = "127.0.0.1", port: int = 21354) -> None:
        self.msgfmt_passer = MessageFormatPasser(host=host, port=port)
        self.username: str | None = None
        self.current_room: str | None = None
        self.current_game = None
        self.listen_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.stop_listening_event = threading.Event()

    def start(self) -> None:
        self.listen_thread.start()

    def close(self) -> None:
        self.stop_listening_event.set()
        self.listen_thread.join()
        self.msgfmt_passer.close()

    def listen_for_messages(self) -> None:
        while not self.stop_listening_event.is_set():
            try:
                msg = self.msgfmt_passer.receive_args(Protocols.LobbyToClient.RESPONSE)
                self.handle_message(msg)
            except TimeoutError:
                continue
            except Exception as e:
                print(f"Error listening for messages: {e}")
                break

    def handle_message(self, msg: list) -> None:
        # Handle incoming messages from the server
        pass