from player import Player
from tetris import Tetris
from protocols import Protocols, Words

class Game:
    def __init__(self, seed: int) -> None:
        self.player1: Player = Player("player1")
        self.player2: Player = Player("player2")
        self.tetris1: Tetris = Tetris(gravity_time=1.0, seed=seed)
        self.tetris2: Tetris = Tetris(gravity_time=1.0, seed=seed)
        self.goal_score: int = 300
        self.seed: int = seed
        self.gameover: bool = False
        self.winner: str | None = None


    def handle_player_action(self, player_id: str, action: str, data: dict) -> None:
        if player_id == "player1":
            tetris = self.tetris1
        else:
            tetris = self.tetris2
        match action:
            case Words.GameAction.MOVE_LEFT:
                if tetris.now_piece_can_move("left"):
                    tetris.now_piece.move("left")
            case Words.GameAction.MOVE_RIGHT:
                if tetris.now_piece_can_move("right"):
                    tetris.now_piece.move("right")
            case Words.GameAction.ROTATE:
                tetris.try_rotate_now_piece()
            case Words.GameAction.SOFT_DROP:
                tetris.drop_piece_one_step()
            case Words.GameAction.HARD_DROP:
                tetris.hard_drop_piece()
            case Words.GameAction.CHANGE_COLOR:
                tetris.change_now_piece_color(data.get("color", 1))

    def update(self, delta_time: float) -> None:
        if self.gameover:
            return
        self.tetris1.update(delta_time)
        self.tetris2.update(delta_time)
        cleared_cells1 = self.tetris1.get_recent_cleared_cells()
        cleared_cells2 = self.tetris2.get_recent_cleared_cells()
        if sum(cleared_cells1) > 0:
            self.player1.process_cleared_cells(cleared_cells1, self.player2)
            self.tetris1.clear_recent_cleared_cells()
        if sum(cleared_cells2) > 0:
            self.player2.process_cleared_cells(cleared_cells2, self.player1)
            self.tetris2.clear_recent_cleared_cells()
        self.player1.update(delta_time)
        self.player2.update(delta_time)
        if self.player1.score >= self.goal_score and not self.gameover:
            self.gameover = True
            self.winner = "player1"
        elif self.player2.score >= self.goal_score and not self.gameover:
            self.gameover = True
            self.winner = "player2"

    def get_board_string(self, player_id: str) -> str:
        if player_id == "player1":
            tetris = self.tetris1
        else:
            tetris = self.tetris2
        return Tetris.to_board_string(tetris.board)

        