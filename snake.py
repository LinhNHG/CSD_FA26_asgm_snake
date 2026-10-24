
from collections import deque


DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0)
}


class Snake:
    def __init__(self, body, direction):
        """
        body: danh sach toa do tu dau den duoi
        direction: UP, DOWN, LEFT hoac RIGHT
        """

        if direction not in DIRECTIONS:
            raise ValueError("Invalid direction")

        if not body:
            raise ValueError("Snake body cannot be empty")

        positions = []

        for pos in body:
            if (
                not isinstance(pos, (tuple, list))
                or len(pos) != 2
                or any(type(v) is not int for v in pos)
            ):
                raise ValueError("Invalid position")

            positions.append(tuple(pos))

        if len(set(positions)) != len(positions):
            raise ValueError("Snake body contains duplicate positions")

        for i in range(len(positions) - 1):
            x1, y1 = positions[i]
            x2, y2 = positions[i + 1]

            if abs(x1 - x2) + abs(y1 - y2) != 1:
                raise ValueError("Snake body is not connected")

        # Khong cho phep than ran co it hon 2 dot
        if len(positions) < 2:
            raise ValueError("Snake body must contain at least 2 segments")

        # Kiem tra huong dau ran
        head_x, head_y = positions[0]
        neck_x, neck_y = positions[1]

        expected_direction = (
            head_x - neck_x,
            head_y - neck_y
        )

        if DIRECTIONS[direction] != expected_direction:
            raise ValueError("Direction does not match snake body")

        self.body = deque(positions)
        self.occupied = set(positions)
        self.direction = direction

    @staticmethod
    def _validate_position(pos):
        """Kiem tra toa do gom dung 2 so nguyen."""
        if (
            not isinstance(pos, (tuple, list))
            or len(pos) != 2
            or any(type(v) is not int for v in pos)
        ):
            raise ValueError("Position must contain exactly 2 integers")

        return tuple(pos)

    @staticmethod
    def _validate_grow(grow):
        """grow chi duoc la True hoac False."""
        if type(grow) is not bool:
            raise ValueError("grow must be a boolean")

    def next_head(self):
        """Tinh toa do dau ran tiep theo, khong thay doi than ran."""
        x, y = self.body[0]
        dx, dy = DIRECTIONS[self.direction]

        return (x + dx, y + dy)

    def would_hit_self(self, pos, grow):
        """
        Kiem tra dau moi co cham than ran khong.
        Khong thay doi trang thai ran.
        """
        pos = self._validate_position(pos)
        self._validate_grow(grow)

        if pos not in self.occupied:
            return False

        # Duoi sap roi di nen co the di vao o duoi cu
        if not grow and pos == self.body[-1]:
            return False

        return True

    def advance(self, pos, grow):
        """
        Cap nhat than ran tai vi tri dau moi.

        pos phai bang next_head() da duoc engine tinh.
        grow=True: giu duoi, tang chieu dai.
        grow=False: bo duoi cu, them dau moi.

        Tra ve None. Input sai se bao ValueError
        truoc khi thay doi than ran.
        """
        pos = self._validate_position(pos)
        self._validate_grow(grow)

        # Tranh di chuyen den mot o khong dung huong
        if pos != self.next_head():
            raise ValueError("Position must equal next_head()")

        # Kiem tra va cham truoc khi sua du lieu
        if self.would_hit_self(pos, grow):
            raise ValueError("New head would hit the snake body")

        # Cap nhat duoi neu khong tang chieu dai
        if not grow:
            tail = self.body.pop()
            self.occupied.remove(tail)

        # Them dau moi
        self.body.appendleft(pos)
        self.occupied.add(pos)
