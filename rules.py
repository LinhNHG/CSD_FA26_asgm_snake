"""
Game rules and collision checking for the Snake game.

This module contains pure functions.
It only checks game rules and returns results.
It does not modify the snake, game state,
direction, or input data.
"""

from models import Position, Direction


# ============================================================
# CONSTANTS
# ============================================================

VALID_DIRECTIONS = {
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT"
}


OPPOSITE_DIRECTIONS = {
    "UP": "DOWN",
    "DOWN": "UP",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT"
}


# ============================================================
# VALIDATE POSITION
# ============================================================

def validate_position(pos: Position) -> None:
    """
    Validate a position.

    A valid position must:
    - be a tuple
    - contain exactly 2 elements
    - contain 2 integer coordinates

    Raises:
        ValueError: if the position is invalid.
    """

    # Position must be a tuple
    if not isinstance(pos, tuple):
        raise ValueError(
            "Position must be a tuple of 2 integers"
        )

    # Position must contain exactly 2 elements
    if len(pos) != 2:
        raise ValueError(
            "Position must contain exactly 2 elements"
        )

    x, y = pos

    # bool is not accepted as a coordinate
    if isinstance(x, bool) or isinstance(y, bool):
        raise ValueError(
            "Position coordinates must be integers"
        )

    # Both coordinates must be integers
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError(
            "Position coordinates must be integers"
        )


# ============================================================
# VALIDATE DIRECTION
# ============================================================

def validate_direction(direction: Direction) -> None:
    """
    Validate a snake direction.

    Valid directions:
        UP
        DOWN
        LEFT
        RIGHT

    Raises:
        ValueError: if the direction is invalid.
    """

    # Direction must be a string
    if not isinstance(direction, str):
        raise ValueError(
            "Direction must be a string"
        )

    # Direction must be one of the valid directions
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            "Direction must be UP, DOWN, LEFT, or RIGHT"
        )


# ============================================================
# 1. IS INSIDE
# ============================================================

def is_inside(
    pos: Position,
    cols: int,
    rows: int
) -> bool:
    """
    Check whether a position is inside the game board.

    Parameters:
        pos:
            Position in the form (x, y).

        cols:
            Number of columns of the board.

        rows:
            Number of rows of the board.

    Returns:
        True:
            Position is inside the board.

        False:
            Position is outside the board.

    Raises:
        ValueError:
            If position or board size is invalid.
    """

    # --------------------------------------------------------
    # Step 1:
    # Validate the position.
    # --------------------------------------------------------

    validate_position(pos)

    # --------------------------------------------------------
    # Step 2:
    # Validate board dimensions.
    # cols and rows must be positive integers.
    # --------------------------------------------------------

    if isinstance(cols, bool) or isinstance(rows, bool):
        raise ValueError(
            "cols and rows must be positive integers"
        )

    if not isinstance(cols, int) or not isinstance(rows, int):
        raise ValueError(
            "cols and rows must be positive integers"
        )

    if cols <= 0 or rows <= 0:
        raise ValueError(
            "cols and rows must be positive integers"
        )

    # --------------------------------------------------------
    # Step 3:
    # Get x and y coordinates.
    # --------------------------------------------------------

    x, y = pos

    # --------------------------------------------------------
    # Step 4:
    # Check all four board boundaries.
    #
    # Left:
    #     x >= 0
    #
    # Right:
    #     x < cols
    #
    # Top:
    #     y >= 0
    #
    # Bottom:
    #     y < rows
    # --------------------------------------------------------

    return 0 <= x < cols and 0 <= y < rows


# ============================================================
# 2. IS OPPOSITE
# ============================================================

def is_opposite(
    current: Direction,
    requested: Direction
) -> bool:
    """
    Check whether requested direction is opposite
    to the current direction.

    Returns:
        True:
            The two directions are opposite.

        False:
            The two directions are not opposite.

    Raises:
        ValueError:
            If either direction is invalid.
    """

    # --------------------------------------------------------
    # Step 1:
    # Validate current direction.
    # --------------------------------------------------------

    validate_direction(current)

    # --------------------------------------------------------
    # Step 2:
    # Validate requested direction.
    # --------------------------------------------------------

    validate_direction(requested)

    # --------------------------------------------------------
    # Step 3:
    # Find the opposite direction of current.
    #
    # Example:
    #     RIGHT -> LEFT
    #     UP    -> DOWN
    # --------------------------------------------------------

    opposite = OPPOSITE_DIRECTIONS[current]

    # --------------------------------------------------------
    # Step 4:
    # Compare the requested direction with the opposite.
    # --------------------------------------------------------

    return opposite == requested


# ============================================================
# 3. HITS BODY
# ============================================================

def hits_body(
    next_head: Position,
    tail: Position,
    occupied: set[Position],
    grow: bool
) -> bool:
    """
    Check whether the next head position hits the
    snake body.

    Parameters:
        next_head:
            Position of the next snake head.

        tail:
            Current position of the snake tail.

        occupied:
            Set of cells currently occupied by the snake.

        grow:
            True:
                Snake grows during this move.

            False:
                Snake does not grow during this move.

    Returns:
        True:
            The next head collides with the body.

        False:
            There is no body collision.

    Raises:
        ValueError:
            If the input position or grow value is invalid.
    """

    # --------------------------------------------------------
    # Step 1:
    # Validate positions.
    # --------------------------------------------------------

    validate_position(next_head)
    validate_position(tail)

    # --------------------------------------------------------
    # Step 2:
    # Validate grow.
    # --------------------------------------------------------

    if not isinstance(grow, bool):
        raise ValueError(
            "grow must be a boolean"
        )

    # --------------------------------------------------------
    # Step 3:
    # Check whether next_head is inside occupied.
    #
    # If it is not occupied by the snake,
    # there is no body collision.
    # --------------------------------------------------------

    if next_head not in occupied:
        return False

    # --------------------------------------------------------
    # Step 4:
    # Check the special tail case.
    # --------------------------------------------------------

    if next_head == tail:

        # ----------------------------------------------------
        # If the snake does NOT grow:
        #
        # The old tail will be removed during this move.
        # Therefore, entering the old tail is allowed.
        # ----------------------------------------------------

        if not grow:
            return False

        # ----------------------------------------------------
        # If the snake DOES grow:
        #
        # The tail remains in place.
        # Therefore, entering the tail is a collision.
        # ----------------------------------------------------

        return True

    # --------------------------------------------------------
    # Step 5:
    # next_head is occupied by another body segment.
    # Therefore, there is a collision.
    # --------------------------------------------------------

    return True
