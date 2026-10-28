"""Trợ lý hướng dẫn chơi Snake (chatbot dựa trên từ khóa, chạy offline).

Không cần internet, API key hay thư viện ngoài. Cách hoạt động:
1. Chuẩn hóa câu hỏi: viết thường, bỏ dấu tiếng Việt, bỏ ký tự lạ.
2. Chấm điểm từng chủ đề = số từ khóa xuất hiện (khớp nguyên từ/cụm từ).
3. Trả lời chủ đề điểm cao nhất; không khớp gì thì gợi ý các chủ đề.
"""
import difflib
import re
import unicodedata

GREETING = (
    "Xin chào! Mình là trợ lý hướng dẫn Snake.\n"
    "Bạn có thể hỏi về cách chơi, phím điều khiển, độ khó, điểm số, "
    "bảng xếp hạng... hoặc bấm các gợi ý bên dưới."
)

SUGGESTIONS = [
    "Cách chơi",
    "Phím điều khiển",
    "Độ khó",
    "Táo đặc biệt",
    "Bảng xếp hạng",
    "Mẹo chơi",
]

FALLBACK = (
    "Mình chưa hiểu câu này. Bạn thử hỏi về: cách chơi, phím điều khiển, "
    "tạm dừng, chơi lại, độ khó, đá cản đường, tính điểm, táo đặc biệt, tốc độ, "
    "bảng xếp hạng, giao diện hoặc mẹo chơi nhé!"
)

