"""Engine nhiều luật phụ (kế thừa SpecialEngine, KHÔNG sửa engine.py/obstacles.py).

Mỗi luật bật/tắt riêng theo độ khó (xem DIFFICULTIES trong ui.py):

* Đá tự mọc theo thời gian (`grow_ticks`, `max_rocks`), táo đá phá đá (specials.py).
* Cổng dịch chuyển (`portals`): vào cổng này ra cổng kia, dùng xong cặp cổng
  đổi sang chỗ khác. Ô thoát có thân rắn thì thua (reason "SELF").
* Combo táo (`combo`): ăn táo đỏ liên tiếp trong COMBO_SECONDS giây thì táo kế
  được x1,5 rồi x2; để quá lâu combo mất.
* Hai táo chọn một (`twin`): luôn có 2 táo đỏ ở xa nhau; ăn một quả thì quả kia
  biến mất và cả hai được sinh lại.
* Ô băng (`ice_count`): bước vào thì trượt thêm 1 ô theo hướng cũ (không thua).
* Ô mũi tên (`arrow_count`): bước vào thì hướng đi bị đổi theo mũi tên
  (bỏ qua nếu mũi tên chỉ ngược hướng đang đi, để không tự đâm vào cổ).
* Ô bùn (`mud_count`): bước vào bị trừ MUD_PENALTY điểm (không dưới 0); vũng
  bùn đó biến mất và một vũng mới xuất hiện ở chỗ khác. Ngoài ra cứ
  `mud_move_seconds` giây thì toàn bộ bùn đổi sang chỗ khác.
* Nhiệm vụ nhanh (`quests`): nhiệm vụ "ăn N táo trong T giây", xong được thưởng
  điểm; hết giờ mà chưa xong thì bị trừ QUEST_PENALTY điểm (không dưới 0).
  Mỗi ván chỉ có tối đa `max_quests` nhiệm vụ.
* Nhiều táo đặc biệt cùng lúc (`max_specials`): mỗi táo có thời gian tồn tại riêng.

Chỉ engine đổi điểm/thân rắn; UI chỉ đọc các thuộc tính công khai.
"""
from dataclasses import dataclass
from random import Random

from config import POINTS_PER_APPLE
from food import spawn_apple
from models import Direction, Position, StepResult
from rules import is_opposite
from rules import VECTORS as DIRECTIONS
from specials import SpecialEngine, ALL_KINDS

NEW_ROCK_TICKS = 8          # số bước đá mới được UI tô nổi bật
PORTAL_MIN_DIST = 8         # hai cổng cách nhau tối thiểu (Manhattan)
ROCK_HEAD_SAFE = 4          # đá mới cách đầu rắn hơn bấy nhiêu ô (Manhattan)
COMBO_SECONDS = 6
TWIN_MIN_DIST = 6           # hai táo đỏ cách nhau tối thiểu (Manhattan)
MUD_PENALTY = 30
QUEST_PENALTY = 20          # trừ điểm khi hết giờ mà chưa xong nhiệm vụ
QUEST_FIRST_SECONDS = 10    # chờ trước nhiệm vụ đầu tiên
QUEST_COOLDOWN_SECONDS = 8  # nghỉ giữa hai nhiệm vụ
QUESTS = ((2, 8, 30), (3, 15, 50), (4, 22, 80))   # (số táo, giây, điểm thưởng)


def _cheb(a: Position, b: Position) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class Quest:
    need: int
    seconds: int
    reward: int
    left: int            # số bước còn lại
    got: int = 0


