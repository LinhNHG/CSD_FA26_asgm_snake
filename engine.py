from random import Random

from config import POINTS_PER_APPLE
from models import Direction, Position, Snapshot, StepResult
from snake import Snake
from food import spawn_apple
from rules import is_inside, is_opposite, validate_direction


def _is_plain_int(value) -> bool:
    """True khi value là int thật (bool không được tính là số nguyên)."""
    return isinstance(value, int) and not isinstance(value, bool)


class GameEngine:
    # Rắn ban đầu: đầu -> đuôi, hướng RIGHT (theo README / PHAN_CONG)
    START_BODY: tuple[Position, ...] = ((2, 1), (1, 1), (0, 1))
    START_DIRECTION: Direction = "RIGHT"

    def __init__(self, cols: int = 20, rows: int = 15, seed: int | None = None):
        """IN: cols>=4, rows>=3, số nguyên; sai: ValueError.

        OUT: lưu kích thước, Random(seed), sau đó reset().
        """
        if not _is_plain_int(cols) or not _is_plain_int(rows):
            raise ValueError("cols and rows must be integers")
        if cols < 4:
            raise ValueError("cols must be >= 4")
        if rows < 3:
            raise ValueError("rows must be >= 3")

        self.cols: int = cols
        self.rows: int = rows
        self.rng: Random = Random(seed)  # tạo một lần; reset() không tạo lại

        # Các thuộc tính trạng thái được khai báo ở đây, giá trị thật do reset() gán
        self.snake: Snake
        self.apple: Position | None
        self.score: int
        self.status: str
        self._direction_locked: bool

        self.reset()

    def reset(self) -> None:
        """OUT: None; rắn [(2,1),(1,1),(0,1)], hướng RIGHT,
        score=0, status=RUNNING, sinh táo mới. Xóa khóa đổi hướng.
        Giữ rng hiện có, không khởi tạo lại seed mỗi lần reset.
        """
        self.snake = Snake(list(self.START_BODY), self.START_DIRECTION)
        self.score = 0
        self.status = "RUNNING"
        self._direction_locked = False
        self.apple = spawn_apple(self.cols, self.rows, self.snake.occupied, self.rng)

    def change_direction(self, new_direction: Direction) -> bool:
        """OUT: True khi nhận hướng mới; False khi cùng hướng, ngược 180 độ,
        game đã kết thúc hoặc đã nhận một lần đổi hướng trước step tiếp theo.
        Chuỗi ngoài 4 hướng: ValueError. Từ chối không làm thay đổi trạng thái.
        """
        validate_direction(new_direction)  # sai -> ValueError, chưa đổi gì

        if self.status != "RUNNING":
            return False
        if self._direction_locked:
            return False
        current = self.snake.direction
        if new_direction == current:
            return False  # cùng hướng: không khóa tick
        if is_opposite(current, new_direction):
            return False  # quay ngược: không khóa tick

        self.snake.direction = new_direction
        self._direction_locked = True  # tối đa một lần đổi hướng giữa hai tick
        return True

    def step(self) -> StepResult:
        """Một tick logic. Xem README mục trình tự và bảng kết quả.

        OUT: StepResult; đây là nơi duy nhất tăng điểm và thay trạng thái game.
        """
        # 1. Game đã kết thúc: không thay đổi gì
        if self.status != "RUNNING":
            return StepResult(self.status, self.score, False, "NO_CHANGE")

        # 2. Đầu mới và có ăn táo hay không
        next_head = self.snake.next_head()
        grow = self.apple is not None and next_head == self.apple

        # 3. Đụng tường
        if not is_inside(next_head, self.cols, self.rows):
            self.status = "GAME_OVER"
            self._direction_locked = False
            return StepResult(self.status, self.score, False, "WALL")

        # 4. Đụng thân (ô đuôi hiện tại hợp lệ khi không grow: do Snake xử lý)
        if self.snake.would_hit_self(next_head, grow):
            self.status = "GAME_OVER"
            self._direction_locked = False
            return StepResult(self.status, self.score, False, "SELF")

        # 5. Cập nhật rắn; ăn táo thì cộng điểm và sinh táo mới
        self.snake.advance(next_head, grow)
        reason = "MOVE"
        if grow:
            self.score += POINTS_PER_APPLE
            self.apple = spawn_apple(
                self.cols, self.rows, self.snake.occupied, self.rng
            )
            if self.apple is None:  # kín bàn
                self.status = "WON"
                reason = "BOARD_FULL"
            else:
                reason = "EAT"

        # 6. Mở khóa đổi hướng cho tick kế tiếp
        self._direction_locked = False
        return StepResult(self.status, self.score, grow, reason)

    def snapshot(self) -> Snapshot:
        """OUT: bản sao body dạng tuple và các giá trị hiện tại; O(L)."""
        return Snapshot(
            body=tuple(self.snake.body),
            apple=self.apple,
            direction=self.snake.direction,
            score=self.score,
            status=self.status,
        )
