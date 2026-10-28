"""Engine có TÁO ĐẶC BIỆT (kế thừa ObstacleEngine, KHÔNG sửa engine.py).

Táo đỏ vẫn là táo thường: +10 điểm, dài thêm 1 ô. Ngoài ra, mỗi lần ăn táo đỏ
có xác suất `chance` sinh thêm táo đặc biệt (tối đa `max_specials` cái cùng lúc),
mỗi cái tồn tại một số bước riêng rồi biến mất:

  gold   táo vàng   +30 điểm, chỉ tồn tại ~8 bước
  blue   táo xanh   rắn chạy chậm lại ~5 giây
  purple táo tím    x2 điểm cho táo đỏ trong ~10 giây (táo đỏ = +20)
  poison táo độc    -10 điểm, rắn ngắn đi 2 đốt
  orange táo cam    rắn chạy nhanh ~5 giây
  bomb   táo bom    ~10 giây: đâm vào đá thì đá nổ tung, rắn không thua
                    (chỉ xuất hiện khi bàn có đá)

Táo đặc biệt KHÔNG làm rắn dài thêm. Engine chỉ đếm theo bước (tick); thời gian
"giây" được đổi ra số bước dựa trên `tick_ms` do UI cập nhật mỗi lần xếp lịch.
Chỉ engine được đổi điểm / thân rắn; UI chỉ đọc `special`, `effects`,
`last_events`.
"""
import math
from dataclasses import dataclass
from random import Random

from config import POINTS_PER_APPLE
from models import Position, StepResult
from obstacles import ObstacleEngine
from rules import VECTORS as DIRECTIONS

ALL_KINDS = ("gold", "blue", "purple", "poison", "bomb", "hammer", "orange")

GOLD_POINTS = 30
POISON_POINTS = 10
POISON_SHRINK = 2
MIN_LENGTH = 2            # rắn không bị cắt ngắn hơn mức này
SLOW_SECONDS = 5
X2_SECONDS = 10
BOMB_SECONDS = 10
FAST_SECONDS = 5
SLOW_FACTOR = 1.7         # khi chậm: thời gian mỗi bước nhân hệ số này
FAST_FACTOR = 0.6         # khi nhanh (táo cam): thời gian mỗi bước nhân hệ số này

# số bước táo đặc biệt tồn tại trước khi biến mất
TTL = {"gold": 8, "blue": 16, "purple": 16, "poison": 22, "bomb": 18, "hammer": 18,
       "orange": 16}
# tỉ lệ xuất hiện tương đối giữa các loại
WEIGHT = {"gold": 3, "blue": 2, "purple": 2, "poison": 4, "bomb": 1, "hammer": 4,
          "orange": 2}


@dataclass
class SpecialApple:
    kind: str
    pos: Position
    ttl: int          # số bước còn lại
    max_ttl: int