class LevelEngine(SpecialEngine):
    def __init__(self, cols: int = 20, rows: int = 15, seed: int | None = None,
                 obstacle_count: int = 0, kinds=ALL_KINDS, chance: float = 0.3,
                 grow_every: int = 0, max_rocks: int = 0, portals: bool = False,
                 grow_ticks: int = 0, rocks_per_apple: int = 0,
                 combo: bool = False, twin: bool = False,
                 ice_count: int = 0, arrow_count: int = 0, quests: bool = False,
                 mud_count: int = 0, max_quests: int | None = None,
                 mud_move_seconds: float = 0, max_specials: int = 1):
        if min(grow_every, max_rocks, grow_ticks, rocks_per_apple,
               ice_count, arrow_count, mud_count) < 0:
            raise ValueError("counts must be >= 0")
        self.grow_every = grow_every
        self.grow_ticks = grow_ticks
        self.rocks_per_apple = rocks_per_apple
        self.ticks = 0
        self.max_rocks = max_rocks
        self.use_portals = portals
        self.use_combo = combo
        self.use_twin = twin
        self.ice_count = ice_count
        self.arrow_count = arrow_count
        self.mud_count = mud_count
        self.mud_move_seconds = mud_move_seconds   # 0 = bùn đứng yên
        self.mud_left = 0
        self.use_quests = quests
        self.max_quests = max_quests          # None = không giới hạn
        self._lrng = Random(None if seed is None else seed + 2)
        self.portals: dict[Position, Position] = {}
        self.rock_age: dict[Position, int] = {}
        self.apples_eaten = 0
        self.apple2: Position | None = None
        self.ice: set[Position] = set()
        self.arrows: dict[Position, Direction] = {}
        self.mud: set[Position] = set()
        self.combo_count = 0
        self.combo_left = 0
        self.quest: Quest | None = None
        self.quest_wait = 0
        self.quests_done = 0
        self.quests_spawned = 0
        super().__init__(cols, rows, seed, obstacle_count, kinds, chance,
                         max_specials)

    # ------------------------------------------------------------------
    def reset(self) -> None:
        super().reset()
        self.portals = {}
        self.rock_age = {}
        self.apples_eaten = 0
        self.ticks = 0
        self.apple2 = None
        self.ice = set()
        self.arrows = {}
        self.mud = set()
        self.mud_left = self._ticks_for(self.mud_move_seconds or 1, 1.0)
        self.combo_count = 0
        self.combo_left = 0
        self.quest = None
        self.quests_done = 0
        self.quests_spawned = 0
        self.quest_wait = self._ticks_for(QUEST_FIRST_SECONDS, 1.0)
        if self.use_portals:
            self.portals = self._place_portals(initial=True)
        self._place_tiles()
        self._fix_apple()
        self._spawn_twin()

    # ---- tiện ích ----------------------------------------------------
    def _tiles(self) -> set[Position]:
        return self.ice | set(self.arrows) | self.mud

    def _extra_blocked(self) -> set[Position]:
        """Ô mà táo không được nằm lên."""
        return set(self.portals) | self._tiles()

    def _special_blocked(self) -> set[Position]:
        """Táo đặc biệt mới cũng tránh cổng, ô đặc biệt và táo đỏ thứ hai."""
        blocked = super()._special_blocked() | self._extra_blocked()
        if self.apple2 is not None:
            blocked.add(self.apple2)
        return blocked

    def _fix_apple(self) -> None:
        if self.apple is not None and self.apple in self._extra_blocked():
            blocked = (self.snake.occupied | self.obstacles | self._extra_blocked()
                       | ({self.apple2} if self.apple2 else set()))
            self.apple = spawn_apple(self.cols, self.rows, blocked, self.rng)

    # ---- cổng --------------------------------------------------------
    def _place_portals(self, initial: bool = False) -> dict[Position, Position]:
        hx, hy = self.snake.body[0]
        special = {s.pos for s in self.specials}
        tiles = self._tiles()
        cells = []
        for y in range(2, self.rows - 2):
            for x in range(2, self.cols - 2):
                p = (x, y)
                if initial and y == hy and x <= hx + 6:   # chừa đường thẳng trước đầu rắn
                    continue
                if p in self.snake.occupied or p in (self.apple, self.apple2) or p in special:
                    continue
                if abs(x - hx) + abs(y - hy) <= 2:        # không đặt sát đầu rắn
                    continue
                if any(_cheb(p, r) < 2 for r in self.obstacles):
                    continue
                if any(_cheb(p, q) < 2 for q in tiles):
                    continue
                cells.append(p)
        self._lrng.shuffle(cells)
        for a in cells:
            for b in cells:
                if _manhattan(a, b) >= PORTAL_MIN_DIST:
                    return {a: b, b: a}
        return {}

    # ---- ô băng / mũi tên ---------------------------------------------
    def _place_tiles(self) -> None:
        want = (["ice"] * self.ice_count + ["arrow"] * self.arrow_count
                + ["mud"] * self.mud_count)
        if not want:
            return
        hx, hy = self.snake.body[0]
        cells = []
        for y in range(2, self.rows - 2):
            for x in range(2, self.cols - 2):
                p = (x, y)
                if y == hy and x <= hx + 6:
                    continue
                if p in self.snake.occupied or p == self.apple:
                    continue
                if any(_cheb(p, r) < 2 for r in self.obstacles):
                    continue
                if any(_cheb(p, q) < 2 for q in self.portals):
                    continue
                cells.append(p)
        self._lrng.shuffle(cells)
        chosen: list[Position] = []
        for p in cells:
            if len(chosen) >= len(want):
                break
            if any(_cheb(p, q) < 2 for q in chosen):   # không hai ô chạm nhau
                continue
            kind = want[len(chosen)]
            if kind == "ice":
                self.ice.add(p)
            elif kind == "mud":
                self.mud.add(p)
            else:
                self.arrows[p] = self._lrng.choice(list(DIRECTIONS))
            chosen.append(p)

    def _respawn_mud(self) -> None:
        hx, hy = self.snake.body[0]
        special = {s.pos for s in self.specials}
        tiles = self._tiles()
        cands = []
        for y in range(2, self.rows - 2):
            for x in range(2, self.cols - 2):
                p = (x, y)
                if p in self.snake.occupied or p in (self.apple, self.apple2) or p in special:
                    continue
                if abs(x - hx) + abs(y - hy) <= 4:
                    continue
                if any(_cheb(p, r) < 2 for r in self.obstacles):
                    continue
                if any(_cheb(p, q) < 2 for q in self.portals):
                    continue
                if any(_cheb(p, q) < 2 for q in tiles):
                    continue
                cands.append(p)
        if cands:
            self.mud.add(self._lrng.choice(cands))

    # ---- táo đôi -------------------------------------------------------
    def _spawn_twin(self) -> None:
        self.apple2 = None
        if not self.use_twin or self.apple is None:
            return
        special = {s.pos for s in self.specials}
        blocked = (self.snake.occupied | self.obstacles | self._extra_blocked()
                   | {self.apple} | special)
        hx, hy = self.snake.body[0]
        ax, ay = self.apple[0] - hx, self.apple[1] - hy
        far = [(x, y) for y in range(self.rows) for x in range(self.cols)
               if (x, y) not in blocked and _manhattan((x, y), self.apple) >= TWIN_MIN_DIST]
        if not far:
            return
        # ưu tiên táo nằm ở hướng khác (tích vô hướng <= 0) để phải chọn đường
        other_way = [c for c in far if (c[0] - hx) * ax + (c[1] - hy) * ay <= 0]
        self.apple2 = self._lrng.choice(other_way or far)

    # ------------------------------------------------------------------
    @property
    def combo_mult(self) -> float:
        return self._mult_for(self.combo_count)

    @property
    def next_combo_mult(self) -> float:
        return self._mult_for(self.combo_count + 1)

    @staticmethod
    def _mult_for(count: int) -> float:
        return 1.0 if count <= 1 else (1.5 if count == 2 else 2.0)

    def combo_seconds(self) -> float:
        return self.combo_left * self.tick_ms * self.slow_factor / 1000.0

    def mud_seconds(self) -> float:
        """Số giây còn lại trước khi bùn đổi chỗ (0 nếu bùn đứng yên)."""
        if not self.mud_move_seconds:
            return 0.0
        return self.mud_left * self.tick_ms * self.slow_factor / 1000.0

    def quest_seconds(self) -> float:
        return 0.0 if self.quest is None else (
            self.quest.left * self.tick_ms * self.slow_factor / 1000.0)

    # ------------------------------------------------------------------
    def step(self) -> StepResult:
        was_running = self.status == "RUNNING"
        result = self._single_step()
        # ô băng: trượt thêm đúng 1 ô trong cùng nhịp
        if (was_running and self.status == "RUNNING" and self.ice
                and self.snake.body[0] in self.ice
                and result.reason in ("MOVE", "EAT")):
            events = list(self.last_events)
            second = self._single_step()
            self.last_events = events + [("ice", "TRƯỢT")] + self.last_events
            result = StepResult(second.status, second.score,
                                result.ate or second.ate, second.reason)
        return result

    def _single_step(self) -> StepResult:
        was_running = self.status == "RUNNING"
        # táo thứ hai: coi như táo chính để engine gốc xử lý việc ăn
        if (was_running and self.apple2 is not None
                and self.snake.next_head() == self.apple2):
            self.apple, self.apple2 = self.apple2, self.apple

        result = super().step()
        if not was_running:
            return result
        if self.status != "RUNNING":              # thua hoặc thắng ở bước này
            self._tick_rocks()
            return result

        # 1) cổng dịch chuyển
        head = self.snake.body[0]
        if head in self.portals:
            dest = self.portals[head]
            if dest in self.snake.occupied:
                self.status = "GAME_OVER"
                self._direction_locked = False
                self._tick_rocks()
                return StepResult(self.status, self.score, False, "SELF")
            self.snake.occupied.discard(head)
            self.snake.body[0] = dest
            self.snake.occupied.add(dest)
            self.last_events.append(("portal", "DỊCH CHUYỂN"))
            moved = self._place_portals()          # cổng đổi sang chỗ khác
            if moved:
                self.portals = moved

        # 2) ô mũi tên: đổi hướng đi (không quay ngược 180 độ)
        head = self.snake.body[0]
        arrow = self.arrows.get(head)
        if arrow and arrow != self.snake.direction \
                and not is_opposite(self.snake.direction, arrow):
            self.snake.direction = arrow
            self.last_events.append(("arrow", {"UP": "↑", "DOWN": "↓",
                                               "LEFT": "←", "RIGHT": "→"}[arrow]))

        # 2b) ô bùn: trừ điểm, vũng này biến mất, vũng mới mọc chỗ khác
        head = self.snake.body[0]
        if head in self.mud:
            self.mud.discard(head)
            lost = min(MUD_PENALTY, self.score)
            self.score -= lost
            self.last_events.append(("mud", f"-{lost}" if lost else "BÙN!"))
            self._respawn_mud()

        # 2c) cứ mud_move_seconds giây thì toàn bộ bùn đổi chỗ
        if self.mud and self.mud_move_seconds:
            self.mud_left -= 1
            if self.mud_left <= 0:
                n = len(self.mud)
                self.mud = set()
                for _ in range(max(n, self.mud_count)):
                    self._respawn_mud()
                self.mud_left = self._ticks_for(self.mud_move_seconds, self.slow_factor)
                self.last_events.append(("mud", "BÙN ĐỔI CHỖ"))

        # 3) táo / táo đặc biệt không nằm trên cổng hoặc ô đặc biệt
        if result.ate:
            self.apple2 = None                     # ăn một quả thì quả kia mất
        self._fix_apple()
        blocked_tiles = self._extra_blocked()
        self.specials = [s for s in self.specials if s.pos not in blocked_tiles]
        if result.ate:
            self._spawn_twin()

        # 4) combo, nhiệm vụ
        self._update_combo(result.ate)
        self._update_quest(result.ate)

        # 5) đá mọc / vỡ
        self._tick_rocks()
        self.ticks += 1
        if result.ate:
            self.apples_eaten += 1
            self._break_rocks(self.rocks_per_apple)
            if (self.grow_every and self.apples_eaten % self.grow_every == 0
                    and len(self.obstacles) < self.max_rocks):
                self._grow_rock()
        if (self.grow_ticks and self.ticks % self.grow_ticks == 0
                and len(self.obstacles) < self.max_rocks):
            self._grow_rock()

        return StepResult(self.status, self.score, result.ate, result.reason)

    # ---- combo ---------------------------------------------------------
    def _update_combo(self, ate: bool) -> None:
        if not self.use_combo:
            return
        if not ate:
            if self.combo_count > 0:
                self.combo_left -= 1
                if self.combo_left <= 0:
                    self.combo_count = 0
            return
        self.combo_count += 1
        self.combo_left = self._ticks_for(COMBO_SECONDS, self.slow_factor)
        mult = self.combo_mult
        if mult <= 1.0:
            return
        for i, (kind, text) in enumerate(self.last_events):
            if kind == "red" and text.startswith("+"):
                points = int(text[1:])             # điểm engine gốc vừa cộng
                bonus = round(points * (mult - 1))
                self.score += bonus
                self.last_events[i] = ("red", f"+{points + bonus} x{mult:g}")
                break

    # ---- nhiệm vụ ------------------------------------------------------
    def _update_quest(self, ate: bool) -> None:
        if not self.use_quests:
            return
        q = self.quest
        if q is None:
            if self.max_quests is not None and self.quests_spawned >= self.max_quests:
                return                              # đã hết lượt nhiệm vụ của ván này
            self.quest_wait -= 1
            if self.quest_wait <= 0:
                self.quests_spawned += 1
                need, secs, reward = self._lrng.choice(QUESTS)
                self.quest = Quest(need, secs, reward, self._ticks_for(secs, 1.0))
            return
        if ate:
            q.got += 1
        if q.got >= q.need:
            self.score += q.reward
            self.quests_done += 1
            self.last_events.append(("quest", f"+{q.reward} NHIỆM VỤ!"))
            self._end_quest()
            return
        q.left -= 1
        if q.left <= 0:
            lost = min(QUEST_PENALTY, self.score)      # trượt nhiệm vụ: trừ điểm
            self.score -= lost
            self.last_events.append(("quest", f"HẾT GIỜ -{lost}" if lost else "HẾT GIỜ"))
            self._end_quest()

    def _end_quest(self) -> None:
        self.quest = None
        self.quest_wait = self._ticks_for(QUEST_COOLDOWN_SECONDS, 1.0)

    # ---- đá --------------------------------------------------------------
    def _tick_rocks(self) -> None:
        self.rock_age = {p: a + 1 for p, a in self.rock_age.items()
                         if p in self.obstacles and a + 1 < NEW_ROCK_TICKS}

    def _break_rocks(self, n: int) -> None:
        for _ in range(n):
            if not self.obstacles:
                return
            rock = self._lrng.choice(sorted(self.obstacles))
            self.obstacles = set(self.obstacles) - {rock}
            self.rock_age.pop(rock, None)
            self.last_events.append(("rock", "ĐÁ VỠ!"))

    def _grow_rock(self) -> None:
        hx, hy = self.snake.body[0]
        special = {s.pos for s in self.specials}
        tiles = self._tiles()
        cands = []
        for y in range(1, self.rows - 1):
            for x in range(1, self.cols - 1):
                p = (x, y)
                if p in self.snake.occupied or p in self.obstacles:
                    continue
                if p in (self.apple, self.apple2) or p in special or p in self.portals:
                    continue
                if abs(x - hx) + abs(y - hy) <= ROCK_HEAD_SAFE:
                    continue
                if any(_cheb(p, r) < 2 for r in self.obstacles):
                    continue
                if any(_cheb(p, q) < 2 for q in self.portals):
                    continue
                if any(_cheb(p, q) < 2 for q in tiles):
                    continue
                cands.append(p)
        if not cands:
            return
        pos = self._lrng.choice(cands)
        self.obstacles = set(self.obstacles) | {pos}
        self.rock_age[pos] = 0
        self.last_events.append(("rock", "ĐÁ MỌC!"))