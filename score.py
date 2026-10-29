"""Người 3: quy tắc điểm và tốc độ, độc lập engine/UI."""
from config import (POINTS_PER_APPLE, TICK_MS, MIN_TICK_MS,
                    SPEED_STEP_MS, APPLES_PER_LEVEL)

def _validate_score(score: int) -> None:
    if type(score) is not int or score < 0:
        raise ValueError("Score must be a nonnegative integer")

def add_apple_score(score: int) -> int:
    """IN: điểm >=0. OUT: điểm mới; 20 -> 30. Không sửa đối tượng nào."""
    _validate_score(score)
    return score + POINTS_PER_APPLE

def level_for_score(score: int) -> int:
    """Mỗi 5 táo tăng 1 cấp: 0..40 -> cấp 1; 50..90 -> cấp 2."""
    _validate_score(score)
    return score // (POINTS_PER_APPLE * APPLES_PER_LEVEL) + 1

def tick_ms_for_score(score: int) -> int:
    """OUT: thời gian giữa 2 bước; thấp hơn là nhanh hơn; tối thiểu 60ms."""
    return max(MIN_TICK_MS, TICK_MS - (level_for_score(score)-1)*SPEED_STEP_MS)
