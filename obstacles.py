"""Engine có vật cản (chỉ dùng cho độ khó 'Khó').

Kế thừa GameEngine, KHÔNG sửa engine.py. Vật cản là các ô đá cố định:
- đụng đá = thua (reason "WALL");
- táo không bao giờ sinh trên đá;
- đá nằm bên trong bàn và không hai viên nào chạm nhau (kể cả chéo)
  nên bàn luôn liên thông, rắn không bao giờ bị nhốt.
"""
from config import POINTS_PER_APPLE  # noqa: F401  (giữ cùng hợp đồng config)
from engine import GameEngine
from food import spawn_apple
from models import Position, StepResult


class ObstacleEngine(GameEngine):
    def __init__(self, cols: int = 20, rows: int = 15, seed: int | None = None,
                 obstacle_count: int = 6):
        self.obstacle_count = obstacle_count
        self.obstacles: set[Position] = set()
        super().__init__(cols, rows, seed)

    def _place_obstacles(self) -> set[Position]:
        head_x, head_y = self.snake.body[0]
        candidates = []
        for y in range(1, self.rows - 1):
            for x in range(1, self.cols - 1):
                # chừa đường thẳng phía trước đầu rắn lúc bắt đầu
                if y == head_y and x <= head_x + 6:
                    continue
                if (x, y) in self.snake.occupied:
                    continue
                candidates.append((x, y))
        self.rng.shuffle(candidates)

        chosen: list[Position] = []
        for (x, y) in candidates:
            if len(chosen) >= self.obstacle_count:
                break
            if all(max(abs(x - cx), abs(y - cy)) >= 2 for cx, cy in chosen):
                chosen.append((x, y))
        return set(chosen)

    def reset(self) -> None:
        super().reset()
        self.obstacles = self._place_obstacles()
        self.apple = spawn_apple(
            self.cols, self.rows, self.snake.occupied | self.obstacles, self.rng
        )

    def step(self) -> StepResult:
        if self.status == "RUNNING" and self.snake.next_head() in self.obstacles:
            self.status = "GAME_OVER"
            self._direction_locked = False
            return StepResult(self.status, self.score, False, "WALL")

        result = super().step()

        if result.ate:
            # engine gốc có thể đặt táo lên đá -> sinh lại, tránh cả đá
            self.apple = spawn_apple(
                self.cols, self.rows,
                self.snake.occupied | self.obstacles, self.rng,
            )
            if self.apple is None:
                self.status = "WON"
                result = StepResult("WON", self.score, True, "BOARD_FULL")
        return result
