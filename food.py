from random import Random
from models import Position


def spawn_apple(cols: int, rows: int, occupied: set[Position], rng: Random) -> Position | None:
    """IN: kích thước dương; occupied gồm các ô trong bàn; rng được truyền từ engine.
    OUT: một ô trống chọn đều; None khi kín bàn. Không sửa occupied.
    Sai kích thước/ô ngoài bàn: ValueError.
    Duyệt theo y rồi x để lập danh sách ô trống và dùng rng.choice.
    Chi phí O(cols*rows), tránh thử ngẫu nhiên lặp vô hạn khi bàn gần kín.
    """
 
    #1: KIỂM TRA TÍNH HỢP LỆ CỦA KÍCH THƯỚC BÀN CỜ (cols, rows)

    if not isinstance(cols, int) or isinstance(cols, bool):
        raise ValueError("Số cột (cols) phải là một số nguyên.")
    if not isinstance(rows, int) or isinstance(rows, bool):
        raise ValueError("Số hàng (rows) phải là một số nguyên.")

    if cols <= 0:
        raise ValueError(f"Số cột (cols) phải là số nguyên dương lớn hơn 0 (nhận được: {cols}).")
    if rows <= 0:
        raise ValueError(f"Số hàng (rows) phải là số nguyên dương lớn hơn 0 (nhận được: {rows}).")


    #2: KIỂM TRA ĐỐI TƯỢNG occupied VÀ BỘ SINH SỐ NGẪU NHIÊN rng
 
    if occupied is None or not isinstance(occupied, set):
        raise ValueError("Tham số occupied phải là một tập hợp (set) chứa các tọa độ.")

    if rng is None or not isinstance(rng, Random):
        raise ValueError("Tham số rng phải là một đối tượng thuộc lớp random.Random.")


    #3: KIỂM TRA TỪNG Ô TRONG TẬP HỢP occupied

    for cell in occupied:
        # Kiểm tra cấu trúc tuple gồm đúng 2 phần tử
        if not isinstance(cell, tuple) or len(cell) != 2:
            raise ValueError(f"Ô {cell} trong occupied không hợp lệ. Mỗi ô phải là tuple (x, y).")

        x, y = cell

        # Kiểm tra tọa độ x và y phải là số nguyên
        if not isinstance(x, int) or isinstance(x, bool):
            raise ValueError(f"Hoành độ x={x} của ô {cell} phải là số nguyên.")
        if not isinstance(y, int) or isinstance(y, bool):
            raise ValueError(f"Tung độ y={y} của ô {cell} phải là số nguyên.")

        # Kiểm tra tọa độ (x, y) có nằm trong phạm vi bàn cờ hay không:
        # Hoành độ x hợp lệ: từ 0 đến cols - 1
        # Tung độ y hợp lệ: từ 0 đến rows - 1
        if x < 0 or x >= cols:
            raise ValueError(
                f"Ô ({x}, {y}) có hoành độ x={x} nằm ngoài phạm vi bàn cờ (0 <= x < {cols})."
            )
        if y < 0 or y >= rows:
            raise ValueError(
                f"Ô ({x}, {y}) có tung độ y={y} nằm ngoài phạm vi bàn cờ (0 <= y < {rows})."
            )


    # 4: DUYỆT BÀN CỜ THEO THỨ TỰ y RỒI x ĐỂ LẬP DANH SÁCH Ô TRỐNG

    empty_cells: list[Position] = []

    for y in range(rows):
        for x in range(cols):
            current_cell: Position = (x, y)
            if current_cell not in occupied:    # Kiểm tra xem ô hiện tại có nằm trong tập các ô bị thân rắn chiếm hay không.
               empty_cells.append(current_cell)



    #5: XỬ LÝ TRƯỜNG HỢP BÀN ĐÃ KÍN HOẶC CHỌN Ô TRỐNG NGẪU NHIÊN

    # Nếu danh sách ô trống rỗng (tức là rắn đã chiếm hết mọi ô trên bàn cờ)
    if len(empty_cells) == 0:
        return None

    # Chọn ngẫu nhiên đồng đều (uniformly) 1 ô trống từ danh sách bằng đối tượng rng
    selected_apple_position: Position = rng.choice(empty_cells)

    return selected_apple_position



# Ghi chú : 
# isinstance() là một hàm có sẵn trong Python, dùng để kiểm tra xem một đối tượng (object) có phải là thể hiện (instance) của một lớp cụ thể hay của một lớp cha (superclass) nào đó hay không.
# Cú pháp : isinstance(object, classinfo). 
# Hàm trả về kết quả True: Nếu đối tượng thuộc kiểu dữ liệu (hoặc class) được chỉ định và False: Nếu không phải.
