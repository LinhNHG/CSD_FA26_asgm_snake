import math
import tkinter as tk

import helpbot
import leaderboard
from config import CELL_SIZE, POINTS_PER_APPLE, TICK_MS
from engine import GameEngine
from models import Snapshot
from obstacles import ObstacleEngine
from specials import SpecialEngine
from levels import LevelEngine

# ----------------------------------------------------------------------
# Hằng số
# ----------------------------------------------------------------------
KEY_TO_DIRECTION = {
    "Up": "UP", "Down": "DOWN", "Left": "LEFT", "Right": "RIGHT",
    "w": "UP", "W": "UP", "s": "DOWN", "S": "DOWN",
    "a": "LEFT", "A": "LEFT", "d": "RIGHT", "D": "RIGHT",
}
ZOOM_SIZES = (22, 26, 30, 36, 42, 48, 56, 64)   # kích thước 1 ô khi thu/phóng
BASE_W, BASE_H = 624, 646                   # cỡ cửa sổ của menu và các màn phụ
MIN_W, MIN_H = 480, 380                     # cỡ nhỏ nhất khi kéo cửa sổ ở màn game
CHROME_W, CHROME_H = 24, 196                # phần ngoài bàn chơi (viền + thanh trên/dưới)
DIR_VECTORS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

FONT = "Arial"  # được đổi sang Segoe UI khi máy có font này

MAX_NAME_LEN = 15
TOP_N = 10
COUNTDOWN_FROM = 3
EFFECT_TICKS = 6          # số tick chữ "+10" bay lên rồi mờ
MIN_TICK_MS = 80          # thời gian mỗi bước nhỏ nhất = rắn nhanh nhất (80 ms ≈ 12 bước/giây)
SPEEDUP_FREE_APPLES = 5   # ăn bấy nhiêu táo đầu tiên thì tốc độ vẫn giữ nguyên
SPEEDUP_MS_PER_APPLE = 4  # từ quả tiếp theo, mỗi quả rút ngắn bấy nhiêu ms mỗi bước => rắn CHẠY NHANH HƠN

# Độ khó: tốc độ gốc (ms/tick) và số vật cản
DIFFICULTIES = {
    "Dễ": {"tick": 260, "obstacles": 0, "specials": ("gold", "blue", "purple", "orange"),
           "special_chance": 0.7, "max_specials": 3,
           "grow_every": 0, "grow_ticks": 0,
           "rocks_per_apple": 0, "max_rocks": 0, "portals": False,
           "combo": True, "quests": True, "max_quests": 2},
    "Vừa": {"tick": 220, "obstacles": 0,
            "specials": ("gold", "blue", "purple", "poison", "orange"),
            "special_chance": 0.7, "max_specials": 3,
            "grow_every": 0, "grow_ticks": 0, "rocks_per_apple": 0,
            "max_rocks": 0, "portals": True, "combo": True, "twin": True,
            "ice_count": 3, "mud_count": 3, "mud_move_seconds": 15, "quests": True,
            "max_quests": 2},
    "Khó": {"tick": 180, "obstacles": 6,
            "specials": ("gold", "blue", "purple", "poison", "bomb", "hammer", "orange"),
            "special_chance": 0.7, "max_specials": 3,
            "grow_every": 0, "grow_ticks": 14, "rocks_per_apple": 0,
            "max_rocks": 16, "portals": False,
            "combo": True, "twin": True, "quests": True, "max_quests": 2},
}
DIFF_ORDER = ["Dễ", "Vừa", "Khó"]

THEMES = {
    "Rừng": {
        "bg": "#1a1d21", "bg2": "#10261c", "panel": "#101214", "board_a": "#23282d", "board_b": "#1f2327",
        "head": "#2e9e45", "body_a": "#4cc468", "body_b": "#2a7a45",
        "apple": "#e53935", "leaf": "#43a047", "obstacle": "#7a6f66",
        "btn": "#2e7d32", "btn_hover": "#43a047",
        "alt": "#3a3f45", "alt_hover": "#555c63",
        "text": "#ffffff", "alt_text": "#ffffff", "muted": "#9aa0a6",
        "accent": "#ffd54f", "row_hl": "#2d3a2f",
    },
    "Sáng": {
        "bg": "#f4f1e8", "bg2": "#dfe9cf", "panel": "#fffdf6", "board_a": "#e8e3d3", "board_b": "#dcd6c2",
        "head": "#2e7d32", "body_a": "#66bb6a", "body_b": "#9ccc65",
        "apple": "#d32f2f", "leaf": "#388e3c", "obstacle": "#8d6e63",
        "btn": "#2e7d32", "btn_hover": "#43a047",
        "alt": "#c9c3b0", "alt_hover": "#b3ad99",
        "text": "#222222", "alt_text": "#222222", "muted": "#666666",
        "accent": "#c98a00", "row_hl": "#d9e6c8",
    },
    "Đại dương": {
        "bg": "#0d1b2a", "bg2": "#06303f", "panel": "#081420", "board_a": "#13293d", "board_b": "#10233a",
        "head": "#00b4d8", "body_a": "#48cae4", "body_b": "#0077b6",
        "apple": "#ff6b6b", "leaf": "#52b788", "obstacle": "#7b8794",
        "btn": "#0077b6", "btn_hover": "#0096c7",
        "alt": "#26415c", "alt_hover": "#34567a",
        "text": "#e8f1f8", "alt_text": "#e8f1f8", "muted": "#8aa0b3",
        "accent": "#ffd166", "row_hl": "#17405c",
    },
}
THEME_ORDER = ["Rừng", "Sáng", "Đại dương"]

# táo đặc biệt: (màu thân, màu viền/nhấn, màu chữ nổi khi ăn)
SPECIAL_COLORS = {
    "gold": ("#ffc107", "#b28704", "#ffd54f"),
    "blue": ("#29b6f6", "#0277bd", "#4fc3f7"),
    "purple": ("#ab47bc", "#6a1b9a", "#ce93d8"),
    "poison": ("#1c3a34", "#4db6a0", "#ff8a80"),
    "bomb": ("#2b2b2b", "#ff9800", "#ffb74d"),
    "hammer": ("#78909c", "#37474f", "#b0bec5"),
    "orange": ("#ff9100", "#e65100", "#ffb74d"),
    "quest": ("#ffd54f", "#f9a825", "#ffeb3b"),
    "ice": ("#b3e5fc", "#4fc3f7", "#80deea"),
    "arrow": ("#ffab40", "#e65100", "#ffab40"),
    "mud": ("#6d4c41", "#3e2723", "#bcaaa4"),
    "portal": ("#7c4dff", "#b388ff", "#b388ff"),
    "rock": ("#8d6e63", "#4e342e", "#bcaaa4"),
}
SPECIAL_NAMES = {"gold": "Táo vàng", "blue": "Táo xanh", "purple": "Táo tím",
                 "poison": "Táo độc", "bomb": "Táo bom"}

MEDAL_COLORS = {1: "#ffd54f", 2: "#cfd8dc", 3: "#d08c5b"}
DIFF_COLORS = {"Dễ": "#4caf50", "Vừa": "#ffb300", "Khó": "#ef5350"}

# kích thước màn bảng xếp hạng
TAB_W, TAB_H = 540, 44
TABLE_W = 548
HEADER_H, ROW_H = 36, 34
TABLE_H = HEADER_H + 8 + TOP_N * ROW_H + 10

HELP_PAGES = ["Điều khiển", "Luật chơi", "Độ khó", "Táo đặc biệt", "Cơ chế"]
# số vạch "tốc độ" hiển thị ở trang Độ khó (chỉ để minh họa)
SPEED_LEVEL = {"Dễ": 2, "Vừa": 3, "Khó": 5}

# kích thước khung chat với trợ lý
CHAT_W, CHAT_H = 548, 235


# ----------------------------------------------------------------------
# Hàm phụ
# ----------------------------------------------------------------------
def cell_to_pixel(x: int, y: int) -> tuple[int, int]:
    """Ô (x,y) -> pixel góc trên trái. Ví dụ (3,1), CELL_SIZE=30 -> (90,30)."""
    return x * CELL_SIZE, y * CELL_SIZE


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def lerp_color(c1: str, c2: str, t: float) -> str:
    """Pha màu c1 -> c2 theo t in [0,1]."""
    t = max(0.0, min(1.0, t))
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def mix_at(t: dict, frac: float) -> str:
    """Màu nền gradient của theme tại vị trí dọc frac in [0,1]."""
    return lerp_color(t["bg"], t["bg2"], frac)


def vgradient(canvas, w, h, c1, c2, steps=60, tags="bgfx"):
    """Nền chuyển màu dọc bằng các dải ngang."""
    for i in range(steps):
        y1, y2 = h * i / steps, h * (i + 1) / steps
        canvas.create_rectangle(0, y1, w, y2 + 1, fill=lerp_color(c1, c2, i / (steps - 1)),
                                outline="", tags=tags)


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Vẽ hình chữ nhật bo góc bằng polygon smooth."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


def draw_apple_icon(c, kind: str, cx: float, cy: float, r: float, theme: dict,
                    tags="") -> None:
    """Vẽ một quả táo (red / gold / blue / purple / poison / bomb) tại (cx, cy)."""
    if kind == "bomb":
        c.create_oval(cx - r, cy - r + 2, cx + r, cy + r + 2, fill="#2b2b2b",
                      outline="#111111", width=1, tags=tags)
        c.create_oval(cx - r + 3, cy - r + 5, cx - r + 8, cy - r + 9, fill="#6d6d6d",
                      outline="", tags=tags)
        c.create_line(cx + 2, cy - r + 2, cx + 6, cy - r - 3, cx + 9, cy - r - 4,
                      fill="#8d6e63", width=2, smooth=True, tags=tags)
        c.create_oval(cx + 7, cy - r - 8, cx + 13, cy - r - 2, fill="#ff9800",
                      outline="", tags=tags)
        c.create_oval(cx + 9, cy - r - 6, cx + 11, cy - r - 4, fill="#fff59d",
                      outline="", tags=tags)
        return
    if kind == "red":
        body, edge = theme["apple"], lerp_color(theme["apple"], "#000000", 0.3)
    else:
        body, edge, _ = SPECIAL_COLORS[kind]
    c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=body, outline=edge, width=1, tags=tags)
    c.create_oval(cx - r + 3, cy - r + 3, cx - r + 8, cy - r + 7,
                  fill=lerp_color(body, "#ffffff", 0.55), outline="", tags=tags)
    c.create_line(cx, cy - r + 1, cx + 2, cy - r - 5, fill="#6d4c41", width=2, tags=tags)
    leaf = "#2e7d6b" if kind == "poison" else theme["leaf"]
    c.create_oval(cx + 2, cy - r - 8, cx + 11, cy - r - 2, fill=leaf, outline="", tags=tags)
    if kind == "gold":      # lấp lánh
        for dx, dy, s in ((r - 3, -r + 4, 4), (-r + 5, r - 6, 3)):
            x, y = cx + dx, cy + dy
            c.create_line(x - s, y, x + s, y, fill="#fffde7", width=1, tags=tags)
            c.create_line(x, y - s, x, y + s, fill="#fffde7", width=1, tags=tags)
    elif kind == "blue":    # tinh thể băng
        for ang in (0, 60, 120):
            a = math.radians(ang)
            c.create_line(cx - 5 * math.cos(a), cy + 2 - 5 * math.sin(a),
                          cx + 5 * math.cos(a), cy + 2 + 5 * math.sin(a),
                          fill="#e1f5fe", width=1, tags=tags)
    elif kind == "purple":  # sao nhỏ x2
        c.create_text(cx, cy + 2, text="x2", fill="#f3e5f5",
                      font=(FONT, max(6, int(r * 0.7)), "bold"), tags=tags)
    elif kind == "orange":  # hai mũi tên >> chỉ tốc độ
        for dx in (-4, 1):
            c.create_line(cx + dx - 2, cy - 3, cx + dx + 2, cy + 1, cx + dx - 2, cy + 5,
                          fill="#fff8e1", width=2, tags=tags)
    elif kind == "hammer":  # vết nứt như đá vỡ
        c.create_line(cx - 5, cy - 3, cx - 1, cy + 1, cx - 3, cy + 3, cx + 2, cy + 6,
                      cx + 5, cy + 2, fill="#eceff1", width=2, tags=tags)
    elif kind == "poison":  # mặt đầu lâu nhỏ
        for sx in (-4, 4):
            c.create_oval(cx + sx - 2, cy - 2, cx + sx + 2, cy + 2, fill="#b2dfdb",
                          outline="", tags=tags)
        c.create_line(cx - 4, cy + 6, cx + 4, cy + 6, fill="#b2dfdb", width=1, tags=tags)


