"""Snake help assistant (keyword-based chatbot, runs offline, answers in English).

Không cần internet, API key hay thư viện ngoài. Cách hoạt động:
1. Normalize the question: lowercase, strip Vietnamese accents, drop odd characters.
2. Score each topic = number of keywords found (whole word / phrase match).
3. Reply with the best-scoring topic; if nothing matches, suggest topics.
"""
import difflib
import re
import unicodedata

GREETING = (
    "Hello! I'm the Snake help assistant.\n"
    "Ask me about how to play, controls, difficulty, scoring, "
    "the leaderboard... or tap a suggestion below."
)

SUGGESTIONS = [
    "How to play",
    "Controls",
    "Difficulty",
    "Special apples",
    "Leaderboard",
    "Tips",
]

FALLBACK = (
    "I didn't understand that. Try asking about: how to play, controls, "
    "pause, restart, difficulty, rocks, scoring, special apples, speed, "
    "the leaderboard, appearance or tips!"
)

EMPTY_PROMPT = "Please type a question, for example: 'How to play?'"

# (keywords, answer). Keywords are English plus the old accent-free Vietnamese
# ones, so Vietnamese questions still get answered (in English).
TOPICS = [
    ([
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'xin chao', 'chao', 'alo'],
     'Hi there! What would you like to know about Snake Eats Apples?'),
    ([
        'thanks', 'thank you', 'thx', 'cam on', 'thank', 'cảm ơn'],
     "You're welcome! Have fun and climb the leaderboard!"),
    ([
        'who are you', 'your name', 'what are you', 'bot', 'assistant', 'ban la ai', 'ten gi',
        'tro ly'],
     "I'm the Snake help assistant. I answer with ready-made replies, so I only know things about this game."),
    ([
        'how to play', 'how do i play', 'guide', 'instructions', 'objective', 'goal', 'rules',
        'start', 'begin', 'tutorial', 'about the game', 'cach choi', 'huong dan',
        'choi nhu the nao', 'choi the nao', 'muc tieu', 'bat dau', 'luat', 'luat choi',
        'lam sao choi', 'choi sao', 'choi lam the nao', 'choi ra sao', 'choi nhu nao',
        'choi kieu gi', 'choi the nao', 'huong dan choi', 'gioi thieu'],
     'GOAL: steer the snake to eat red apples; each one gives +10 points and makes the snake 1 cell longer.\n'
     'The edges wrap around: leave on the left and you appear on the right, leave at the top and you appear at the bottom. '
     'Hitting your own body or a rock ends the game. Fill the whole board to win.\n'
     "Click 'Play', enter your name, then play after the 3-2-1 countdown."),
    ([
        'controls', 'keys', 'keyboard', 'move', 'movement', 'arrow', 'arrows', 'wasd', 'steer',
        'turn', 'direction', 'buttons', 'phim', 'dieu khien', 'di chuyen', 'bam', 'mui ten',
        'dieu huong', 'doi huong'],
     'Steer: arrow keys or W A S D.\n'
     "Pause: E, Space or P (or the 'Pause' button). While paused, press Q to quit; your score is still saved.\n"
     "Zoom: + / - keys, Ctrl + mouse wheel, the window's maximize button, or drag the window edge (the board resizes automatically).\n"
     'Restart: R. Back to menu: Esc.\n'
     'Only one direction change is accepted between two steps.'),
    ([
        'pause', 'resume', 'stop', 'space', 'freeze', 'tam dung', 'dung lai', 'dung game'],
     "Press E (or Space, P, or the 'Pause' button) to pause, and again or click 'Resume' to continue. While paused, press Q or click 'Quit' to go to the menu and keep your score."),
    ([
        'restart', 'play again', 'retry', 'reset', 'again', 'replay', 'choi lai', 'lai tu dau',
        'phim r'],
     "Press R to restart right away (with the 3-2-1 countdown). After a game over there is also a 'Play Again' button."),
    ([
        'quit', 'exit', 'escape', 'esc', 'menu', 'leave', 'back to menu', 'thoat', 'quay ve'],
     'Esc: back to the menu (on the menu it quits the game). If you leave a round with Esc, the score is not saved (to keep it, pause and press Q).'),
    ([
        'reverse', '180', 'turn around', 'go back', 'opposite', 'quay nguoc', 'di nguoc',
        'dao chieu'],
     'The snake cannot turn 180 degrees. For example, while moving right, pressing left does nothing.'),
    ([
        'score', 'points', 'point', 'how many points', 'scoring', 'diem', 'tinh diem',
        'bao nhieu diem', 'cong diem'],
     "Each red apple gives +10 points (gold apple +30, poison apple -10). Your score is at the top right, next to your 'Best' for the current difficulty."),
    ([
        'speed', 'fast', 'slow', 'faster', 'slower', 'speed up', 'toc do', 'nhanh', 'cham',
        'tang toc', 'nhanh dan'],
     'The snake starts slow. For the first 5 apples the speed stays the same; from the 6th apple each one makes it a little FASTER, up to about 12 steps per second. Starting speed: Easy ~4 steps/s, Medium ~4.5 steps/s, Hard ~5.5 steps/s.'),
    ([
        'difficulty', 'difficulties', 'easy', 'medium', 'hard', 'level', 'levels', 'mode',
        'modes', 'do kho', 'de', 'vua', 'kho', 'muc do', 'cap do', 'che do'],
     '3 difficulties (choose in the menu):\n'
     '- Easy: slow snake, combos, quests and 2-3 special apples at once.\n'
     '- Medium: no rocks, but portals, ice, mud, combos, twin apples and quick quests.\n'
     '- Hard: faster, 6 starting rocks, rocks keep growing, rock apples, bomb apples, combos, twin apples and quick quests.\n'
     'Each difficulty has its own leaderboard.'),
    ([
        'combo', 'streak', 'multiplier', 'consecutive', 'x1 5', 'lien tiep', 'nhan diem',
        'nhan doi'],
     'COMBO (all 3 levels): eat red apples less than 6 seconds apart and the next apple is worth x1.5, then x2. Wait more than 6 seconds and the combo is lost. A combo timer is shown above the board.'),
    ([
        'twin', 'two apples', 'twin apples', 'pick one', '2 apples', 'hai tao', '2 tao',
        'tao doi', 'chon mot', 'hai qua'],
     'Medium and Hard always have TWO red apples far apart from each other. Eat one and the other disappears, then both respawn. Pick the safer one.'),
    ([
        'ice', 'ice tile', 'slide', 'slippery', 'sliding', 'bang', 'o bang', 'truot', 'trượt',
        'trơn', 'tron'],
     'ICE TILE (light blue, Medium): step on it and the snake slides 1 extra cell in its current direction. Not fatal, but easy to mistime if an apple or a turn comes right after.'),
    ([
        'mud', 'mud puddle', 'lose points', 'penalty', 'bun', 'vung bun', 'o bun', 'tru diem',
        'mat diem', 'bi tru'],
     'MUD PUDDLE (brown, Medium): step in and lose 30 points (never below 0). That puddle disappears and a new one appears elsewhere. Every 15 seconds all the mud moves (it blinks for 3 seconds first), so watch your path.'),
    ([
        'quest', 'quests', 'mission', 'missions', 'challenge', 'bonus', 'nhiem vu', 'thuong',
        'thu thach'],
     "QUICK QUESTS (all 3 levels): now and then a task like 'eat 3 apples in 15 seconds' appears above the board. Each round has only 2 quests. Complete one for +30 / +50 / +80 points; if time runs out you lose 20 points (never below 0)."),
    ([
        'rock', 'rocks', 'stone', 'stones', 'obstacle', 'obstacles', 'da', 'vat can',
        'chuong ngai', 'tang da', 'hon da', 'da moc', 'moc dan'],
     'Rocks only appear on Hard (Medium uses other mechanics instead). Hitting a rock ends the game (unless a bomb is active). Rocks GROW over time. To destroy rocks, eat a ROCK APPLE (grey with cracks): each one smashes 1 rock. New rocks blink with a yellow outline. Apples never spawn on rocks and rocks never trap the snake, so a path always exists.'),
    ([
        'portal', 'portals', 'teleport', 'teleporter', 'cong', 'cong dich chuyen',
        'dich chuyen', 'xoay'],
     'Medium has a pair of PORTALS (purple-blue swirls). Enter one and you exit from the other, continuing in the same direction; after use the pair moves elsewhere. Careful: if the exit cell holds your body, you lose.'),
    ([
        'special apple', 'special apples', 'special', 'golden apple', 'gold apple',
        'blue apple', 'purple apple', 'poison', 'poison apple', 'bomb', 'bomb apple',
        'orange apple', 'rock apple', 'power up', 'power ups', 'effect', 'effects',
        'tao dac biet', 'dac biet', 'tao vang', 'tao xanh', 'tao tim', 'tao doc', 'tao bom',
        'bom', 'tao cam', 'tao da', 'tao xam', 'x2', 'hieu ung', 'xanh duong', 'tao mau'],
     'Besides the red apple (+10) there are special apples that only last a while:\n'
     '- Gold apple: +30 points, only ~8 steps.\n'
     '- Blue apple: snake slows down for 5 seconds.\n'
     '- Orange apple: snake runs FASTER for 5 seconds.\n'
     '- Purple apple: x2 points for 10 seconds.\n'
     '- Poison apple: -10 points and 2 fewer segments. Avoid it!\n'
     '- Bomb apple (Hard): for 10 seconds, hitting a rock blows it up and you survive.\n'
     '- Rock apple (grey, cracked): eating it smashes 1 rock.\n'
     'Easy has gold/blue/purple/orange, Medium adds poison, Hard adds poison, bomb and rock apples.\n'
     'On all levels there can be 2-3 special apples at once, each vanishing after its own number of steps; poison and rock apples (Hard) show up fairly often.'),
    ([
        'apple', 'red apple', 'eat apple', 'food', 'tao', 'an tao', 'tao do', 'qua tao'],
     "Red apples appear randomly on empty cells. Eating one gives +10 points, makes the snake 1 cell longer and a bit faster. Ask about 'special apples' to learn about the other kinds."),
    ([
        'lose', 'die', 'dead', 'game over', 'crash', 'collision', 'hit', 'thua', 'chet',
        'dung tuong', 'dung than', 'va cham'],
     "You lose when the snake's head hits its own body or a rock (walls do not kill: the snake wraps to the other side). Your score is then saved to the leaderboard, and you get 'Play Again' / 'Main Menu' buttons."),
    ([
        'win', 'victory', 'fill board', 'full board', 'winning', 'thang', 'chien thang',
        'kin ban'],
     "Fill every empty cell so the snake covers the whole board and you win ('VICTORY!'). It is very hard, so play carefully!"),
    ([
        'leaderboard', 'ranking', 'rank', 'top', 'high score', 'highscore', 'best score',
        'record', 'save score', 'name', 'xep hang', 'bang xep hang', 'hang', 'luu diem', 'ten',
        'ky luc'],
     'Your score is saved when a round ends. Each difficulty has its own top 10 (click the Easy / Medium / Hard tab or use the left / right arrow keys). Each name keeps only its best score.'),
    ([
        'theme', 'themes', 'appearance', 'color', 'colour', 'dark', 'light', 'ocean', 'forest',
        'skin', 'snake color', 'snake style', 'style', 'customize', 'giao dien', 'mau', 'toi',
        'sang', 'dai duong', 'rung', 'doi mau'],
     "Open 'Appearance' in the menu to pick a theme (Forest, Light or Ocean), a snake style (Classic, Block, Striped, Spotted) and a snake color."),
    ([
        'countdown', '3 2 1', 'get ready', 'ready', 'dem nguoc', 'chuan bi'],
     'Every round starts with a 3-2-1 countdown so you can get ready. You can already pick your first direction during the countdown.'),
    ([
        'tip', 'tips', 'trick', 'tricks', 'strategy', 'advice', 'how to win',
        'how to get better', 'pro', 'meo', 'bi quyet', 'choi gioi', 'loi khuyen',
        'kinh nghiem', 'kinh nghiem', 'khong thua'],
     'Tips:\n'
     "- Look 2-3 cells ahead and don't change direction constantly.\n"
     '- Hug the edges and leave room to turn around when the snake is long.\n'
     '- Play Easy first to learn the rhythm, then move up to Hard.\n'
     '- Use Space to pause and plan your next move.'),
]


