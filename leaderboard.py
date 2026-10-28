"""Lưu và xếp hạng điểm người chơi (file leaderboard.json cạnh code).

Mỗi độ khó có BẢNG RIÊNG. Trong một bảng, mỗi tên chỉ giữ MỘT dòng:
điểm cao nhất của tên đó ở độ khó ấy (không phân biệt hoa/thường).
Xếp hạng: điểm cao hơn đứng trước; bằng điểm thì người đạt trước đứng trước.
Module này không đụng tới engine hay UI.
"""
import json
import os
from datetime import datetime

LEADERBOARD_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "leaderboard.json"
)
DEFAULT_MODE = "Vừa"  # dữ liệu cũ không có độ khó được xem là "Vừa"


def load_scores() -> list[dict]:
    """Đọc file; file chưa có hoặc hỏng -> danh sách rỗng.
    Mỗi phần tử: {"name": str, "score": int, "date": str, "mode": str}."""
    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []

    if not isinstance(data, list):
        return []

    entries = []
    for item in data:
        if (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("score"), int)
            and not isinstance(item.get("score"), bool)
        ):
            entries.append(
                {
                    "name": item["name"],
                    "score": item["score"],
                    "date": str(item.get("date", "")),
                    "mode": str(item.get("mode") or DEFAULT_MODE),
                }
            )
    return entries


def _write(entries: list[dict]) -> None:
    tmp = LEADERBOARD_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.replace(tmp, LEADERBOARD_FILE)


def save_score(name: str, score: int, mode: str = DEFAULT_MODE) -> None:
    """Lưu điểm vào bảng của độ khó `mode`.
    Tên đã có trong bảng đó: chỉ cập nhật khi điểm mới cao hơn."""
    name = name.strip()
    if not name:
        raise ValueError("name must not be empty")

    entries = load_scores()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for entry in entries:
        if entry["mode"] == mode and entry["name"].casefold() == name.casefold():
            if score > entry["score"]:
                entry["score"] = score
                entry["date"] = now
                _write(entries)
            return

    entries.append({"name": name, "score": score, "date": now, "mode": mode})
    _write(entries)


def _ranked(mode: str | None) -> list[dict]:
    entries = load_scores()
    if mode is not None:
        entries = [e for e in entries if e["mode"] == mode]
    entries.sort(key=lambda e: -e["score"])  # sort ổn định: bằng điểm giữ thứ tự cũ
    return entries


def top_scores(limit: int = 10, mode: str | None = None) -> list[dict]:
    """Bảng xếp hạng của độ khó `mode` (None = gộp tất cả), tối đa `limit` dòng."""
    return _ranked(mode)[:limit]


def get_rank(name: str, mode: str | None = None) -> int | None:
    """Hạng (bắt đầu từ 1) của tên trong bảng `mode`; không có -> None."""
    for i, entry in enumerate(_ranked(mode), start=1):
        if entry["name"].casefold() == name.strip().casefold():
            return i
    return None