class RoundButton(tk.Canvas):
    """Nút bo góc có đổ bóng, icon tùy chọn, hiệu ứng rê chuột / nhấn."""

    SHADOW = 4

    def __init__(self, parent, text, command, colors, width=260, height=44,
                 font=None, alt=False, icon=None, bg=None, dot=None, chevron=False):
        bg = bg or colors["bg"]
        super().__init__(
            parent, width=width, height=height + self.SHADOW, bg=bg,
            highlightthickness=0, cursor="hand2",
        )
        font = font or (FONT, 13, "bold")
        self._cmd = command
        self._bw, self._bh = width, height
        self._normal = colors["alt"] if alt else colors["btn"]
        self._hover = colors["alt_hover"] if alt else colors["btn_hover"]
        self._fg = colors["alt_text"] if alt else "#ffffff"
        self._pressed = False

        # bóng đổ + thân nút + vệt sáng phía trên
        round_rect(self, 2, 2 + self.SHADOW, width - 2, height - 2 + self.SHADOW, 14,
                   fill=lerp_color(bg, "#000000", 0.38), outline="")
        self._shape = round_rect(self, 2, 2, width - 2, height - 2, 14,
                                 fill=self._normal, outline="", tags="face")
        self._hl = self.create_line(16, 4, width - 16, 4, tags="face",
                                    fill=lerp_color(self._normal, "#ffffff", 0.22), width=2)

        cy = height / 2
        if icon:
            self._draw_icon(icon, 34, cy, self._fg, tags="face")
            self._label = self.create_text(62, cy, text=text, fill=self._fg, font=font,
                                           anchor="w", tags="face")
        else:
            self._label = self.create_text(width / 2, cy, text=text, fill=self._fg,
                                           font=font, tags="face")
        self._dot = None
        if dot:
            self._dot = self.create_oval(18, cy - 5, 28, cy + 5, fill=dot, outline="",
                                         tags="face")
            self.coords(self._label, 38, cy)
            self.itemconfig(self._label, anchor="w")
        if chevron:
            self.create_line(width - 30, cy - 6, width - 22, cy, width - 30, cy + 6,
                             fill=lerp_color(self._fg, self._normal, 0.35), width=2,
                             capstyle="round", joinstyle="round", tags="face")

        self.bind("<Enter>", lambda e: self._paint(self._hover))
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _paint(self, color):
        self.itemconfig(self._shape, fill=color)
        self.itemconfig(self._hl, fill=lerp_color(color, "#ffffff", 0.22))

    def _draw_icon(self, kind, cx, cy, col, tags):
        c = self
        if kind == "play":
            c.create_polygon(cx - 7, cy - 10, cx - 7, cy + 10, cx + 11, cy,
                             fill=col, outline=col, width=2, joinstyle="round", tags=tags)
        elif kind == "trophy":
            c.create_polygon(cx - 9, cy - 10, cx + 9, cy - 10, cx + 7, cy + 2,
                             cx - 7, cy + 2, fill=col, outline="", tags=tags)
            c.create_arc(cx - 15, cy - 9, cx - 5, cy + 1, start=90, extent=180,
                         style="arc", outline=col, width=2, tags=tags)
            c.create_arc(cx + 5, cy - 9, cx + 15, cy + 1, start=-90, extent=180,
                         style="arc", outline=col, width=2, tags=tags)
            c.create_rectangle(cx - 2, cy + 2, cx + 2, cy + 7, fill=col, outline="", tags=tags)
            c.create_rectangle(cx - 7, cy + 7, cx + 7, cy + 10, fill=col, outline="", tags=tags)
        elif kind == "book":
            c.create_rectangle(cx - 11, cy - 10, cx - 1, cy + 9, fill=col, outline="", tags=tags)
            c.create_rectangle(cx + 1, cy - 10, cx + 11, cy + 9, fill=col, outline="", tags=tags)
        elif kind == "power":
            c.create_arc(cx - 9, cy - 8, cx + 9, cy + 10, start=120, extent=300,
                         style="arc", outline=col, width=3, tags=tags)
            c.create_line(cx, cy - 11, cx, cy, fill=col, width=3, capstyle="round", tags=tags)

    def set_text(self, text: str) -> None:
        self.itemconfig(self._label, text=text)

    def set_dot(self, color: str) -> None:
        if self._dot is not None:
            self.itemconfig(self._dot, fill=color)

    def _on_press(self, event) -> None:
        if not self._pressed:
            self._pressed = True
            self.move("face", 0, 2)

    def _on_leave(self, event) -> None:
        self._paint(self._normal)
        if self._pressed:
            self._pressed = False
            self.move("face", 0, -2)

    def _on_release(self, event) -> None:
        was = self._pressed
        if was:
            self._pressed = False
            self.move("face", 0, -2)
        if was and 0 <= event.x <= self._bw and 0 <= event.y <= self._bh:
            self._cmd()