def normalize(text: str) -> str:
    """Viết thường, bỏ dấu tiếng Việt, chỉ giữ chữ/số, gọn khoảng trắng."""
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def _fuzzy_in(word: str, qwords: set) -> bool:
    """Từ có trong câu hỏi, cho phép gõ sai nhẹ (từ >= 4 ký tự)."""
    if word in qwords:
        return True
    if len(word) < 4:
        return False
    return bool(difflib.get_close_matches(word, qwords, n=1, cutoff=0.84))


def _score(q: str, qwords: set, keywords: list) -> float:
    score = 0.0
    for kw in keywords:
        kw_n = normalize(kw)
        if not kw_n:
            continue
        if f" {kw_n} " in q:                       # khớp nguyên cụm, đúng thứ tự
            score += 1 + kw_n.count(" ")
            continue
        parts = kw_n.split()
        if len(parts) >= 2 and all(_fuzzy_in(p, qwords) for p in parts):
            score += 0.9 * len(parts)              # đủ các từ nhưng đảo thứ tự
        elif len(parts) == 1 and len(parts[0]) >= 4 and _fuzzy_in(parts[0], qwords):
            score += 0.8                           # gõ sai chính tả nhẹ
    return score


def reply(question: str) -> str:
    """IN: câu hỏi của người chơi. OUT: câu trả lời (luôn là str, không ném lỗi)."""
    q = f" {normalize(question)} "
    if q.strip() == "":
        return EMPTY_PROMPT

    qwords = set(q.split())
    best_score, best_answer = 0.0, FALLBACK
    for keywords, answer in TOPICS:
        score = _score(q, qwords, keywords)
        if score > best_score:
            best_score, best_answer = score, answer
    return best_answer