class SpecialEngine(ObstacleEngine):
    def __init__(self, cols: int = 20, rows: int = 15, seed: int | None = None,
                 obstacle_count: int = 0, kinds=ALL_KINDS, chance: float = 0.3,
                 max_specials: int = 1):
        kinds = tuple(kinds)
        for k in kinds:
            if k not in ALL_KINDS:
                raise ValueError(f"unknown special apple kind: {k}")
        if not 0.0 <= chance <= 1.0:
            raise ValueError("chance must be in [0, 1]")
        if max_specials < 1:
            raise ValueError("max_specials must be >= 1")
        self.special_kinds = kinds
        self.special_chance = chance
        self.max_specials = max_specials       # số táo đặc biệt tối đa cùng lúc
        self._srng = Random(None if seed is None else seed + 1)  # rng riêng cho táo đặc biệt
        self.tick_ms = 200            # UI cập nhật: thời gian cơ bản của 1 bước
        self.specials: list[SpecialApple] = []
        self.effects: dict[str, int] = {}     # "slow"/"x2" -> số bước còn lại
        self.last_events: list[tuple[str, str]] = []
        super().__init__(cols, rows, seed, obstacle_count)

    # ------------------------------------------------------------------
    def reset(self) -> None:
        super().reset()
        self.specials = []
        self.effects = {}
        self.last_events = []

    @property
    def special(self) -> SpecialApple | None:
        """Táo đặc biệt đầu tiên (giữ để tương thích code/test cũ)."""
        return self.specials[0] if self.specials else None

    @special.setter
    def special(self, value: SpecialApple | None) -> None:
        self.specials = [] if value is None else [value]

    def _special_blocked(self) -> set[Position]:
        """Ô mà táo đặc biệt mới không được nằm lên (lớp con có thể mở rộng)."""
        blocked = set(self.snake.occupied) | set(self.obstacles)
        if self.apple is not None:
            blocked.add(self.apple)
        blocked.update(sp.pos for sp in self.specials)
        return blocked

    @property
    def slow_factor(self) -> float:
        """Hệ số nhân thời gian mỗi bước (>1 khi bị làm chậm, <1 khi chạy nhanh)."""
        factor = 1.0
        if self.effects.get("slow", 0) > 0:
            factor *= SLOW_FACTOR
        if self.effects.get("fast", 0) > 0:
            factor *= FAST_FACTOR
        return factor

    def effect_seconds(self, name: str) -> float:
        """Số giây còn lại (ước lượng) của hiệu ứng 'slow', 'fast', 'x2' hoặc 'bomb'."""
        return self.effects.get(name, 0) * self.tick_ms * self.slow_factor / 1000.0

    # ------------------------------------------------------------------
    def step(self) -> StepResult:
        self.last_events = []
        was_running = self.status == "RUNNING"
        # đang có bom: đá ngay trước mặt nổ tung thay vì làm rắn thua
        if was_running and self.effects.get("bomb", 0) > 0:
            nxt = self.snake.next_head()
            if nxt in self.obstacles:
                self.obstacles = set(self.obstacles) - {nxt}
                self.last_events.append(("bomb", "BÙM!"))
        result = super().step()
        if not was_running or result.reason not in ("MOVE", "EAT", "BOARD_FULL"):
            return result

        picked: set[str] = set()

        if result.ate:                                  # táo đỏ
            points = POINTS_PER_APPLE
            if self.effects.get("x2", 0) > 0:
                self.score += POINTS_PER_APPLE          # gấp đôi: +10 nữa
                points *= 2
            self.last_events.append(("red", f"+{points}"))
            # táo đỏ mới đè lên táo đặc biệt -> bỏ táo đặc biệt đó
            self.specials = [s for s in self.specials if s.pos != self.apple]

        head = self.snake.body[0]
        remaining: list[SpecialApple] = []
        for sp in self.specials:
            if head == sp.pos:                          # ăn táo đặc biệt này
                key = self._apply(sp)
                if key:
                    picked.add(key)
            else:                                       # mỗi táo đếm ngược riêng
                sp.ttl -= 1
                if sp.ttl > 0:
                    remaining.append(sp)
        self.specials = remaining

        if (result.ate and self.status == "RUNNING"
                and len(self.specials) < self.max_specials):
            self._maybe_spawn()

        for name in list(self.effects):                 # đếm ngược, trừ cái vừa nhặt
            if name in picked:
                continue
            self.effects[name] -= 1
            if self.effects[name] <= 0:
                del self.effects[name]

        return StepResult(self.status, self.score, result.ate, result.reason)

    # ------------------------------------------------------------------
    def _ticks_for(self, seconds: float, factor: float) -> int:
        return max(1, math.ceil(seconds * 1000 / (self.tick_ms * factor)))

    def _apply(self, sp: SpecialApple) -> str | None:
        """Áp hiệu ứng táo vừa ăn. Trả tên hiệu ứng có thời hạn (nếu có)."""
        if sp.kind == "gold":
            self.score += GOLD_POINTS
            self.last_events.append(("gold", f"+{GOLD_POINTS}"))
        elif sp.kind == "blue":
            factor = SLOW_FACTOR * (FAST_FACTOR if "fast" in self.effects else 1.0)
            self.effects["slow"] = self._ticks_for(SLOW_SECONDS, factor)
            self.last_events.append(("blue", "CHẬM"))
            return "slow"
        elif sp.kind == "orange":
            factor = FAST_FACTOR * (SLOW_FACTOR if "slow" in self.effects else 1.0)
            self.effects["fast"] = self._ticks_for(FAST_SECONDS, factor)
            self.last_events.append(("orange", "NHANH"))
            return "fast"
        elif sp.kind == "purple":
            factor = self.slow_factor
            self.effects["x2"] = self._ticks_for(X2_SECONDS, factor)
            self.last_events.append(("purple", "x2 ĐIỂM"))
            return "x2"
        elif sp.kind == "poison":
            self.score = max(0, self.score - POISON_POINTS)
            self._shrink(POISON_SHRINK)
            self.last_events.append(("poison", f"-{POISON_POINTS}"))
        elif sp.kind == "bomb":
            factor = self.slow_factor
            self.effects["bomb"] = self._ticks_for(BOMB_SECONDS, factor)
            self.last_events.append(("bomb", "BOM 10s"))
            return "bomb"
        elif sp.kind == "hammer":
            if self.obstacles:
                rock = self._srng.choice(sorted(self.obstacles))
                self.obstacles = set(self.obstacles) - {rock}
                ages = getattr(self, "rock_age", None)
                if ages:
                    ages.pop(rock, None)
            self.last_events.append(("hammer", "ĐÁ VỠ!"))
        return None

    def _shrink(self, n: int) -> None:
        body, occupied = self.snake.body, self.snake.occupied
        for _ in range(n):
            if len(body) <= MIN_LENGTH:
                break
            occupied.discard(body.pop())

    def _maybe_spawn(self) -> None:
        """Sau khi ăn táo đỏ: có xác suất `chance` sinh 1..(chỗ còn trống) táo
        đặc biệt, tổng số táo đặc biệt không vượt quá `max_specials`."""
        room = self.max_specials - len(self.specials)
        if room <= 0 or not self.special_kinds:
            return
        if self._srng.random() >= self.special_chance:
            return
        count = self._srng.randint(1, room) if room > 1 else 1
        for _ in range(count):
            self._spawn_one()

    def _spawn_one(self) -> None:
        kinds = [k for k in self.special_kinds
                 if k not in ("bomb", "hammer") or self.obstacles]
        # ưu tiên loại chưa có trên bàn để các táo cùng lúc đa dạng hơn
        present = {s.kind for s in self.specials}
        fresh = [k for k in kinds if k not in present]
        kinds = fresh or kinds
        if not kinds:
            return
        kind = self._srng.choices(kinds, weights=[WEIGHT[k] for k in kinds])[0]
        ttl = TTL[kind]

        hx, hy = self.snake.body[0]
        blocked = self._special_blocked()
        reach = max(3, ttl - 3)                         # đủ gần để kịp tới nơi
        cands = [
            (x, y)
            for y in range(self.rows) for x in range(self.cols)
            if (x, y) not in blocked and 2 <= abs(x - hx) + abs(y - hy) <= reach
        ]
        if not cands:
            return
        dx, dy = DIRECTIONS[self.snake.direction]
        ahead = [c for c in cands if (c[0] - hx) * dx + (c[1] - hy) * dy >= 0]
        pos = self._srng.choice(ahead or cands)
        self.specials.append(SpecialApple(kind, pos, ttl, ttl))