# ----------------------------------------------------------------------
# Ứng dụng
# ----------------------------------------------------------------------
class SnakeApp:
    def __init__(self, engine: GameEngine):
        """Tạo cửa sổ Tkinter với các màn hình: menu, nhập tên, game,
        bảng xếp hạng, hướng dẫn. UI chỉ gọi engine, không sửa dữ liệu engine.
        """
        self._base_engine = engine
        self._engines: dict[str, SpecialEngine] = {}  # mỗi độ khó một engine
        self.engine = engine

        self._after_id = None   # id của lần after đang chờ (chỉ một chuỗi)
        self._closed = False
        self._screen = "menu"
        self._phase = "idle"    # idle | countdown | playing | paused | ended
        self._count = 0
        self._player = ""
        self._difficulty = "Vừa"
        self._theme_name = "Rừng"
        self._saved = False
        self._result_lines: list[str] = []
        self._effects: list[dict] = []   # chữ "+10" bay lên
        self._best = 0
        self._frame = 0                  # nhịp nhấp nháy của táo
        self._board_mode = "Vừa"         # tab đang xem ở bảng xếp hạng
        self._tab_hover = -1
        self._help_page = 0              # trang đang xem ở màn hướng dẫn
        self._help_hover = -1
        self._chat_history: list[tuple[str, str]] = []  # (who, text)
        self._chat_drawn = False
        self._chat_y = 10

        self.width = engine.cols * CELL_SIZE
        self.height = engine.rows * CELL_SIZE

        self.root = tk.Tk()
        global FONT
        try:
            from tkinter import font as tkfont
            if "Segoe UI" in tkfont.families(self.root):
                FONT = "Segoe UI"
        except tk.TclError:
            pass
        self._menu_after = None
        self._anim_t = 0
        self.root.title("Snake Eats Apples")
        self.root.resizable(True, True)
        self.root.minsize(MIN_W, MIN_H)
        self._resize_job = None
        self._apply_geometry()

        self._container = None
        self._build_ui()

        self.root.bind("<Key>", self.on_key)
        self.root.bind("<Configure>", self._on_window_resize)
        self.root.bind("<Control-MouseWheel>",
                       lambda e: self._zoom(1 if e.delta > 0 else -1))
        self.root.bind("<Control-Button-4>", lambda e: self._zoom(1))   # Linux
        self.root.bind("<Control-Button-5>", lambda e: self._zoom(-1))
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._show("menu")

    @property
    def theme(self) -> dict:
        return THEMES[self._theme_name]

    # ------------------------------------------------------------------
    # Dựng giao diện (dựng lại toàn bộ khi đổi theme)
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        t = self.theme
        self._stop_menu_anim()
        self.root.configure(bg=t["bg"])
        if self._container is not None:
            self._container.destroy()

        self._container = tk.Frame(self.root, bg=t["bg"])
        self._container.pack(fill="both", expand=True)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

        self._frames: dict[str, tk.Frame] = {}
        for name in ("menu", "name", "game", "leaderboard", "help", "chat"):
            frame = tk.Frame(self._container, bg=t["bg"])
            if name == "game":
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.configure(width=BASE_W, height=BASE_H)
                frame.pack_propagate(False)
                frame.grid_propagate(False)
                frame.grid(row=0, column=0)
            self._frames[name] = frame

        self._build_menu(self._frames["menu"])
        self._build_name(self._frames["name"])
        self._build_game(self._frames["game"])
        self._build_leaderboard(self._frames["leaderboard"])
        self._build_help(self._frames["help"])
        self._build_chat(self._frames["chat"])

    def _btn(self, parent, text, command, alt=False, width=260, height=44,
             font=None, **kw) -> RoundButton:
        return RoundButton(parent, text, command, self.theme, width=width,
                           height=height, font=font, alt=alt, **kw)

    def _heading(self, parent, text, size=22) -> tk.Label:
        t = self.theme
        return tk.Label(parent, text=text, font=(FONT, size, "bold"),
                        fg=t["text"], bg=t["bg"])

    # ---- menu --------------------------------------------------------
    MENU_W, MENU_H = 624, 620

    def _build_menu(self, f: tk.Frame) -> None:
        t = self.theme
        W, H = self.MENU_W, self.MENU_H
        mc = tk.Canvas(f, width=W, height=H, bg=t["bg"], highlightthickness=0)
        mc.place(relx=0.5, rely=0, anchor="n")
        self.menu_canvas = mc
        vgradient(mc, W, H, t["bg"], t["bg2"], steps=70)

        # trang trí: lưới ô caro mờ ở đáy + vài vầng sáng
        glow = lerp_color(t["bg2"], t["head"], 0.07)
        mc.create_oval(W - 250, 420, W + 150, 800, fill=glow, outline="")
        cs = 26
        for gy in range(3):
            for gx in range(W // cs + 1):
                if (gx + gy) % 2 == 0:
                    y0 = H - (gy + 1) * cs
                    mc.create_rectangle(gx * cs, y0, gx * cs + cs, y0 + cs, outline="",
                                        fill=lerp_color(mix_at(t, (y0 + cs / 2) / H),
                                                        t["head"], 0.07 - gy * 0.02))

        # tiêu đề hai tầng
        cx = W / 2
        mc.create_text(cx + 2, 52, text="SNAKE", font=(FONT, 44, "bold"),
                       fill=lerp_color(t["bg"], "#000000", 0.28))
        mc.create_text(cx, 50, text="SNAKE", font=(FONT, 44, "bold"), fill=t["text"])
        mc.create_text(cx, 96, text="E A T S   A P P L E S", font=(FONT, 13, "bold"),
                       fill=t["accent"])
        mc.create_line(cx - 90, 118, cx + 90, 118, fill=lerp_color(t["accent"], t["bg"], 0.55),
                       width=2, capstyle="round")

        # rắn bò lượn sóng về phía quả táo (hoạt hình, xem _menu_animate)
        self._anim_head_x = -10.0
        self._anim_eat = 0
        self._menu_animate()

        # nút
        def bgat(y):  # màu nền gradient tại độ cao y để nút hòa vào nền
            return mix_at(t, y / H)

        def put(widget, y):
            mc.create_window(cx, y, window=widget, anchor="n")

        btn_w = 320
        play = self._btn(mc, "Chơi game", lambda: self._show("name"), width=btn_w,
                         height=54, icon="play", chevron=True, bg=bgat(250),
                         font=(FONT, 15, "bold"))
        put(play, 250)
        board = self._btn(mc, "Bảng xếp hạng", lambda: self._show("leaderboard"),
                          alt=True, width=btn_w, height=46, icon="trophy",
                          chevron=True, bg=bgat(322))
        put(board, 322)
        guide = self._btn(mc, "Hướng dẫn chơi", lambda: self._show("help"), alt=True,
                          width=btn_w, height=46, icon="book", chevron=True, bg=bgat(384))
        put(guide, 384)

        self.diff_btn = self._btn(
            mc, f"Độ khó: {self._difficulty}", self._cycle_difficulty, alt=True,
            width=156, height=38, font=(FONT, 10, "bold"), bg=bgat(458),
            dot=DIFF_COLORS[self._difficulty])
        mc.create_window(cx - 82, 458, window=self.diff_btn, anchor="n")
        self.theme_btn = self._btn(
            mc, f"Giao diện: {self._theme_name}", self._cycle_theme, alt=True,
            width=156, height=38, font=(FONT, 10, "bold"), bg=bgat(458),
            dot=t["head"])
        mc.create_window(cx + 82, 458, window=self.theme_btn, anchor="n")

        quit_btn = self._btn(mc, "Thoát", self._close, alt=True, width=140, height=36,
                             icon=None, font=(FONT, 10, "bold"), bg=bgat(514))
        put(quit_btn, 514)

        mc.create_text(cx, H - 22, text="Mũi tên / WASD để điều khiển  •  Esc để thoát",
                       font=(FONT, 9), fill=t["muted"])

    # ---- hoạt hình rắn ở menu ---------------------------------------
    def _menu_animate(self) -> None:
        """Vẽ một khung hình rắn bò sóng sin tới quả táo rồi lặp lại."""
        self._menu_after = None
        if self._closed or self._screen != "menu":
            return
        mc, t = self.menu_canvas, self.theme
        try:
            mc.delete("anim")
        except tk.TclError:
            return
        self._anim_t += 1
        apple_x, base_y = 520, 178
        n, gap = 18, 13

        if self._anim_eat > 0:
            self._anim_eat -= 1
            if self._anim_eat == 0:
                self._anim_head_x = -10.0
        else:
            self._anim_head_x += 3.2
            if self._anim_head_x >= apple_x - 26:
                self._anim_eat = 22

        def wave(x):
            return base_y + 14 * math.sin(x / 38.0 - self._anim_t * 0.16)

        # táo (biến mất khi bị ăn, bập bềnh nhẹ)
        if self._anim_eat == 0 or self._anim_eat > 14:
            bob = 2 * math.sin(self._anim_t * 0.2)
            ay = base_y + bob
            mc.create_oval(apple_x - 15, ay - 13, apple_x + 15, ay + 17,
                           fill=t["apple"], outline="", tags="anim")
            mc.create_oval(apple_x - 9, ay - 8, apple_x - 3, ay - 2,
                           fill=lerp_color(t["apple"], "#ffffff", 0.55), outline="", tags="anim")
            mc.create_line(apple_x, ay - 12, apple_x + 3, ay - 21, fill="#6d4c41",
                           width=3, tags="anim")
            mc.create_oval(apple_x + 3, ay - 24, apple_x + 15, ay - 14,
                           fill=t["leaf"], outline="", tags="anim")

        hx = self._anim_head_x
        pts = [(hx - i * gap, wave(hx - i * gap)) for i in range(n)]
        for i in range(n - 1, 0, -1):  # đuôi -> thân
            x, y = pts[i]
            if x < -14:
                continue
            r = 5 + 8 * (1 - i / n) ** 0.6
            col = lerp_color(t["body_a"], t["body_b"], i / n)
            mc.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="", tags="anim")
        x, y = pts[0]
        y2 = wave(hx - 4)
        ang = math.atan2(y - y2, 4)
        mc.create_oval(x - 15, y - 14, x + 15, y + 14, fill=t["head"], outline="", tags="anim")
        for s in (-1, 1):
            ex = x + 5 * math.cos(ang) - 6 * s * math.sin(ang)
            ey = y + 5 * math.sin(ang) + 6 * s * math.cos(ang)
            mc.create_oval(ex - 4.5, ey - 4.5, ex + 4.5, ey + 4.5, fill="white", outline="", tags="anim")
            mc.create_oval(ex - 1.5, ey - 2, ex + 3, ey + 2.5, fill="#111111", outline="", tags="anim")
        if (self._anim_t // 6) % 3 != 2 and self._anim_eat == 0:  # lưỡi thè ra, thụt vào
            tx, ty = x + 15 * math.cos(ang), y + 15 * math.sin(ang)
            mc.create_line(tx, ty, tx + 12 * math.cos(ang), ty + 12 * math.sin(ang),
                           fill="#e53935", width=2, tags="anim")

        self._menu_after = self.root.after(45, self._menu_animate)

    def _stop_menu_anim(self) -> None:
        if self._menu_after is not None:
            try:
                self.root.after_cancel(self._menu_after)
            except (tk.TclError, AttributeError):
                pass
            self._menu_after = None

    def _cycle_difficulty(self) -> None:
        i = DIFF_ORDER.index(self._difficulty)
        self._difficulty = DIFF_ORDER[(i + 1) % len(DIFF_ORDER)]
        self.diff_btn.set_text(f"Độ khó: {self._difficulty}")
        self.diff_btn.set_dot(DIFF_COLORS[self._difficulty])

    def _cycle_theme(self) -> None:
        i = THEME_ORDER.index(self._theme_name)
        self._theme_name = THEME_ORDER[(i + 1) % len(THEME_ORDER)]
        # dựng lại sau khi xử lý xong sự kiện (nút đang bị hủy chính là nút vừa bấm)
        self.root.after_idle(self._rebuild_after_theme)

    def _rebuild_after_theme(self) -> None:
        if self._closed:
            return
        self._build_ui()
        self._show("menu")

    # ---- nhập tên ----------------------------------------------------
    def _build_name(self, f: tk.Frame) -> None:
        t = self.theme
        self._heading(f, "Sẵn sàng chưa?", 26).pack(pady=(70, 2))
        self.name_info = tk.Label(f, text="", font=(FONT, 11),
                                  fg=t["muted"], bg=t["bg"])
        self.name_info.pack(pady=(0, 18))

        border = lerp_color(t["muted"], t["bg"], 0.55)
        card = tk.Frame(f, bg=t["panel"], highlightthickness=2, highlightbackground=border)
        card.pack(ipadx=34, ipady=10)
        tk.Label(card, text="TÊN NGƯỜI CHƠI", font=(FONT, 9, "bold"), fg=t["muted"],
                 bg=t["panel"]).pack(pady=(16, 6))

        self.name_var = tk.StringVar(value=self._player)
        vcmd = (self.root.register(lambda v: len(v) <= MAX_NAME_LEN), "%P")
        self.name_entry = tk.Entry(
            card, textvariable=self.name_var, font=(FONT, 18, "bold"), width=18,
            justify="center", validate="key", validatecommand=vcmd,
            relief="flat", bg=lerp_color(t["panel"], t["bg"], 0.45), fg=t["text"],
            insertbackground=t["text"], highlightthickness=2,
            highlightbackground=border, highlightcolor=t["accent"],
        )
        self.name_entry.pack(pady=4, ipady=6)
        self.name_entry.bind("<Return>", lambda e: self._start_game())

        self.name_error = tk.Label(card, text="", font=(FONT, 10),
                                   fg="#ff8a80", bg=t["panel"])
        self.name_error.pack(pady=(4, 6))
        tk.Label(card, text=f"Tối đa {MAX_NAME_LEN} ký tự  •  Enter để bắt đầu",
                 font=(FONT, 9), fg=t["muted"], bg=t["panel"]).pack(pady=(0, 10))

        self._btn(f, "Bắt đầu", self._start_game, icon="play",
                  font=(FONT, 14, "bold"), height=50).pack(pady=(22, 6))
        self._btn(f, "Quay lại", lambda: self._show("menu"), alt=True,
                  height=40).pack(pady=4)

    # ---- màn game ----------------------------------------------------
    def _build_game(self, f: tk.Frame) -> None:
        t = self.theme
        edge = lerp_color(t["muted"], t["bg"], 0.5)
        bar = tk.Frame(f, bg=t["panel"], highlightthickness=1, highlightbackground=edge)
        bar.pack(padx=12, pady=(10, 8), ipady=4, fill="x")

        self.player_label = tk.Label(bar, text="", font=(FONT, 12, "bold"),
                                     fg=t["muted"], bg=t["panel"])
        self.player_label.pack(side="left", padx=14)
        self.fx_slow = tk.Label(bar, text="", font=(FONT, 11, "bold"),
                                fg=SPECIAL_COLORS["blue"][2], bg=t["panel"])
        self.fx_slow.pack(side="left", padx=(0, 8))
        self.fx_fast = tk.Label(bar, text="", font=(FONT, 11, "bold"),
                                fg=SPECIAL_COLORS["orange"][2], bg=t["panel"])
        self.fx_fast.pack(side="left", padx=(0, 8))
        self.fx_x2 = tk.Label(bar, text="", font=(FONT, 11, "bold"),
                              fg=SPECIAL_COLORS["purple"][2], bg=t["panel"])
        self.fx_x2.pack(side="left", padx=(0, 8))
        self.fx_bomb = tk.Label(bar, text="", font=(FONT, 11, "bold"),
                                fg=SPECIAL_COLORS["bomb"][2], bg=t["panel"])
        self.fx_bomb.pack(side="left")
        self.score_label = tk.Label(bar, text="Score: 0", font=(FONT, 16, "bold"),
                                    fg=t["text"], bg=t["panel"])
        self.score_label.pack(side="right", padx=14)
        self.best_label = tk.Label(bar, text="Best: 0", font=(FONT, 11, "bold"),
                                   fg=t["accent"], bg=t["panel"])
        self.best_label.pack(side="right", padx=10)
        self.pause_btn = self._btn(bar, "Tạm dừng", self._toggle_pause, alt=True,
                                   width=110, height=30, font=(FONT, 10, "bold"),
                                   bg=t["panel"])
        self.pause_btn.pack(side="right", padx=(0, 6))

        bar2 = tk.Frame(f, bg=t["bg"], height=22)   # combo (trái) + nhiệm vụ (phải)
        bar2.pack(fill="x", padx=14, pady=(0, 4))
        bar2.pack_propagate(False)
        self.fx_combo = tk.Label(bar2, text="", font=(FONT, 10, "bold"),
                                 fg=SPECIAL_COLORS["gold"][2], bg=t["bg"])
        self.fx_combo.pack(side="left")
        self.fx_quest = tk.Label(bar2, text="", font=(FONT, 10, "bold"),
                                 fg=SPECIAL_COLORS["quest"][2], bg=t["bg"])
        self.fx_quest.pack(side="right")

        frame = tk.Frame(f, bg=edge)  # viền quanh bàn chơi
        frame.pack()
        self.canvas = tk.Canvas(frame, width=self.width, height=self.height,
                                bg=t["board_a"], highlightthickness=0)
        self.canvas.pack(padx=3, pady=3)
        self._draw_board()

        # thanh dưới: gợi ý phím / nút khi kết thúc / nút khi tạm dừng
        self.bottom = tk.Frame(f, bg=t["bg"], height=56)
        self.bottom.pack(fill="x", pady=4)
        self.bottom.pack_propagate(False)

        self.hint_label = tk.Label(
            self.bottom, text="Mũi tên/WASD: di chuyển   E: tạm dừng   R: chơi lại   +/-: phóng to/nhỏ   Esc: menu",
            font=(FONT, 9), fg=t["muted"], bg=t["bg"])

        self.end_row = tk.Frame(self.bottom, bg=t["bg"])
        self._btn(self.end_row, "Chơi lại", self._begin_round, width=150,
                  height=40).pack(side="left", padx=8)
        self._btn(self.end_row, "Về menu", lambda: self._show("menu"), alt=True,
                  width=150, height=40).pack(side="left", padx=8)

        self.pause_row = tk.Frame(self.bottom, bg=t["bg"])
        self._btn(self.pause_row, "Tiếp tục (E)", self._toggle_pause, width=150,
                  height=40).pack(side="left", padx=8)
        self._btn(self.pause_row, "Thoát (Q)", self._quit_from_pause, alt=True,
                  width=150, height=40).pack(side="left", padx=8)

        self._set_bottom("hint")

    def _set_bottom(self, mode: str) -> None:
        for w in (self.hint_label, self.end_row, self.pause_row):
            w.pack_forget()
        {"hint": self.hint_label, "ended": self.end_row,
         "paused": self.pause_row}[mode].pack(expand=True)

    def _draw_board(self) -> None:
        """Nền caro vẽ một lần (tag 'bg'); phần động dùng tag 'dyn'."""
        t = self.theme
        for y in range(self.engine.rows):
            for x in range(self.engine.cols):
                px, py = cell_to_pixel(x, y)
                color = t["board_a"] if (x + y) % 2 == 0 else t["board_b"]
                self.canvas.create_rectangle(
                    px, py, px + CELL_SIZE, py + CELL_SIZE,
                    fill=color, outline="", tags="bg")

    # ---- bảng xếp hạng / hướng dẫn -----------------------------------
    def _build_leaderboard(self, f: tk.Frame) -> None:
        t = self.theme
        # nút quay lại đặt trước để luôn còn chỗ ở đáy
        self._btn(f, "Quay lại", lambda: self._show("menu"), alt=True,
                  height=40).pack(side="bottom", pady=14)
        self._heading(f, "BẢNG XẾP HẠNG").pack(pady=(18, 10))

        self.tab_canvas = tk.Canvas(f, width=TAB_W, height=TAB_H, bg=t["bg"],
                                    highlightthickness=0, cursor="hand2")
        self.tab_canvas.pack()
        self.tab_canvas.bind("<Button-1>", self._on_tab_click)
        self.tab_canvas.bind("<Motion>", self._on_tab_motion)
        self.tab_canvas.bind("<Leave>", self._on_tab_leave)

        self.table_canvas = tk.Canvas(f, width=TABLE_W, height=TABLE_H, bg=t["bg"],
                                      highlightthickness=0)
        self.table_canvas.pack(pady=(10, 0))

    def _tab_index(self, x: float, n: int | None = None) -> int:
        n = n or len(DIFF_ORDER)
        return max(0, min(n - 1, int(x // (TAB_W / n))))

    def _on_tab_click(self, event) -> None:
        self._set_board_mode(DIFF_ORDER[self._tab_index(event.x)])

    def _on_tab_motion(self, event) -> None:
        i = self._tab_index(event.x)
        if i != self._tab_hover:
            self._tab_hover = i
            self._draw_tabs()

    def _on_tab_leave(self, event) -> None:
        self._tab_hover = -1
        self._draw_tabs()

    def _set_board_mode(self, mode: str) -> None:
        self._board_mode = mode
        self._refresh_leaderboard()

    def _shift_board_mode(self, step: int) -> None:
        i = DIFF_ORDER.index(self._board_mode)
        self._set_board_mode(DIFF_ORDER[(i + step) % len(DIFF_ORDER)])

    def _refresh_leaderboard(self) -> None:
        self._draw_tabs()
        self._draw_table()

    def _draw_tabs(self) -> None:
        """Thanh chọn độ khó: Dễ | Vừa | Khó, tab đang chọn tô màu của mức đó."""
        c, t = self.tab_canvas, self.theme
        c.delete("all")
        seg = TAB_W / len(DIFF_ORDER)
        round_rect(c, 1, 1, TAB_W - 1, TAB_H - 1, 22, fill=t["panel"],
                   outline=lerp_color(t["muted"], t["bg"], 0.55), width=1)
        for i, mode in enumerate(DIFF_ORDER):
            x1, x2 = i * seg + 5, (i + 1) * seg - 5
            cx = (x1 + x2) / 2
            if mode == self._board_mode:
                round_rect(c, x1, 5, x2, TAB_H - 5, 17, fill=DIFF_COLORS[mode], outline="")
                c.create_text(cx, TAB_H / 2, text=mode, fill="#1a1a1a",
                              font=(FONT, 13, "bold"))
            else:
                hover = i == self._tab_hover
                if hover:
                    round_rect(c, x1, 5, x2, TAB_H - 5, 17, fill=t["alt"], outline="")
                c.create_oval(cx - 30, TAB_H / 2 - 4, cx - 22, TAB_H / 2 + 4,
                              fill=DIFF_COLORS[mode], outline="")
                c.create_text(cx + 4, TAB_H / 2, text=mode,
                              fill=t["text"] if hover else t["muted"],
                              font=(FONT, 13, "bold"))

    def _draw_table(self) -> None:
        """Bảng top 10 của độ khó đang chọn, vẽ dạng thẻ bo góc."""
        c, t = self.table_canvas, self.theme
        c.delete("all")
        W = TABLE_W
        dim = lerp_color(t["muted"], t["panel"], 0.55)
        round_rect(c, 1, 1, W - 1, TABLE_H - 1, 18, fill=t["panel"],
                   outline=lerp_color(t["muted"], t["bg"], 0.5), width=2)

        col_rank, col_name, col_score, col_date = 48, 96, W - 200, W - 78
        head_font = (FONT, 9, "bold")
        hy = HEADER_H / 2 + 4
        c.create_text(col_rank, hy, text="HẠNG", fill=t["muted"], font=head_font)
        c.create_text(col_name, hy, text="TÊN", fill=t["muted"], font=head_font, anchor="w")
        c.create_text(col_score, hy, text="ĐIỂM", fill=t["muted"], font=head_font)
        c.create_text(col_date, hy, text="NGÀY", fill=t["muted"], font=head_font)
        c.create_line(16, HEADER_H + 3, W - 16, HEADER_H + 3,
                      fill=lerp_color(t["muted"], t["panel"], 0.6))

        rows = leaderboard.top_scores(TOP_N, mode=self._board_mode)
        me = self._player.casefold()

        for i in range(1, TOP_N + 1):
            y0 = HEADER_H + 8 + (i - 1) * ROW_H
            y1 = y0 + ROW_H - 4
            cy = (y0 + y1) / 2
            entry = rows[i - 1] if i <= len(rows) else None
            is_me = entry is not None and bool(me) and entry["name"].casefold() == me

            if is_me:
                round_rect(c, 10, y0, W - 10, y1, 12, fill=t["row_hl"],
                           outline=t["accent"], width=1)
            elif i % 2 == 1:
                round_rect(c, 10, y0, W - 10, y1, 12,
                           fill=lerp_color(t["panel"], t["bg"], 0.35), outline="")

            # huy chương / số hạng
            if i in MEDAL_COLORS and entry is not None:
                c.create_oval(col_rank - 13, cy - 13, col_rank + 13, cy + 13,
                              fill=MEDAL_COLORS[i], outline="")
                c.create_text(col_rank, cy, text=str(i), fill="#222222",
                              font=(FONT, 12, "bold"))
            else:
                c.create_text(col_rank, cy, text=f"#{i}",
                              fill=t["muted"] if entry else dim,
                              font=(FONT, 11, "bold"))

            if entry is None:
                c.create_text(col_name, cy, text="—", fill=dim,
                              font=(FONT, 12), anchor="w")
                continue

            name_color = t["accent"] if (i <= 3 or is_me) else t["text"]
            c.create_text(col_name, cy, text=entry["name"], fill=name_color,
                          font=(FONT, 13, "bold"), anchor="w")
            c.create_text(col_score, cy, text=str(entry["score"]), fill=name_color,
                          font=(FONT, 13, "bold"))
            d = entry["date"][:10].split("-")
            date_text = f"{d[2]}/{d[1]}/{d[0]}" if len(d) == 3 else "-"
            c.create_text(col_date, cy, text=date_text, fill=t["muted"],
                          font=(FONT, 10))

        if not rows:
            cx, cy = W / 2, HEADER_H + 8 + 4 * ROW_H
            round_rect(c, cx - 190, cy - 22, cx + 190, cy + 22, 20,
                       fill=t["panel"], outline=DIFF_COLORS[self._board_mode], width=2)
            c.create_text(cx, cy, text=f"Chưa có ai chơi mức {self._board_mode}!",
                          fill=t["text"], font=(FONT, 12, "bold"))

    def _build_help(self, f: tk.Frame) -> None:
        t = self.theme
        row = tk.Frame(f, bg=t["bg"])
        row.pack(side="bottom", pady=14)
        self._btn(row, "Hỏi trợ lý", lambda: self._show("chat"), width=220,
                  height=40).pack(side="left", padx=8)
        self._btn(row, "Quay lại", lambda: self._show("menu"), alt=True, width=180,
                  height=40).pack(side="left", padx=8)
        self._heading(f, "HƯỚNG DẪN CHƠI").pack(pady=(18, 10))

        self.help_tabs = tk.Canvas(f, width=TAB_W, height=TAB_H, bg=t["bg"],
                                   highlightthickness=0, cursor="hand2")
        self.help_tabs.pack()
        self.help_tabs.bind("<Button-1>", self._on_help_click)
        self.help_tabs.bind("<Motion>", self._on_help_motion)
        self.help_tabs.bind("<Leave>", self._on_help_leave)

        self.help_canvas = tk.Canvas(f, width=TABLE_W, height=TABLE_H, bg=t["bg"],
                                     highlightthickness=0)
        self.help_canvas.pack(pady=(10, 0))

    def _on_help_click(self, event) -> None:
        self._set_help_page(self._tab_index(event.x, len(HELP_PAGES)))

    def _on_help_motion(self, event) -> None:
        i = self._tab_index(event.x, len(HELP_PAGES))
        if i != self._help_hover:
            self._help_hover = i
            self._draw_help_tabs()

    def _on_help_leave(self, event) -> None:
        self._help_hover = -1
        self._draw_help_tabs()

    def _set_help_page(self, page: int) -> None:
        self._help_page = page
        self._refresh_help()

    def _shift_help_page(self, step: int) -> None:
        self._set_help_page((self._help_page + step) % len(HELP_PAGES))

    def _refresh_help(self) -> None:
        self._draw_help_tabs()
        self._draw_help_page()

    def _draw_help_tabs(self) -> None:
        c, t = self.help_tabs, self.theme
        c.delete("all")
        seg = TAB_W / len(HELP_PAGES)
        round_rect(c, 1, 1, TAB_W - 1, TAB_H - 1, 22, fill=t["panel"],
                   outline=lerp_color(t["muted"], t["bg"], 0.55), width=1)
        for i, label in enumerate(HELP_PAGES):
            x1, x2 = i * seg + 5, (i + 1) * seg - 5
            cx = (x1 + x2) / 2
            if i == self._help_page:
                round_rect(c, x1, 5, x2, TAB_H - 5, 17, fill=t["btn"], outline="")
                c.create_text(cx, TAB_H / 2, text=label, fill="#ffffff",
                              font=(FONT, 12, "bold"))
            else:
                hover = i == self._help_hover
                if hover:
                    round_rect(c, x1, 5, x2, TAB_H - 5, 17, fill=t["alt"], outline="")
                c.create_text(cx, TAB_H / 2, text=label,
                              fill=t["text"] if hover else t["muted"],
                              font=(FONT, 12, "bold"))

    # ---- vẽ từng trang hướng dẫn ------------------------------------
    def _help_card(self) -> None:
        c, t = self.help_canvas, self.theme
        c.delete("all")
        round_rect(c, 1, 1, TABLE_W - 1, TABLE_H - 1, 18, fill=t["panel"],
                   outline=lerp_color(t["muted"], t["bg"], 0.5), width=2)

    def _help_footer(self, y: int, text: str) -> None:
        c, t = self.help_canvas, self.theme
        round_rect(c, 24, y, TABLE_W - 24, y + 42, 14,
                   fill=lerp_color(t["panel"], t["bg"], 0.4), outline="")
        c.create_oval(40, y + 17, 48, y + 25, fill=t["accent"], outline="")
        c.create_text(58, y + 21, text=text, fill=t["text"], font=(FONT, 10),
                      anchor="w", width=TABLE_W - 100)

    def _help_line(self, y: int) -> None:
        t = self.theme
        self.help_canvas.create_line(
            24, y, TABLE_W - 24, y, fill=lerp_color(t["muted"], t["panel"], 0.7))

    def _keycap(self, cx: float, cy: float, text: str, w: int = 40, h: int = 40,
                size: int = 13) -> None:
        """Phím bàn phím có đổ bóng bên dưới cho cảm giác nổi."""
        c, t = self.help_canvas, self.theme
        x1, y1 = cx - w / 2, cy - h / 2
        round_rect(c, x1, y1 + 3, x1 + w, y1 + h + 3, 8,
                   fill=lerp_color(t["alt"], "#000000", 0.4), outline="")
        round_rect(c, x1, y1, x1 + w, y1 + h, 8, fill=t["alt"],
                   outline=lerp_color(t["alt"], "#ffffff", 0.25))
        c.create_text(cx, cy, text=text, fill=t["alt_text"], font=(FONT, size, "bold"))

    def _draw_help_page(self) -> None:
        self._help_card()
        (self._help_controls, self._help_rules, self._help_levels,
         self._help_specials, self._help_mechanics)[self._help_page]()

    def _help_controls(self) -> None:
        c, t = self.help_canvas, self.theme
        label_font, desc_font = (FONT, 14, "bold"), (FONT, 10)

        # Di chuyển: mũi tên và WASD xếp chữ T ngược như bàn phím thật
        c.create_text(28, 54, text="Di chuyển", fill=t["text"], font=label_font, anchor="w")
        c.create_text(28, 70, text="Điều khiển hướng đi\ncủa rắn", fill=t["muted"],
                      font=desc_font, anchor="nw")
        for cx, keys in ((262, ("↑", "←", "↓", "→")), (460, ("W", "A", "S", "D"))):
            size = 16 if cx == 262 else 13  # mũi tên cần cỡ chữ lớn hơn cho dễ nhìn
            self._keycap(cx, 44, keys[0], size=size)
            for dx, k in zip((-46, 0, 46), keys[1:]):
                self._keycap(cx + dx, 90, k, size=size)
        c.create_text(361, 68, text="hoặc", fill=t["muted"], font=(FONT, 10, "italic"))
        self._help_line(132)

        rows = [
            (170, "Tạm dừng", "Dừng / tiếp tục (Q: thoát, lưu điểm)",
             [(222, "Space", 100), (300, "P", 40), (350, "E", 40)], None),
            (222, "Chơi lại", "Bắt đầu ván mới", [(216, "R", 40)], None),
            (274, "Về menu", "Rời ván đang chơi", [(224, "Esc", 56)], None),
        ]
        for i, (y, title, desc, caps, or_x) in enumerate(rows):
            c.create_text(28, y - 9, text=title, fill=t["text"], font=label_font, anchor="w")
            c.create_text(28, y + 11, text=desc, fill=t["muted"], font=desc_font, anchor="w")
            for cx, text, w in caps:
                self._keycap(cx, y, text, w=w, h=36, size=12)
            if or_x:
                c.create_text(or_x, y, text="hoặc", fill=t["muted"],
                              font=(FONT, 10, "italic"))
            if i < len(rows) - 1:
                self._help_line(y + 26)

        self._help_footer(322, "+ / - hoặc nút phóng to của cửa sổ: đổi cỡ bàn chơi")

    def _help_icon(self, kind: str, cx: float, cy: float) -> None:
        c, t = self.help_canvas, self.theme
        if kind == "apple":
            c.create_oval(cx - 13, cy - 11, cx + 13, cy + 15, fill=t["apple"], outline="")
            c.create_oval(cx - 9, cy - 7, cx - 3, cy - 2,
                          fill=lerp_color(t["apple"], "#ffffff", 0.6), outline="")
            c.create_line(cx, cy - 10, cx + 2, cy - 18, fill="#6d4c41", width=3)
            c.create_oval(cx + 2, cy - 20, cx + 12, cy - 12, fill=t["leaf"], outline="")
        elif kind == "speed":
            for dx in (-9, 5):
                c.create_line(cx + dx - 6, cy - 12, cx + dx + 6, cy, cx + dx - 6, cy + 12,
                              fill=t["accent"], width=5, capstyle="round", joinstyle="round")
        elif kind == "noreverse":
            c.create_line(cx - 13, cy, cx + 13, cy, fill=t["text"], width=3, arrow="both",
                          arrowshape=(8, 10, 4))
            c.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, outline="#ef5350", width=3)
            c.create_line(cx - 13, cy + 13, cx + 13, cy - 13, fill="#ef5350", width=3)
        elif kind == "stone":
            round_rect(c, cx - 15, cy - 15, cx + 15, cy + 15, 8, fill=t["obstacle"],
                       outline=lerp_color(t["obstacle"], "#000000", 0.4), width=2)
            c.create_oval(cx - 9, cy - 10, cx - 2, cy - 5,
                          fill=lerp_color(t["obstacle"], "#ffffff", 0.35), outline="")
        elif kind == "star":
            pts = []
            for k in range(10):
                r = 17 if k % 2 == 0 else 7.5
                ang = -math.pi / 2 + k * math.pi / 5
                pts += [cx + r * math.cos(ang), cy + r * math.sin(ang)]
            c.create_polygon(pts, fill=t["accent"], outline="")
        elif kind == "podium":
            for x1, x2, y1, col in ((cx - 20, cx - 7, cy - 2, MEDAL_COLORS[2]),
                                    (cx - 7, cx + 7, cy - 14, MEDAL_COLORS[1]),
                                    (cx + 7, cx + 20, cy + 4, MEDAL_COLORS[3])):
                c.create_rectangle(x1, y1, x2, cy + 15, fill=col, outline="")

    def _help_rules(self) -> None:
        c, t = self.help_canvas, self.theme
        rules = [
            ("apple", "Ăn táo = +10 điểm", "Mỗi quả táo làm rắn dài thêm 1 ô."),
            ("speed", "Rắn nhanh dần", "Càng ăn nhiều táo, rắn càng chạy nhanh."),
            ("noreverse", "Không quay đầu 180°",
             "Đang đi sang phải thì không thể rẽ ngược sang trái ngay."),
            ("stone", "Đụng là thua",
             "Đụng tường, thân mình hoặc đá (mức Khó) thì kết thúc ván."),
            ("star", "Ăn kín bàn = thắng", "Lấp đầy mọi ô trống trên bàn là chiến thắng."),
            ("podium", "Lên bảng xếp hạng",
             "Điểm lưu khi hết ván; mỗi tên giữ điểm cao nhất."),
        ]
        for i, (icon, title, desc) in enumerate(rules):
            cy = 52 + i * 58
            self._help_icon(icon, 54, cy)
            c.create_text(100, cy - 11, text=title, fill=t["text"],
                          font=(FONT, 13, "bold"), anchor="w")
            c.create_text(100, cy + 10, text=desc, fill=t["muted"], font=(FONT, 10),
                          anchor="w", width=TABLE_W - 130)
            if i < len(rules) - 1:
                self._help_line(cy + 29)

    def _help_specials(self) -> None:
        c, t = self.help_canvas, self.theme
        rows = [
            ("red", "Táo đỏ  +10", "Táo thường: +10 điểm, rắn dài thêm 1 ô."),
            ("gold", "Táo vàng  +30", "Chỉ tồn tại khoảng 8 bước. Liều hay không?"),
            ("blue", "Táo xanh  làm chậm", "Rắn chạy chậm lại trong 5 giây."),
            ("orange", "Táo cam  chạy nhanh", "Rắn chạy nhanh hơn trong 5 giây. Giữ tay vững!"),
            ("purple", "Táo tím  x2 điểm", "10 giây: mỗi táo đỏ được 20 điểm."),
            ("poison", "Táo độc  -10", "Trừ 10 điểm, rắn ngắn đi 2 đốt. Tránh ra!"),
            ("bomb", "Táo bom (mức Khó)", "10 giây: đâm vào đá thì đá nổ, không thua!"),
            ("hammer", "Táo đá (mức Khó)", "Ăn vào là tự phá vỡ 1 viên đá ngẫu nhiên."),
        ]
        for i, (kind, title, desc) in enumerate(rows):
            cy = 24 + i * 40
            draw_apple_icon(c, kind, 52, cy + 3, 13, t)
            col = SPECIAL_COLORS[kind][2] if kind in SPECIAL_COLORS else t["text"]
            c.create_text(92, cy - 9, text=title, fill=col, font=(FONT, 13, "bold"), anchor="w")
            c.create_text(92, cy + 11, text=desc, fill=t["muted"], font=(FONT, 10), anchor="w")
            if i < len(rows) - 1:
                self._help_line(cy + 20)
        self._help_footer(334, "Dễ: vàng, xanh, tím, cam  •  Vừa: thêm độc  •  Khó: thêm bom, táo đá.")

    def _mech_icon(self, kind: str, cx: float, cy: float) -> None:
        c, t = self.help_canvas, self.theme
        if kind == "portal":
            c.create_oval(cx - 15, cy - 15, cx + 15, cy + 15, fill="#1a1033",
                          outline="#b388ff", width=2)
            for r, col in ((11, "#7c4dff"), (7, "#40c4ff"), (3, "#ffffff")):
                c.create_arc(cx - r, cy - r, cx + r, cy + r, start=40, extent=240,
                             style="arc", outline=col, width=2)
        elif kind == "ice":
            round_rect(c, cx - 14, cy - 14, cx + 14, cy + 14, 6, fill="#b3e5fc",
                       outline="#4fc3f7", width=2)
            c.create_line(cx - 8, cy + 1, cx - 1, cy - 7, fill="#ffffff", width=2)
            c.create_line(cx - 3, cy + 9, cx + 7, cy - 1, fill="#ffffff", width=2)
        elif kind == "mud":
            c.create_oval(cx - 16, cy - 9, cx + 16, cy + 13, fill="#6d4c41",
                          outline="#3e2723", width=2)
            c.create_oval(cx - 9, cy - 4, cx - 3, cy + 2, fill="#8d6e63", outline="")
            c.create_oval(cx + 3, cy + 2, cx + 9, cy + 8, fill="#8d6e63", outline="")
        elif kind == "twin":
            for dx in (-9, 9):
                c.create_oval(cx + dx - 8, cy - 6, cx + dx + 8, cy + 10,
                              fill=t["apple"], outline="")
                c.create_line(cx + dx, cy - 5, cx + dx + 2, cy - 11, fill="#6d4c41", width=2)
        elif kind == "combo":
            c.create_text(cx, cy, text="x2", fill=SPECIAL_COLORS["gold"][0],
                          font=(FONT, 20, "bold"))
        elif kind == "quest":
            round_rect(c, cx - 14, cy - 14, cx + 14, cy + 14, 6, fill=SPECIAL_COLORS["quest"][1],
                       outline="")
            c.create_text(cx, cy, text="!", fill="#ffffff", font=(FONT, 20, "bold"))

    def _help_mechanics(self) -> None:
        c, t = self.help_canvas, self.theme
        rows = [
            ("portal", "Cổng dịch chuyển", "Vào cổng này ra cổng kia, rồi cổng đổi chỗ. Ô thoát có thân rắn là thua."),
            ("ice", "Ô băng", "Bước vào thì trượt thêm 1 ô theo hướng cũ. Không thua, chỉ dễ lỡ nhịp."),
            ("mud", "Vũng bùn", "Bước vào bị trừ 30 điểm (không dưới 0). Cứ 15 giây bùn đổi chỗ (nhấp nháy báo trước)."),
            ("twin", "Hai táo, chọn một", "Hai táo đỏ ở xa nhau, ăn một quả thì quả kia biến mất."),
            ("combo", "Combo táo", "Ăn táo liên tiếp trong 6 giây: táo kế x1,5 rồi x2. Chậm quá thì mất."),
            ("quest", "Nhiệm vụ nhanh", "Mỗi ván có 2 nhiệm vụ, ví dụ 'ăn 3 táo trong 15 giây' +50 điểm; hết giờ mà chưa xong bị trừ 20 điểm."),
        ]
        for i, (kind, title, desc) in enumerate(rows):
            cy = 36 + i * 52
            self._mech_icon(kind, 50, cy)
            c.create_text(90, cy - 11, text=title, fill=t["text"], font=(FONT, 13, "bold"),
                          anchor="w")
            c.create_text(90, cy + 10, text=desc, fill=t["muted"], font=(FONT, 9),
                          anchor="w", width=TABLE_W - 120)
            if i < len(rows) - 1:
                self._help_line(cy + 27)
        self._help_footer(344, "Combo và nhiệm vụ có ở cả 3 mức. Cổng, băng, bùn chỉ ở mức Vừa; 2 táo có ở Vừa và Khó.")

    def _help_levels(self) -> None:
        c, t = self.help_canvas, self.theme
        descs = {
            "Dễ": "Rắn chạy chậm, không có đá. Có combo,\nnhiệm vụ và 2-3 táo đặc biệt cùng lúc.",
            "Vừa": "Không đá, nhưng nhiều cơ chế vui: cổng,\nbăng, bùn, combo, 2 táo, nhiệm vụ.",
            "Khó": "Rắn nhanh, 6 đá sẵn, đá mọc nhanh; có combo,\n2 táo, nhiệm vụ. Ăn táo đá để phá bớt đá.",
        }
        dim = lerp_color(t["muted"], t["panel"], 0.55)
        for i, mode in enumerate(DIFF_ORDER):
            y = 18 + i * 92
            color = DIFF_COLORS[mode]
            round_rect(c, 16, y, TABLE_W - 16, y + 80, 14,
                       fill=lerp_color(t["panel"], t["bg"], 0.35),
                       outline=lerp_color(t["muted"], t["bg"], 0.65))
            round_rect(c, 16, y + 10, 23, y + 70, 3, fill=color, outline="")
            c.create_text(42, y + 24, text=mode, fill=color, font=(FONT, 18, "bold"),
                          anchor="w")
            c.create_text(42, y + 56, text=descs[mode], fill=t["muted"],
                          font=(FONT, 10), anchor="w")

            # vạch tốc độ
            c.create_text(330, y + 20, text="Tốc độ", fill=t["muted"],
                          font=(FONT, 9, "bold"), anchor="w")
            for k in range(5):
                x = 330 + k * 36
                round_rect(c, x, y + 32, x + 30, y + 44, 4,
                           fill=color if k < SPEED_LEVEL[mode] else dim, outline="")
            n = DIFFICULTIES[mode]["obstacles"]
            cfg = DIFFICULTIES[mode]
            parts = []
            if cfg["obstacles"]:
                parts.append(f"{cfg['obstacles']} đá sẵn")
            if cfg["grow_ticks"]:
                parts.append("đá mọc dần")
            if "hammer" in cfg["specials"]:
                parts.append("táo đá")
            if cfg["portals"]:
                parts.append("cổng")
            if cfg.get("ice_count"):
                parts.append("băng")
            if cfg.get("arrow_count"):
                parts.append("mũi tên")
            if cfg.get("mud_count"):
                parts.append("bùn")
            if cfg.get("combo"):
                parts.append("combo")
            if cfg.get("twin"):
                parts.append("2 táo")
            if cfg.get("quests"):
                parts.append("nhiệm vụ")
            n = bool(parts)
            c.create_text(330, y + 62,
                          text=" • ".join(parts) if n else "Không có đá",
                          width=TABLE_W - 330 - 24,
                          fill=t["text"] if n else t["muted"],
                          font=(FONT, 10, "bold" if n else "normal"), anchor="w")

        self._help_footer(300, "Mỗi mức có bảng xếp hạng riêng. Chọn độ khó ở menu trước khi chơi.")

    # ------------------------------------------------------------------
    # Chat với trợ lý hướng dẫn (logic trả lời nằm trong helpbot.py)
    # ------------------------------------------------------------------
    def _build_chat(self, f: tk.Frame) -> None:
        t = self.theme
        self._btn(f, "Quay lại", lambda: self._show("help"), alt=True, width=200,
                  height=38).pack(side="bottom", pady=10)
        self._heading(f, "TRỢ LÝ HƯỚNG DẪN", 20).pack(pady=(14, 0))
        tk.Label(f, text="Hỏi mình bất cứ điều gì về cách chơi!",
                 font=(FONT, 10), fg=t["muted"], bg=t["bg"]).pack(pady=(0, 8))

        card = tk.Frame(f, bg=t["panel"], highlightthickness=2,
                        highlightbackground=lerp_color(t["muted"], t["bg"], 0.5))
        card.pack()
        self.chat_canvas = tk.Canvas(card, width=CHAT_W - 4, height=CHAT_H,
                                     bg=t["panel"], highlightthickness=0)
        self.chat_canvas.pack()
        self.chat_canvas.bind(
            "<MouseWheel>",
            lambda e: self.chat_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.chat_canvas.bind("<Button-4>", lambda e: self.chat_canvas.yview_scroll(-1, "units"))
        self.chat_canvas.bind("<Button-5>", lambda e: self.chat_canvas.yview_scroll(1, "units"))
        self._chat_drawn = False
        self._chat_y = 10

        chips = tk.Frame(f, bg=t["bg"])
        chips.pack(pady=(8, 2))
        for i, text in enumerate(helpbot.SUGGESTIONS):
            self._btn(chips, text, lambda s=text: self._chat_send(s), alt=True,
                      width=172, height=30, font=(FONT, 10, "bold")
                      ).grid(row=i // 3, column=i % 3, padx=3, pady=3)

        row = tk.Frame(f, bg=t["bg"])
        row.pack(pady=(6, 0))
        self.chat_var = tk.StringVar()
        self.chat_entry = tk.Entry(
            row, textvariable=self.chat_var, font=(FONT, 13), width=34,
            relief="flat", bg=t["panel"], fg=t["text"], insertbackground=t["text"],
            highlightthickness=2, highlightbackground=t["muted"],
            highlightcolor=t["accent"])
        self.chat_entry.pack(side="left", ipady=5, padx=(0, 8))
        self.chat_entry.bind("<Return>", lambda e: self._chat_send())
        self._btn(row, "Gửi", self._chat_send, width=90, height=36).pack(side="left")

    def _chat_add(self, who: str, text: str, record: bool = True) -> None:
        """Vẽ một bong bóng chat. who: 'bot' (bên trái) hoặc 'user' (bên phải)."""
        c, t = self.chat_canvas, self.theme
        if record:
            self._chat_history.append((who, text))
        maxw, font = 360, (FONT, 11)
        if who == "bot":
            c.create_oval(12, self._chat_y + 2, 40, self._chat_y + 30,
                          fill=t["btn"], outline="")
            c.create_text(26, self._chat_y + 16, text="S", fill="#ffffff",
                          font=(FONT, 12, "bold"))
            tid = c.create_text(62, self._chat_y + 10, text=text, anchor="nw",
                                width=maxw, font=font, fill=t["text"])
            fill = lerp_color(t["panel"], t["text"], 0.13)
        else:
            tid = c.create_text(CHAT_W - 30, self._chat_y + 10, text=text, anchor="ne",
                                width=maxw, font=font, fill="#ffffff")
            fill = t["btn"]
        x1, y1, x2, y2 = c.bbox(tid)
        bubble = round_rect(c, x1 - 12, y1 - 8, x2 + 12, y2 + 8, 14, fill=fill, outline="")
        c.tag_lower(bubble, tid)
        self._chat_y = y2 + 8 + 12
        c.configure(scrollregion=(0, 0, CHAT_W, max(self._chat_y, CHAT_H)))
        c.yview_moveto(1.0)

    def _chat_replay(self) -> None:
        """Vẽ lại lịch sử chat (lần đầu mở hoặc sau khi đổi giao diện)."""
        if not self._chat_history:
            self._chat_history.append(("bot", helpbot.GREETING))
        self.chat_canvas.delete("all")
        self._chat_y = 10
        for who, text in list(self._chat_history):
            self._chat_add(who, text, record=False)
        self._chat_drawn = True

    def _chat_send(self, text: str | None = None) -> None:
        if text is None:
            text = self.chat_var.get()
        text = text.strip()
        if not text:
            return
        self.chat_var.set("")
        self._chat_add("user", text)
        # trả lời sau một nhịp ngắn cho giống đang gõ (không liên quan vòng tick game)
        self.root.after(350, lambda: self._chat_answer(text))

    def _chat_answer(self, question: str) -> None:
        if self._closed or not self._chat_drawn:
            return
        try:
            self._chat_add("bot", helpbot.reply(question))
        except tk.TclError:
            pass  # giao diện vừa bị dựng lại (đổi theme)

    # ------------------------------------------------------------------
    # Chuyển màn hình
    # ------------------------------------------------------------------
    def _show(self, name: str) -> None:
        """Hiện màn `name`. Rời màn game thì dừng chuỗi tick."""
        if name != "game":
            self._stop_chain()
            if self._screen == "game":
                self._phase = "idle"
        self._screen = name
        for other, fr in self._frames.items():
            if other == name:
                fr.grid()
            else:
                fr.grid_remove()
        self._frames[name].tkraise()
        if name == "game":
            self._fit_window_to_board()
        else:
            self._ensure_min_window()
        self._stop_menu_anim()
        if name == "menu":
            self._menu_animate()

        if name == "name":
            self.name_error.config(text="")
            self.name_info.config(
                text=f"Độ khó: {self._difficulty}   |   Giao diện: {self._theme_name}")
            self.name_entry.focus_set()
            self.name_entry.select_range(0, "end")
        elif name == "leaderboard":
            self._board_mode = self._difficulty
            self._tab_hover = -1
            self._refresh_leaderboard()
            self.root.focus_set()
        elif name == "chat":
            if not self._chat_drawn:
                self._chat_replay()
            self.chat_entry.focus_set()
        elif name == "help":
            self._help_page = 0
            self._help_hover = -1
            self._refresh_help()
            self.root.focus_set()
        else:
            self.root.focus_set()

    # ------------------------------------------------------------------
    # Vòng đời một ván
    # ------------------------------------------------------------------
    def _select_engine(self) -> None:
        """Mỗi độ khó dùng một SpecialEngine (đá + táo đặc biệt theo cấu hình)."""
        cfg = DIFFICULTIES[self._difficulty]
        eng = self._engines.get(self._difficulty)
        if eng is None:
            eng = LevelEngine(
                self._base_engine.cols, self._base_engine.rows,
                obstacle_count=cfg["obstacles"], kinds=cfg["specials"],
                chance=cfg["special_chance"], grow_every=cfg["grow_every"],
                max_rocks=cfg["max_rocks"], portals=cfg["portals"],
                grow_ticks=cfg["grow_ticks"], rocks_per_apple=cfg["rocks_per_apple"],
                combo=cfg.get("combo", False), twin=cfg.get("twin", False),
                ice_count=cfg.get("ice_count", 0), arrow_count=cfg.get("arrow_count", 0),
                mud_count=cfg.get("mud_count", 0), quests=cfg.get("quests", False),
                max_quests=cfg.get("max_quests"),
                mud_move_seconds=cfg.get("mud_move_seconds", 0),
                max_specials=cfg.get("max_specials", 1))
            self._engines[self._difficulty] = eng
        self.engine = eng

    def _start_game(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.name_error.config(text="Vui lòng nhập tên trước khi chơi.")
            return
        self._player = name
        self._select_engine()
        self.player_label.config(text=f"{name}  |  {self._difficulty}")
        self._show("game")
        self._begin_round()

    def _begin_round(self) -> None:
        """Ván mới: reset engine rồi đếm ngược 3-2-1 trước khi rắn chạy."""
        self.engine.reset()
        self._saved = False
        self._result_lines = []
        self._effects = []
        top = leaderboard.top_scores(1, mode=self._difficulty)
        self._best = top[0]["score"] if top else 0

        self._phase = "countdown"
        self._count = COUNTDOWN_FROM
        self._set_bottom("hint")
        self.render(self.engine.snapshot())

        self._stop_chain()
        self._after_id = self.root.after(1000, self._countdown_tick)

    def _countdown_tick(self) -> None:
        self._after_id = None
        if self._closed or self._screen != "game" or self._phase != "countdown":
            return
        self._count -= 1
        if self._count > 0:
            self._after_id = self.root.after(1000, self._countdown_tick)
        else:
            self._phase = "playing"
            self._after_id = self.root.after(self._current_interval(), self.tick)
        self.render(self.engine.snapshot())

    def _current_interval(self) -> int:
        """Rắn nhanh dần: mỗi quả táo giảm SPEEDUP_MS_PER_APPLE ms."""
        base = DIFFICULTIES[self._difficulty]["tick"]
        apples = getattr(self.engine, "apples_eaten", None)
        if apples is None:
            apples = self.engine.score // POINTS_PER_APPLE
        extra = max(0, apples - SPEEDUP_FREE_APPLES)  # vài quả đầu chưa tăng tốc
        interval = max(MIN_TICK_MS, base - SPEEDUP_MS_PER_APPLE * extra)
        if hasattr(self.engine, "tick_ms"):
            self.engine.tick_ms = interval          # để engine đổi "giây" -> số bước
        # táo cam làm bước ngắn lại; giữ tối thiểu 55 ms để rắn không quá nhanh
        return max(55, int(interval * getattr(self.engine, "slow_factor", 1.0)))

    def _toggle_pause(self) -> None:
        if self._screen != "game":
            return
        if self._phase == "playing":
            self._phase = "paused"
            self._stop_chain()
            self._set_bottom("paused")
            self.render(self.engine.snapshot())
        elif self._phase == "paused":
            self._phase = "playing"
            self._set_bottom("hint")
            self.render(self.engine.snapshot())
            self._stop_chain()
            self._after_id = self.root.after(self._current_interval(), self.tick)

    # ------------------------------------------------------------------
    # Thu / phóng bàn chơi
    # ------------------------------------------------------------------
    def _apply_geometry(self) -> None:
        self.root.geometry(f"{max(BASE_W, self.width + CHROME_W)}x"
                           f"{max(BASE_H, self.height + CHROME_H)}")

    def _fit_window_to_board(self) -> None:
        """Vào màn game: cửa sổ vừa khít bàn chơi (trừ khi đang phóng to tối đa)."""
        if self._is_maximized():
            self._on_window_resize(None)
            return
        scr_w, scr_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        cols, rows = self.engine.cols, self.engine.rows
        best = ZOOM_SIZES[0]
        for sz in ZOOM_SIZES:           # lớn nhất mà cửa sổ vẫn nằm gọn trong màn hình
            if (cols * sz + CHROME_W <= scr_w - 40
                    and rows * sz + CHROME_H <= scr_h - 110):
                best = sz
        self._set_cell_size(best)
        self.root.geometry(f"{max(MIN_W, self.width + CHROME_W)}x"
                           f"{max(MIN_H, self.height + CHROME_H)}")

    def _ensure_min_window(self) -> None:
        """Màn menu/phụ cần ít nhất BASE_W x BASE_H; cửa sổ lớn hơn thì giữ nguyên."""
        if self._is_maximized():
            return
        w, h = self.root.winfo_width(), self.root.winfo_height()
        if w < BASE_W or h < BASE_H:
            self.root.geometry(f"{max(w, BASE_W)}x{max(h, BASE_H)}")

    def _is_maximized(self) -> bool:
        try:
            if self.root.state() == "zoomed":
                return True
            return bool(self.root.attributes("-zoomed"))
        except tk.TclError:
            return False

    def _set_cell_size(self, size: int) -> None:
        """Đổi kích thước 1 ô và vẽ lại bàn chơi (không đụng tới cỡ cửa sổ)."""
        global CELL_SIZE
        if size == CELL_SIZE:
            return
        CELL_SIZE = size
        self.width = self.engine.cols * CELL_SIZE
        self.height = self.engine.rows * CELL_SIZE
        self.canvas.config(width=self.width, height=self.height)
        self.canvas.delete("bg")
        self._draw_board()
        self.canvas.tag_lower("bg")
        self.render(self.engine.snapshot())

    def _on_window_resize(self, event) -> None:
        """Kéo / phóng to cửa sổ: bàn chơi tự co giãn theo (gộp nhiều sự kiện)."""
        if event is not None and event.widget is not self.root:
            return
        if self._screen != "game" or self._closed:
            return
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(60, self._fit_board_to_window)

    def _fit_board_to_window(self) -> None:
        self._resize_job = None
        if self._screen != "game" or self._closed:
            return
        cols, rows = self.engine.cols, self.engine.rows
        w, h = self.root.winfo_width(), self.root.winfo_height()
        size = min((w - CHROME_W) // cols, (h - CHROME_H) // rows)
        self._set_cell_size(max(12, min(80, size)))

    def _zoom(self, step: int) -> None:
        """Phím +/-: phóng to (+1) / thu nhỏ (-1) bàn chơi, cửa sổ đổi theo."""
        if self._screen != "game" or self._closed or self._is_maximized():
            return
        sizes = list(ZOOM_SIZES)
        cur = min(range(len(sizes)), key=lambda i: abs(sizes[i] - CELL_SIZE))
        idx = cur + step
        if not 0 <= idx < len(sizes):
            return
        scr_w, scr_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        cols, rows = self.engine.cols, self.engine.rows
        if step > 0 and not (cols * sizes[idx] + CHROME_W <= scr_w
                             and rows * sizes[idx] + CHROME_H <= scr_h - 60):
            return                      # quá màn hình: dừng
        if sizes[idx] == CELL_SIZE:
            return
        self._set_cell_size(sizes[idx])
        self.root.geometry(f"{max(MIN_W, self.width + CHROME_W)}x"
                           f"{max(MIN_H, self.height + CHROME_H)}")

    def _quit_from_pause(self) -> None:
        """Thoát ra menu từ màn tạm dừng, vẫn lưu điểm hiện tại vào bảng xếp hạng."""
        if self._phase == "paused" and not self._saved:
            self._saved = True
            try:
                leaderboard.save_score(self._player, self.engine.score, self._difficulty)
            except OSError:
                pass
        self._show("menu")

    def _stop_chain(self) -> None:
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _finish_round(self, state: Snapshot) -> None:
        """Ván kết thúc: lưu điểm đúng một lần, hiện nút Chơi lại / Về menu."""
        self._phase = "ended"
        self._set_bottom("ended")
        if self._saved:
            return
        self._saved = True
        try:
            record = state.score > 0 and state.score > self._best
            leaderboard.save_score(self._player, state.score, self._difficulty)
            rank = leaderboard.get_rank(self._player, self._difficulty)
            self._result_lines = [
                f"{self._player}: {state.score} điểm",
                f"Hạng #{rank} mức {self._difficulty}" + ("  -  Kỷ lục mới!" if record else ""),
            ]
        except OSError:
            self._result_lines = ["Không lưu được bảng xếp hạng"]

    # ------------------------------------------------------------------
    # Sự kiện bàn phím
    # ------------------------------------------------------------------
    def on_key(self, event) -> None:
        """IN: Tkinter event.keysym.
        Màn game: mũi tên/WASD -> đổi hướng; Space/P/E -> tạm dừng (Q khi đang tạm dừng: thoát và lưu điểm);
        +/- -> phóng to/thu nhỏ; R -> chơi lại;
        Escape -> về menu. Màn menu: Escape -> thoát. Màn khác: Escape -> menu.
        OUT: None. Phím gõ ở ô nhập tên không bị coi là phím game.
        """
        key = event.keysym

        if self._screen == "game":
            if key in KEY_TO_DIRECTION:
                if self._phase in ("countdown", "playing"):
                    self.engine.change_direction(KEY_TO_DIRECTION[key])
            elif key in ("space", "p", "P", "e", "E"):
                self._toggle_pause()
            elif key in ("q", "Q"):
                if self._phase == "paused":
                    self._quit_from_pause()
            elif key in ("plus", "equal", "KP_Add"):
                self._zoom(1)
            elif key in ("minus", "underscore", "KP_Subtract"):
                self._zoom(-1)
            elif key in ("r", "R"):
                self._begin_round()
            elif key == "Escape":
                self._show("menu")
        elif self._screen == "menu":
            if key == "Escape":
                self._close()
        elif self._screen == "chat":
            if key == "Escape":
                self._show("help")
        elif self._screen == "leaderboard" and key in ("Left", "Right"):
            self._shift_board_mode(-1 if key == "Left" else 1)
        elif self._screen == "help" and key in ("Left", "Right"):
            self._shift_help_page(-1 if key == "Left" else 1)
        elif key == "Escape":
            self._show("menu")

    # ------------------------------------------------------------------
    # Vẽ
    # ------------------------------------------------------------------
    def render(self, state: Snapshot) -> None:
        """IN: Snapshot; OUT: None; vẽ ô (x,y) tại pixel
        (x*CELL_SIZE, y*CELL_SIZE), hiển thị điểm/trạng thái.
        apple=None thì không vẽ táo. Không thay đổi engine.
        """
        if self._closed:
            return

        c = self.canvas
        t = self.theme
        c.delete("dyn")
        self._frame += 1

        for (px_, py_) in getattr(self.engine, "portals", {}):
            self._draw_portal(px_, py_)

        for (ix, iy) in getattr(self.engine, "ice", ()):
            self._draw_ice(ix, iy)
        for (ax, ay), adir in getattr(self.engine, "arrows", {}).items():
            self._draw_arrow_tile(ax, ay, adir)
        warn = (hasattr(self.engine, "mud_seconds")
                and 0 < self.engine.mud_seconds() <= 3)   # sắp đổi chỗ: bùn nhấp nháy
        if not (warn and self._frame % 2 == 0):
            for (mx, my) in getattr(self.engine, "mud", ()):
                self._draw_mud(mx, my)

        new_rocks = getattr(self.engine, "rock_age", {})
        for (x, y) in getattr(self.engine, "obstacles", ()):
            self._draw_stone(x, y)
            if (x, y) in new_rocks and self._frame % 2 == 0:   # đá mới mọc: nhấp nháy viền
                px, py = cell_to_pixel(x, y)
                c.create_rectangle(px + 1, py + 1, px + CELL_SIZE - 1, py + CELL_SIZE - 1,
                                   outline=t["accent"], width=2, tags="dyn")

        if state.apple is not None:
            self._draw_apple(state.apple)
        apple2 = getattr(self.engine, "apple2", None)
        if apple2 is not None:
            self._draw_apple(apple2)
        self._draw_special()

        self._draw_snake(state)
        self._draw_aura(state)
        self._draw_effects()

        # nhãn điểm (nháy màu vàng khi vừa ăn táo)
        flash = any(e["age"] <= 1 for e in self._effects)
        self.score_label.config(text=f"Score: {state.score}",
                                fg=t["accent"] if flash else t["text"])
        self.best_label.config(text=f"Best: {max(self._best, state.score)}")
        eng = self.engine
        if hasattr(eng, "effect_seconds"):
            s_slow, s_x2 = eng.effect_seconds("slow"), eng.effect_seconds("x2")
            s_bomb = eng.effect_seconds("bomb")
            self.fx_bomb.config(text=f"BOM {math.ceil(s_bomb)}s" if s_bomb > 0 else "")
            self.fx_slow.config(text=f"CHẬM {math.ceil(s_slow)}s" if s_slow > 0 else "")
            s_fast = eng.effect_seconds("fast")
            self.fx_fast.config(text=f"NHANH {math.ceil(s_fast)}s" if s_fast > 0 else "")
            self.fx_x2.config(text=f"x2 {math.ceil(s_x2)}s" if s_x2 > 0 else "")
        if hasattr(eng, "combo_count"):
            combo_on = eng.use_combo and eng.combo_count > 0
            self.fx_combo.config(
                text=(f"COMBO: táo kế x{eng.next_combo_mult:g}  {math.ceil(eng.combo_seconds())}s"
                      if combo_on else ""))
            q = eng.quest if eng.use_quests else None
            self.fx_quest.config(
                text=(f"NHIỆM VỤ: ăn {q.need} táo  {q.got}/{q.need}  "
                      f"{math.ceil(eng.quest_seconds())}s  +{q.reward}" if q else ""))

        # lớp phủ theo trạng thái
        if state.status == "GAME_OVER":
            lines = [("GAME OVER", (FONT, 26, "bold"), "#ff6b6b")]
            lines += [(s, (FONT, 12, "bold"), t["text"]) for s in self._result_lines]
            self._draw_panel(lines)
        elif state.status == "WON":
            lines = [("CHIẾN THẮNG!", (FONT, 26, "bold"), t["accent"])]
            lines += [(s, (FONT, 12, "bold"), t["text"]) for s in self._result_lines]
            self._draw_panel(lines)
        elif self._phase == "paused":
            self._draw_panel([
                ("TẠM DỪNG", (FONT, 26, "bold"), t["accent"]),
                ("E: tiếp tục   |   Q: thoát (lưu điểm)", (FONT, 12), t["muted"]),
            ])
        elif self._phase == "countdown":
            cx, cy = self.width / 2, self.height / 2
            c.create_oval(cx - 55, cy - 55, cx + 55, cy + 55, fill=t["panel"],
                          outline=t["accent"], width=3, tags="dyn")
            c.create_text(cx, cy, text=str(self._count), fill=t["accent"],
                          font=(FONT, 56, "bold"), tags="dyn")

    def _draw_portal(self, x: int, y: int) -> None:
        """Cổng dịch chuyển: các vòng xoáy quay quanh tâm ô."""
        c = self.canvas
        px, py = cell_to_pixel(x, y)
        cx, cy = px + CELL_SIZE / 2, py + CELL_SIZE / 2
        c.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill="#1a1033",
                      outline="#b388ff", width=2, tags="dyn")
        spin = (self._frame * 40) % 360
        for k, (r, col) in enumerate(((11, "#7c4dff"), (7, "#40c4ff"), (3, "#ffffff"))):
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=(spin * (1 if k % 2 == 0 else -1)) % 360, extent=240,
                         style="arc", outline=col, width=2, tags="dyn")

    def _draw_ice(self, x: int, y: int) -> None:
        """Ô băng: ô vuông xanh nhạt có vệt sáng."""
        c = self.canvas
        px, py = cell_to_pixel(x, y)
        round_rect(c, px + 2, py + 2, px + CELL_SIZE - 2, py + CELL_SIZE - 2, 6,
                   fill="#b3e5fc", outline="#4fc3f7", width=2, tags="dyn")
        c.create_line(px + 7, py + 12, px + 14, py + 6, fill="#ffffff", width=2, tags="dyn")
        c.create_line(px + 12, py + 22, px + 22, py + 12, fill="#ffffff", width=2, tags="dyn")

    def _draw_mud(self, x: int, y: int) -> None:
        """Vũng bùn: đốm nâu có bọt, bước vào bị trừ điểm."""
        c = self.canvas
        px, py = cell_to_pixel(x, y)
        c.create_oval(px + 2, py + 6, px + CELL_SIZE - 2, py + CELL_SIZE - 3,
                      fill="#6d4c41", outline="#3e2723", width=2, tags="dyn")
        c.create_oval(px + 6, py + 10, px + 12, py + 15, fill="#8d6e63", outline="", tags="dyn")
        c.create_oval(px + 16, py + 15, px + 22, py + 20, fill="#8d6e63", outline="", tags="dyn")
        c.create_oval(px + 14, py + 9, px + 17, py + 12, fill="#a1887f", outline="", tags="dyn")

    def _draw_arrow_tile(self, x: int, y: int, direction: str) -> None:
        """Ô mũi tên: nền tối viền cam, mũi tên chỉ hướng đẩy rắn."""
        c, t = self.canvas, self.theme
        px, py = cell_to_pixel(x, y)
        cx, cy = px + CELL_SIZE / 2, py + CELL_SIZE / 2
        round_rect(c, px + 2, py + 2, px + CELL_SIZE - 2, py + CELL_SIZE - 2, 6,
                   fill=lerp_color(t["panel"], "#000000", 0.25), outline="#ffab40",
                   width=2, tags="dyn")
        dx, dy = DIR_VECTORS[direction]
        qx, qy = -dy, dx                                   # vuông góc với hướng
        tip = (cx + dx * 10, cy + dy * 10)
        bx, by = cx + dx * 1, cy + dy * 1
        c.create_line(cx - dx * 9, cy - dy * 9, bx, by, fill="#ffab40", width=4, tags="dyn")
        c.create_polygon(tip[0], tip[1], bx + qx * 7, by + qy * 7, bx - qx * 7, by - qy * 7,
                         fill="#ffab40", outline="", tags="dyn")

    def _draw_stone(self, x: int, y: int) -> None:
        c, t = self.canvas, self.theme
        px, py = cell_to_pixel(x, y)
        round_rect(c, px + 3, py + 3, px + CELL_SIZE - 3, py + CELL_SIZE - 3, 7,
                   fill=t["obstacle"], outline=lerp_color(t["obstacle"], "#000000", 0.4),
                   width=2, tags="dyn")
        c.create_oval(px + 8, py + 7, px + 15, py + 12,
                      fill=lerp_color(t["obstacle"], "#ffffff", 0.35),
                      outline="", tags="dyn")

    def _draw_special(self) -> None:
        """Táo đặc biệt kèm vòng đếm ngược; nhấp nháy khi sắp biến mất."""
        specials = getattr(self.engine, "specials", None)
        if specials is None:                       # engine cũ chỉ có một táo đặc biệt
            one = getattr(self.engine, "special", None)
            specials = [one] if one is not None else []
        for sp in list(specials):
            self._draw_one_special(sp)

    def _draw_one_special(self, sp) -> None:
        c, t = self.canvas, self.theme
        px, py = cell_to_pixel(*sp.pos)
        cx, cy = px + CELL_SIZE / 2, py + CELL_SIZE / 2 + 2
        ring = SPECIAL_COLORS[sp.kind][1 if sp.kind in ("poison", "bomb") else 0]
        c.create_oval(cx - 14, cy - 14, cx + 14, cy + 14,
                      outline=lerp_color(ring, t["board_b"], 0.7), width=2, tags="dyn")
        frac = max(0.0, min(1.0, sp.ttl / sp.max_ttl))
        c.create_arc(cx - 14, cy - 14, cx + 14, cy + 14, start=90,
                     extent=max(2, 359.9 * frac), style="arc", outline=ring,
                     width=2, tags="dyn")
        if sp.ttl <= 3 and self._frame % 2 == 0:
            return  # nhấp nháy cảnh báo
        draw_apple_icon(c, sp.kind, cx, cy, 10, t, tags="dyn")

    def _draw_apple(self, pos) -> None:
        c, t = self.canvas, self.theme
        px, py = cell_to_pixel(*pos)
        cx, cy = px + CELL_SIZE / 2, py + CELL_SIZE / 2 + 2
        r = 10 + (0, 1, 2, 1)[self._frame % 4]  # nhấp nháy nhẹ
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=t["apple"],
                      outline=lerp_color(t["apple"], "#000000", 0.3), width=1, tags="dyn")
        c.create_oval(cx - r + 3, cy - r + 3, cx - r + 9, cy - r + 8,
                      fill=lerp_color(t["apple"], "#ffffff", 0.6), outline="", tags="dyn")
        c.create_line(cx, cy - r + 1, cx + 2, cy - r - 5, fill="#6d4c41",
                      width=2, tags="dyn")
        c.create_oval(cx + 2, cy - r - 8, cx + 11, cy - r - 2, fill=t["leaf"],
                      outline="", tags="dyn")

    def _draw_snake(self, state: Snapshot) -> None:
        """Thân là chuỗi hình tròn nối bằng hình chữ nhật (như ống), màu chuyển
        dần từ đầu về đuôi. Đầu có hai mắt nhìn theo hướng đi."""
        c, t = self.canvas, self.theme
        dead = state.status == "GAME_OVER"
        body = list(state.body)
        n = len(body)

        def center(cell):
            return cell[0] * CELL_SIZE + CELL_SIZE / 2, cell[1] * CELL_SIZE + CELL_SIZE / 2

        colors, radii = [], []
        for i in range(n):
            if i == 0:
                col = "#c62828" if dead else t["head"]
                radii.append(14)
            else:
                frac = (i - 1) / (n - 2) if n > 2 else 0.0
                col = lerp_color(t["body_a"], t["body_b"], frac)
                if dead:
                    col = lerp_color(col, "#8d8d8d", 0.6)
                radii.append(10 if (n > 3 and i == n - 1) else 12)
            colors.append(col)

        for i in range(n - 1, -1, -1):  # đuôi -> đầu, đầu vẽ đè lên trên
            cx, cy = center(body[i])
            r = radii[i]
            if i + 1 < n:  # nối với đốt phía sau
                ax, ay = center(body[i + 1])
                hw = min(r, radii[i + 1])
                col = lerp_color(colors[i], colors[i + 1], 0.5)
                if ax == cx:
                    c.create_rectangle(cx - hw, min(cy, ay), cx + hw, max(cy, ay),
                                       fill=col, outline="", tags="dyn")
                else:
                    c.create_rectangle(min(cx, ax), cy - hw, max(cx, ax), cy + hw,
                                       fill=col, outline="", tags="dyn")
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colors[i],
                          outline="", tags="dyn")

        if n:
            self._draw_eyes(center(body[0]), state.direction, dead)

    def _draw_aura(self, state: Snapshot) -> None:
        """Vòng sáng quanh đầu rắn cho mỗi hiệu ứng đang chạy (chậm / x2 / bom)."""
        fx = getattr(self.engine, "effects", None)
        if not fx or not state.body or state.status == "GAME_OVER":
            return
        hx, hy = state.body[0]
        cx, cy = hx * CELL_SIZE + CELL_SIZE / 2, hy * CELL_SIZE + CELL_SIZE / 2
        names = {"blue": "slow", "orange": "fast", "purple": "x2", "bomb": "bomb"}
        rings = [SPECIAL_COLORS[k][0] for k in ("blue", "orange", "purple", "bomb")
                 if fx.get(names[k], 0) > 0]
        for i, col in enumerate(rings):
            r = 17 + 3 * i
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col,
                                    width=2, tags="dyn")

    def _draw_eyes(self, center, direction, dead: bool) -> None:
        c = self.canvas
        cx, cy = center
        fx, fy = DIR_VECTORS[direction]
        sx, sy = -fy, fx
        for sign in (-1, 1):
            ex = cx + fx * 5 + sx * 6 * sign
            ey = cy + fy * 5 + sy * 6 * sign
            if dead:  # mắt dấu X
                c.create_line(ex - 3, ey - 3, ex + 3, ey + 3, fill="white", width=2, tags="dyn")
                c.create_line(ex - 3, ey + 3, ex + 3, ey - 3, fill="white", width=2, tags="dyn")
            else:
                c.create_oval(ex - 4.5, ey - 4.5, ex + 4.5, ey + 4.5, fill="white",
                              outline="", tags="dyn")
                px_, py_ = ex + fx * 1.5, ey + fy * 1.5
                c.create_oval(px_ - 2.2, py_ - 2.2, px_ + 2.2, py_ + 2.2,
                              fill="#111111", outline="", tags="dyn")

    def _draw_effects(self) -> None:
        t = self.theme
        for e in self._effects:
            frac = e["age"] / EFFECT_TICKS
            self.canvas.create_text(
                e["x"], e["y"] - 6 - e["age"] * 8,
                text=e.get("text", f"+{POINTS_PER_APPLE}"),
                font=(FONT, 14, "bold"),
                fill=lerp_color(e.get("color") or t["accent"], t["board_b"], frac),
                tags="dyn")

    def _advance_effects(self) -> None:
        for e in self._effects:
            e["age"] += 1
        self._effects = [e for e in self._effects if e["age"] < EFFECT_TICKS]

    def _draw_panel(self, lines) -> None:
        """Hộp thông báo giữa bàn; lines = [(text, font, color), ...]."""
        c, t = self.canvas, self.theme
        heights = [f[1] + 12 for (_, f, _) in lines]
        total = sum(heights) + 26
        cx, cy = self.width / 2, self.height / 2
        round_rect(c, cx - 166, cy - total / 2 + 8, cx + 174, cy + total / 2 + 8, 18,
                   fill=lerp_color(t["board_b"], "#000000", 0.5), outline="", tags="dyn")
        round_rect(c, cx - 170, cy - total / 2, cx + 170, cy + total / 2, 18,
                   fill=t["panel"], outline=t["accent"], width=2, tags="dyn")
        y = cy - total / 2 + 13
        for (text, font, color), h in zip(lines, heights):
            c.create_text(cx, y + h / 2, text=text, font=font, fill=color, tags="dyn")
            y += h

    # ------------------------------------------------------------------
    # Vòng lặp game
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """OUT: None; step -> snapshot -> (lưu điểm nếu kết thúc) -> render
        -> root.after(interval, tick). Chỉ chạy khi đang chơi; chỉ có một chuỗi
        after; sau khi kết thúc vẫn nhấn R hoặc bấm nút để chơi lại."""
        self._after_id = None
        if self._closed or self._screen != "game" or self._phase != "playing":
            return

        result = self.engine.step()
        state = self.engine.snapshot()

        self._advance_effects()
        if state.body:
            hx, hy = state.body[0]
            events = getattr(self.engine, "last_events", None)
            if events is None:  # engine thường: chỉ có "+10" khi ăn táo
                events = [("red", f"+{POINTS_PER_APPLE}")] if result.ate else []
            for idx, (kind, text) in enumerate(events):
                self._effects.append({
                    "x": min(self.width - 38, max(38, hx * CELL_SIZE + CELL_SIZE / 2)),
                    "y": hy * CELL_SIZE + CELL_SIZE / 2 - idx * 16,
                    "age": 0, "text": text,
                    "color": SPECIAL_COLORS[kind][2] if kind in SPECIAL_COLORS else None,
                })

        if state.status != "RUNNING":
            self._finish_round(state)
        else:
            self._after_id = self.root.after(self._current_interval(), self.tick)
        self.render(state)

    def run(self) -> None:
        """OUT: None; hiện menu và gọi root.mainloop().
        Chuỗi tick bắt đầu sau khi người chơi bấm 'Bắt đầu' và đếm ngược xong."""
        self._show("menu")
        self.root.mainloop()

    # ------------------------------------------------------------------
    # Đóng cửa sổ
    # ------------------------------------------------------------------
    def _close(self) -> None:
        """Hủy lịch after đang chờ rồi đóng cửa sổ."""
        if self._closed:
            return
        self._closed = True
        self._stop_chain()
        self._stop_menu_anim()
        self.root.destroy()
