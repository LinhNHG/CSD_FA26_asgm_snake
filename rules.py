from models import Position, Direction

VECTORS: dict[Direction, Position] = {
    "UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)
}

def validate_position(pos: Position) -> None:
    if (not isinstance(pos, tuple) or len(pos) != 2
            or any(type(value) is not int for value in pos)):
        raise ValueError("Position must be an (x, y) tuple of integers")

def validate_direction(direction: Direction) -> None:
    if not isinstance(direction, str) or direction not in VECTORS:
        raise ValueError("Direction must be UP, DOWN, LEFT or RIGHT")

def is_inside(pos: Position, cols: int, rows: int) -> bool:
    """IN: (x,y), kích thước dương. OUT: bool; O(1)."""
    validate_position(pos)
    if type(cols) is not int or type(rows) is not int or cols <= 0 or rows <= 0:
        raise ValueError("Board dimensions must be positive integers")
    return 0 <= pos[0] < cols and 0 <= pos[1] < rows

def is_opposite(current: Direction, requested: Direction) -> bool:
    """RIGHT/LEFT -> True; RIGHT/UP và RIGHT/RIGHT -> False."""
    validate_direction(current)
    validate_direction(requested)
    dx, dy = VECTORS[current]
    rx, ry = VECTORS[requested]
    return dx + rx == 0 and dy + ry == 0

def hits_body(next_head: Position, tail: Position,
              occupied: set[Position], grow: bool) -> bool:
    """Trung bình O(1). Được vào đuôi cũ nếu đuôi rời trong cùng tick."""
    return next_head in occupied and not (next_head == tail and not grow)