# (danh sách từ khóa đã bỏ dấu, câu trả lời)
TOPICS = [
    (["xin chao", "chao", "hello", "hi", "alo", "hey"],
     "Chào bạn! Bạn muốn biết điều gì về trò chơi Rắn ăn táo?"),
    (["cam on", "thanks", "thank", "cảm ơn"],
     "Không có gì! Chúc bạn chơi vui và leo lên top bảng xếp hạng nhé!"),
    (["ban la ai", "ten gi", "bot", "tro ly"],
     "Mình là trợ lý hướng dẫn chơi Snake, trả lời bằng các câu có sẵn "
     "nên chỉ biết những gì liên quan đến trò chơi này thôi."),
    (["cach choi", "huong dan", "choi nhu the nao", "choi the nao", "muc tieu",
      "bat dau", "luat", "luat choi", "lam sao choi", "choi sao", "choi lam the nao",
      "choi ra sao", "choi nhu nao", "choi kieu gi", "choi the nao", "huong dan choi", "gioi thieu"],
     "MỤC TIÊU: điều khiển rắn ăn táo đỏ, mỗi quả +10 điểm và rắn dài thêm 1 ô.\n"
     "Đụng tường, thân mình hoặc đá thì thua. Ăn kín bàn là chiến thắng.\n"
     "Bấm 'Chơi game', nhập tên rồi chơi sau khi đếm ngược 3-2-1."),
    (["phim", "dieu khien", "di chuyen", "bam", "wasd", "mui ten", "dieu huong",
      "doi huong"],
     "Đổi hướng: mũi tên hoặc W A S D.\n"
     "Tạm dừng: E, Space hoặc P (hoặc nút 'Tạm dừng'). Khi tạm dừng bấm Q để thoát, điểm vẫn được lưu.\n"
     "Phóng to / thu nhỏ: phím + / -, Ctrl + lăn chuột, hoặc nút phóng to / kéo cạnh cửa sổ (bàn chơi tự co giãn theo).\n"
     "Chơi lại: R. Về menu: Esc.\n"
     "Mỗi lần chỉ nhận một lần đổi hướng giữa hai bước đi."),
    (["tam dung", "pause", "space", "dung lai", "dung game"],
     "Bấm E (hoặc Space, P, hoặc nút 'Tạm dừng') để dừng, bấm lại hoặc nút 'Tiếp tục' để chơi tiếp. "
     "Khi đang tạm dừng, bấm Q hoặc nút 'Thoát' để ra menu và vẫn lưu điểm."),
    (["choi lai", "restart", "lai tu dau", "phim r", "reset"],
     "Bấm phím R để chơi lại ngay (có đếm ngược 3-2-1). Khi thua cũng có nút "
     "'Chơi lại' để bấm bằng chuột."),
    (["thoat", "escape", "esc", "menu", "quay ve"],
     "Esc: về menu (đang ở menu thì thoát game). Ván đang chơi dở mà thoát bằng Esc thì không lưu điểm (muốn lưu hãy tạm dừng rồi bấm Q)."),
    (["quay nguoc", "di nguoc", "180", "dao chieu"],
     "Rắn không được quay ngược 180 độ. Ví dụ đang đi sang phải thì bấm trái "
     "sẽ không có tác dụng."),
    (["diem", "score", "tinh diem", "bao nhieu diem", "cong diem"],
     "Mỗi táo đỏ +10 điểm (táo vàng +30, táo độc -10). Điểm hiện ở góc trên bên phải, bên cạnh là kỷ lục "
     "'Best' của độ khó bạn đang chơi."),
    (["toc do", "nhanh", "cham", "tang toc", "nhanh dan"],
     "Rắn bắt đầu chạy chậm. 5 quả táo đầu tốc độ giữ nguyên, từ quả thứ 6 "
     "mỗi quả táo làm rắn chạy NHANH HƠN một chút, tối đa khoảng 12 bước/giây. "
     "Tốc độ lúc đầu: Dễ ~4 bước/giây, Vừa ~4,5 bước/giây, Khó ~5,5 bước/giây."),
    (["do kho", "de", "vua", "kho", "muc do", "cap do", "che do"],
     "3 độ khó (chọn ở menu):\n"
     "- Dễ: rắn chậm, hợp để làm quen, có combo, nhiệm vụ và 2-3 táo đặc biệt cùng lúc.\n"
     "- Vừa: không đá, nhưng có cổng dịch chuyển, ô băng, vũng bùn, combo, hai táo chọn một và nhiệm vụ nhanh.\n"
     "- Khó: nhanh hơn, 6 đá sẵn, đá mọc dần, có táo đá, táo bom, combo, hai táo chọn một và nhiệm vụ nhanh.\n"
     "Mỗi độ khó có bảng xếp hạng riêng."),
    (["combo", "lien tiep", "nhan diem", "x1 5", "nhan doi"],
     "COMBO (cả 3 mức): ăn táo đỏ liên tiếp, mỗi quả cách nhau chưa tới 6 giây thì "
     "táo kế được x1,5 rồi x2 điểm. Để quá 6 giây là combo mất. Góc trên bàn chơi có đồng hồ combo."),
    (["hai tao", "2 tao", "tao doi", "chon mot", "hai qua"],
     "Mức Vừa và Khó luôn có HAI táo đỏ nằm xa nhau (thường ở hai hướng khác nhau). "
     "Ăn một quả thì quả còn lại biến mất, rồi cả hai được sinh lại. Hãy chọn quả an toàn hơn."),
    (["bang", "o bang", "truot", "trượt", "trơn", "tron"],
     "Ô BĂNG (xanh nhạt, mức Vừa): bước vào thì rắn trượt thêm 1 ô theo hướng đang đi. "
     "Không thua, nhưng dễ lỡ nhịp nếu ngay sau đó có táo hoặc cần rẽ."),
    (["bun", "vung bun", "o bun", "tru diem", "mat diem", "bi tru"],
     "VŨNG BÙN (màu nâu, mức Vừa): bước vào bị trừ 30 điểm (điểm không xuống dưới 0). "
     "Vũng đó biến mất và một vũng mới mọc ở chỗ khác. Ngoài ra cứ 15 giây toàn bộ bùn đổi chỗ "
     "(bùn nhấp nháy 3 giây trước khi đổi), nên hãy nhìn trước đường đi."),
    (["nhiem vu", "thuong", "bonus", "thu thach"],
     "NHIỆM VỤ NHANH (cả 3 mức): thỉnh thoảng hiện yêu cầu như 'ăn 3 táo trong 15 giây' "
     "(phía trên bàn chơi). Mỗi ván chỉ có 2 nhiệm vụ. Xong được thưởng +30 / +50 / +80 điểm, hết giờ mà chưa xong thì bị trừ 20 điểm (điểm không xuống dưới 0)."),
    (["da", "vat can", "chuong ngai", "tang da", "hon da", "da moc", "moc dan"],
     "Đá chỉ có ở độ khó Khó (Vừa thay đá bằng các cơ chế khác). Đụng đá là thua (trừ khi đang có táo bom). Đá MỌC DẦN theo thời gian "
     "(Khó mọc nhanh hơn Vừa). Muốn phá đá thì ăn TÁO ĐÁ (táo xám có vết nứt): mỗi quả vỡ 1 viên. Đá mới nhấp nháy viền vàng. "
     "Táo không xuất hiện trên đá và đá không nhốt rắn nên luôn có đường đi."),
    (["cong", "cong dich chuyen", "dich chuyen", "teleport", "portal", "xoay"],
     "Mức Vừa có một cặp CỔNG DỊCH CHUYỂN (vòng xoáy tím-xanh). Đầu rắn chui vào cổng này "
     "sẽ ra ở cổng kia và đi tiếp theo hướng cũ; dùng xong cặp cổng đổi sang chỗ khác. Cẩn thận: nếu ô thoát đang có thân rắn thì thua."),
    (["tao dac biet", "dac biet", "tao vang", "tao xanh", "tao tim", "tao doc",
      "tao bom", "bom", "tao cam", "tao da", "tao xam", "x2", "hieu ung", "xanh duong", "tao mau"],
     "Ngoài táo đỏ (+10) còn có táo đặc biệt, chỉ tồn tại một lúc rồi biến mất:\n"
     "- Táo vàng: +30 điểm, chỉ ~8 bước.\n"
     "- Táo xanh: rắn chạy chậm lại 5 giây.\n"
     "- Táo cam: rắn chạy NHANH hơn trong 5 giây.\n"
     "- Táo tím: x2 điểm trong 10 giây.\n"
     "- Táo độc: -10 điểm và ngắn đi 2 đốt, tránh ra!\n"
     "- Táo bom (mức Khó): 10 giây đâm vào đá thì đá nổ, không thua.\n"
     "- Táo đá (xám, có vết nứt): ăn vào tự phá 1 viên đá.\n"
     "Dễ có vàng/xanh/tím/cam, Vừa thêm táo độc, Khó thêm táo độc, táo bom và táo đá.\n"
     "Ở cả 3 mức có thể có 2-3 táo đặc biệt cùng lúc, mỗi táo tự biến mất sau một số bước riêng; "
     "táo độc và táo đá (mức Khó) xuất hiện khá nhiều."),
    (["tao", "an tao", "tao do", "qua tao"],
     "Táo đỏ xuất hiện ngẫu nhiên ở ô trống. Ăn táo +10 điểm, rắn dài thêm 1 ô "
     "và chạy nhanh hơn một chút. Hỏi 'táo đặc biệt' để biết thêm các loại táo khác."),
    (["thua", "chet", "game over", "dung tuong", "dung than", "va cham"],
     "Bạn thua khi đầu rắn đụng tường, thân mình hoặc đá. Lúc đó điểm được lưu "
     "vào bảng xếp hạng và có nút 'Chơi lại' / 'Về menu'."),
    (["thang", "chien thang", "kin ban", "win"],
     "Ăn hết ô trống sao cho rắn lấp kín bàn thì bạn thắng ('CHIẾN THẮNG!'). "
     "Rất khó nên cần chơi thật cẩn thận!"),
    (["xep hang", "bang xep hang", "top", "hang", "luu diem", "ten", "ky luc"],
     "Điểm được lưu khi ván kết thúc. Mỗi độ khó có một bảng top 10 riêng "
     "(bấm tab Dễ / Vừa / Khó hoặc phím ← →). Mỗi tên chỉ giữ điểm cao nhất."),
    (["giao dien", "theme", "mau", "toi", "sang", "dai duong", "rung", "doi mau"],
     "Ở menu bấm nút 'Giao diện' để đổi giữa Rừng (tối), Sáng và Đại dương."),
    (["dem nguoc", "3 2 1", "chuan bi"],
     "Mỗi ván bắt đầu bằng đếm ngược 3-2-1 để bạn kịp chuẩn bị. "
     "Trong lúc đếm bạn đã có thể chọn hướng đi đầu tiên."),
    (["meo", "tip", "tips", "bi quyet", "choi gioi", "loi khuyen", "kinh nghiem", "kinh nghiem", "khong thua"],
     "Mẹo chơi:\n"
     "- Nhìn trước 2-3 ô, đừng đổi hướng liên tục.\n"
     "- Đi dọc theo mép và chừa chỗ quay đầu khi rắn dài.\n"
     "- Chơi mức Dễ trước để làm quen nhịp rồi mới lên Khó.\n"
     "- Dùng Space để tạm dừng và suy nghĩ nước đi."),
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
        return "Bạn hãy gõ câu hỏi nhé, ví dụ: 'Cách chơi?'"

    qwords = set(q.split())
    best_score, best_answer = 0.0, FALLBACK
    for keywords, answer in TOPICS:
        score = _score(q, qwords, keywords)
        if score > best_score:
            best_score, best_answer = score, answer
    return best_answer