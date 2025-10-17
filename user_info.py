class UserInfo:
    def __init__(self):
        self.name: str | None = None
        self.current_room: str | None = None
        self.current_game: str | None = None

    def reset(self) -> None:
        self.name = None
        self.current_room = None
        self.current_game = None