"""Test cho engine.py (người 4).

Chạy từ thư mục gốc:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from random import Random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import GameEngine
from food import spawn_apple
from models import Snapshot, StepResult
from snake import Snake


def make_engine(cols=8, rows=6, seed=0, body=None, direction="RIGHT", apple=None):
    """Dựng engine rồi đặt trạng thái cụ thể cho test (chỉ dùng trong test)."""
    game = GameEngine(cols, rows, seed)
    if body is not None:
        game.snake = Snake(body, direction)
    game.apple = apple
    return game


class TestInitAndReset(unittest.TestCase):
    def test_initial_state(self):
        g = GameEngine(seed=1)
        s = g.snapshot()
        self.assertEqual(s.body, ((2, 1), (1, 1), (0, 1)))
        self.assertEqual(s.direction, "RIGHT")
        self.assertEqual(s.score, 0)
        self.assertEqual(s.status, "RUNNING")
        self.assertIsNotNone(s.apple)
        self.assertNotIn(s.apple, s.body)

    def test_invalid_board_size(self):
        for cols, rows in [(3, 15), (20, 2), (0, 0), (-1, 5), (True, 5), (20, False),
                           (4.0, 5), ("20", 15), (None, 15)]:
            with self.subTest(cols=cols, rows=rows):
                with self.assertRaises(ValueError):
                    GameEngine(cols, rows)

    def test_minimum_board_is_valid(self):
        g = GameEngine(4, 3, seed=0)
        self.assertEqual(g.step().status, "RUNNING")

    def test_reset_returns_none_and_restores_state(self):
        g = make_engine(apple=(3, 1), seed=5)
        g.step()  # ăn táo
        g.change_direction("DOWN")
        self.assertIsNone(g.reset())
        s = g.snapshot()
        self.assertEqual((s.body, s.direction, s.score, s.status),
                         (((2, 1), (1, 1), (0, 1)), "RIGHT", 0, "RUNNING"))
        self.assertNotIn(s.apple, s.body)

    def test_reset_after_game_over(self):
        g = make_engine(cols=4, rows=3, apple=(0, 0))
        g.step()
        g.step()  # chạm tường
        self.assertEqual(g.status, "GAME_OVER")
        g.reset()
        self.assertEqual(g.status, "RUNNING")
        self.assertEqual(g.step().reason, "MOVE")

    def test_reset_clears_direction_lock(self):
        g = GameEngine(seed=2)
        self.assertTrue(g.change_direction("DOWN"))
        g.reset()
        self.assertTrue(g.change_direction("UP"))

    def test_reset_keeps_rng_instead_of_reseeding(self):
        g = GameEngine(seed=7)
        first = g.snapshot().apple
        g.reset()
        second = g.snapshot().apple
        rng = Random(7)
        occupied = {(2, 1), (1, 1), (0, 1)}
        self.assertEqual(spawn_apple(20, 15, occupied, rng), first)
        self.assertEqual(spawn_apple(20, 15, occupied, rng), second)

    def test_same_seed_same_game(self):
        a, b = GameEngine(seed=42), GameEngine(seed=42)
        self.assertEqual(a.snapshot(), b.snapshot())


class TestChangeDirection(unittest.TestCase):
    def test_accept_perpendicular(self):
        g = GameEngine(seed=0)
        result = g.change_direction("UP")
        self.assertIs(result, True)
        self.assertEqual(g.snapshot().direction, "UP")

    def test_reject_same_direction_does_not_lock(self):
        g = GameEngine(seed=0)
        self.assertIs(g.change_direction("RIGHT"), False)
        self.assertTrue(g.change_direction("UP"))

    def test_reject_opposite_does_not_lock(self):
        g = GameEngine(seed=0)
        self.assertIs(g.change_direction("LEFT"), False)
        self.assertEqual(g.snapshot().direction, "RIGHT")
        self.assertTrue(g.change_direction("DOWN"))

    def test_invalid_direction_raises_and_changes_nothing(self):
        g = GameEngine(seed=0)
        for bad in ["up", "NORTH", "", None, 1, ("UP",)]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    g.change_direction(bad)
        self.assertEqual(g.snapshot().direction, "RIGHT")
        self.assertTrue(g.change_direction("UP"))  # chưa bị khóa

    def test_only_one_change_per_tick(self):
        """Khóa đổi hướng trong cùng tick."""
        g = make_engine(apple=(7, 5))
        self.assertTrue(g.change_direction("UP"))
        self.assertFalse(g.change_direction("RIGHT"))  # vuông góc với UP nhưng bị khóa
        self.assertFalse(g.change_direction("DOWN"))   # ngược UP
        self.assertFalse(g.change_direction("LEFT"))
        self.assertEqual(g.snapshot().direction, "UP")
        g.step()
        self.assertEqual(g.snake.body[0], (2, 0))      # đi lên đúng một ô
        self.assertTrue(g.change_direction("RIGHT"))   # tick mới: nhận lại

    def test_lock_prevents_instant_u_turn(self):
        """RIGHT -> UP -> LEFT trong một tick sẽ tự cắn thân nếu không khóa."""
        g = make_engine(apple=(7, 5))
        g.change_direction("UP")
        self.assertFalse(g.change_direction("LEFT"))
        self.assertEqual(g.step().reason, "MOVE")

    def test_game_over_rejects_direction(self):
        g = make_engine(cols=4, rows=3, apple=(0, 0))
        g.step()
        g.step()
        self.assertEqual(g.status, "GAME_OVER")
        self.assertIs(g.change_direction("UP"), False)

    def test_won_rejects_direction(self):
        g = full_board_one_step_from_win()
        g.step()
        self.assertEqual(g.status, "WON")
        self.assertIs(g.change_direction("UP"), False)

    def test_game_over_still_validates_input(self):
        g = make_engine(cols=4, rows=3, apple=(0, 0))
        g.step()
        g.step()
        with self.assertRaises(ValueError):
            g.change_direction("bad")


def full_board_one_step_from_win():
    """Bàn 4x3: rắn dài 11, ô trống duy nhất (3,2) chứa táo, ngay trước đầu."""
    body = [(2, 2), (1, 2), (0, 2), (0, 1), (1, 1), (2, 1), (3, 1),
            (3, 0), (2, 0), (1, 0), (0, 0)]
    return make_engine(cols=4, rows=3, body=body, direction="RIGHT", apple=(3, 2))


class TestStep(unittest.TestCase):
    def test_normal_move(self):
        g = make_engine(apple=(7, 5))
        r = g.step()
        self.assertIsInstance(r, StepResult)
        self.assertEqual(r, StepResult("RUNNING", 0, False, "MOVE"))
        self.assertEqual(list(g.snake.body), [(3, 1), (2, 1), (1, 1)])
        self.assertEqual(g.snake.occupied, {(3, 1), (2, 1), (1, 1)})
        self.assertEqual(g.apple, (7, 5))  # táo giữ nguyên

    def test_eat_apple(self):
        g = make_engine(apple=(3, 1))
        r = g.step()
        self.assertEqual(r, StepResult("RUNNING", 10, True, "EAT"))
        self.assertEqual(tuple(g.snake.body), ((3, 1), (2, 1), (1, 1), (0, 1)))
        self.assertEqual(g.score, 10)
        self.assertIsNotNone(g.apple)
        self.assertNotIn(g.apple, g.snake.occupied)
        self.assertNotEqual(g.apple, (3, 1))

    def test_eat_twice_scores_twenty(self):
        g = make_engine(apple=(3, 1))
        g.step()
        g.apple = (4, 1)
        r = g.step()
        self.assertEqual((r.score, r.reason), (20, "EAT"))
        self.assertEqual(len(g.snake.body), 5)

    def test_wall_collision(self):
        g = make_engine(cols=4, rows=3, apple=(0, 0))
        self.assertEqual(g.step().reason, "MOVE")      # đầu -> (3,1)
        r = g.step()                                    # đầu -> (4,1) ngoài bàn
        self.assertEqual(r, StepResult("GAME_OVER", 0, False, "WALL"))
        self.assertEqual(list(g.snake.body), [(3, 1), (2, 1), (1, 1)])  # không di chuyển

    def test_all_four_walls(self):
        cases = {
            "UP": ((1, 0), (2, 0), "UP"),
            "DOWN": ((1, 2), (1, 1), "DOWN"),
            "LEFT": ((0, 1), (1, 1), "LEFT"),
            "RIGHT": ((3, 1), (2, 1), "RIGHT"),
        }
        for d, (head, neck, direction) in cases.items():
            with self.subTest(direction=d):
                if d in ("UP", "DOWN"):
                    neck = (head[0], head[1] + (1 if d == "UP" else -1))
                g = make_engine(cols=4, rows=3, body=[head, neck], direction=direction,
                                apple=(3, 0) if d != "RIGHT" else (0, 0))
                r = g.step()
                self.assertEqual((r.status, r.reason), ("GAME_OVER", "WALL"))

    def test_self_collision(self):
        body = [(3, 2), (3, 3), (2, 3), (2, 2), (2, 1)]
        g = make_engine(body=body, direction="UP", apple=(7, 5))
        self.assertTrue(g.change_direction("LEFT"))     # đầu -> (2,2) là thân
        r = g.step()
        self.assertEqual(r, StepResult("GAME_OVER", 0, False, "SELF"))
        self.assertEqual(list(g.snake.body), body)

    def test_enter_old_tail_cell_when_not_growing(self):
        body = [(1, 1), (1, 2), (2, 2), (2, 1)]         # vòng vuông 2x2, đuôi (2,1)
        g = make_engine(body=body, direction="UP", apple=(7, 5))
        g.snake = Snake(body, "UP")
        self.assertTrue(g.change_direction("RIGHT"))    # đầu -> (2,1) = ô đuôi
        r = g.step()
        self.assertEqual((r.status, r.reason), ("RUNNING", "MOVE"))
        self.assertEqual(g.snake.body[0], (2, 1))

    def test_enter_tail_cell_while_eating_is_collision(self):
        body = [(1, 1), (1, 2), (2, 2), (2, 1)]
        g = make_engine(body=body, direction="UP", apple=(2, 1))  # táo "trên" đuôi (state dựng)
        g.change_direction("RIGHT")
        r = g.step()
        self.assertEqual((r.status, r.reason), ("GAME_OVER", "SELF"))

    def test_win_when_board_full(self):
        g = full_board_one_step_from_win()
        r = g.step()
        self.assertEqual(r, StepResult("WON", 10, True, "BOARD_FULL"))
        self.assertIsNone(g.apple)
        self.assertEqual(len(g.snake.body), 12)
        self.assertEqual(len(g.snake.occupied), 12)

    def test_step_after_finish_changes_nothing(self):
        for build in (full_board_one_step_from_win,
                      lambda: make_engine(cols=4, rows=3, apple=(0, 0))):
            g = build()
            while g.status == "RUNNING":
                g.step()
            before = g.snapshot()
            for _ in range(3):
                r = g.step()
                self.assertEqual(r, StepResult(before.status, before.score, False, "NO_CHANGE"))
            self.assertEqual(g.snapshot(), before)

    def test_step_unlocks_direction(self):
        g = make_engine(apple=(7, 5))
        g.change_direction("UP")
        g.step()
        self.assertFalse(g._direction_locked)

    def test_game_over_step_also_clears_lock(self):
        g = make_engine(cols=4, rows=3, apple=(0, 0))
        g.step()
        g.change_direction("UP")   # đầu (3,1) -> lên (3,0): vẫn trong bàn
        g.step()
        g.change_direction("RIGHT")
        r = g.step()               # (3,0) -> (4,0) ngoài bàn
        self.assertEqual(r.reason, "WALL")
        self.assertFalse(g._direction_locked)

    def test_only_engine_changes_score_and_status(self):
        """Snake/rules/food không đụng tới score hay status."""
        g = make_engine(apple=(3, 1))
        score, status = g.score, g.status
        g.snake.next_head()
        g.snake.would_hit_self((3, 1), True)
        spawn_apple(g.cols, g.rows, g.snake.occupied, g.rng)
        self.assertEqual((g.score, g.status), (score, status))


class TestSnapshot(unittest.TestCase):
    def test_returns_snapshot_with_tuple_body(self):
        s = GameEngine(seed=3).snapshot()
        self.assertIsInstance(s, Snapshot)
        self.assertIsInstance(s.body, tuple)

    def test_snapshot_does_not_change_state(self):
        g = GameEngine(seed=3)
        a = g.snapshot()
        b = g.snapshot()
        self.assertEqual(a, b)
        self.assertEqual(g.score, 0)

    def test_snapshot_is_a_copy(self):
        g = make_engine(apple=(7, 5))
        old = g.snapshot()
        g.step()
        self.assertEqual(old.body, ((2, 1), (1, 1), (0, 1)))
        self.assertNotEqual(old.body, g.snapshot().body)
        with self.assertRaises(Exception):
            old.score = 99  # dataclass frozen

    def test_snapshot_after_win_has_no_apple(self):
        g = full_board_one_step_from_win()
        g.step()
        s = g.snapshot()
        self.assertEqual((s.status, s.apple), ("WON", None))


class TestRandomPlay(unittest.TestCase):
    def test_invariants_over_many_random_games(self):
        for seed in range(200):
            rng = Random(seed)
            g = GameEngine(6, 5, seed)
            for _ in range(300):
                if rng.random() < 0.4:
                    g.change_direction(rng.choice(["UP", "DOWN", "LEFT", "RIGHT"]))
                before_status, before_score = g.status, g.score
                r = g.step()
                snap = g.snapshot()
                self.assertEqual(set(snap.body), g.snake.occupied)
                self.assertEqual(len(snap.body), len(set(snap.body)))
                self.assertTrue(all(0 <= x < 6 and 0 <= y < 5 for x, y in snap.body))
                self.assertEqual(snap.score, 10 * (len(snap.body) - 3))
                if snap.apple is not None:
                    self.assertNotIn(snap.apple, snap.body)
                if before_status != "RUNNING":
                    self.assertEqual((r.reason, g.score), ("NO_CHANGE", before_score))
                self.assertEqual(r.status, g.status)
                if g.status != "RUNNING":
                    break


if __name__ == "__main__":
    unittest.main(verbosity=2)
