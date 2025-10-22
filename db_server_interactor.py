from message_format_passer import MessageFormatPasser
from protocols import Protocols, Words
import threading

class DBServerInteractor:
    def __init__(self, db_msgfmt_passer: MessageFormatPasser) -> None:
        self.msgfmt_passer = db_msgfmt_passer
        self.shutdown_event = threading.Event()
        self.db_requests_: dict[str, tuple[MessageFormatPasser, ]] = {}

# not sure it will be used