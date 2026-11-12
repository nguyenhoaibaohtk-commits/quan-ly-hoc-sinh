import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db

def update_school_classes():
    conn = get_db()
    cursor = conn.cursor()

    # Lấy năm học đang kích hoạt
    cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
    row = cursor.fetchone()
    year_id = row['id'] if row else 1

    # Danh sách 33 lớp theo yêu cầu
    target_classes = []

    # Danh sách tên giáo viên mẫu phong phú cho 33 lớp
    teachers_10 = [
        "Thầy Nguyễn Trọng Hoàng", "Cô Trần Thị Mai", "Thầy Lê Anh Tuấn", "Cô Đặng Thu Hà",
        "Thầy Vũ Đình Long", "Cô Phạm Hồng Nhung", "Thầy Bùi Văn Thắng", "Cô Ngô Phương Thảo",
        "Thầy Đỗ Minh Đức", "Cô Hoàng Yến Nhi", "Thầy Phan Quốc Việt"
    ]
    teachers_11 = [
        "Cô Nguyễn Thị Bích", "Thầy Trần Trung Kiên", "Cô Lê Minh Trang", "Thầy Phạm Đức An",
        "Cô Vũ Hải Vân", "Thầy Đặng Hữu Tài", "Cô Bùi Kim Ngân", "Thầy Ngô Thành Nam",
        "Cô Đỗ Thúy Hằng", "Thầy Hoàng Tuấn Tú", "Cô Phan Mai Anh"
    ]
    teachers_12 = [
        "Thầy Nguyễn Hữu Phước", "Cô Trần Lan Anh", "Thầy Lê Xuân Bách", "Cô Đặng Mỹ Dung",
        "Thầy Vũ Quang Huy", "Cô Phạm Quỳnh Chi", "Thầy Bùi Đức Thịnh", "Cô Ngô Diệu Linh",
        "Thầy Đỗ Khắc Cường", "Cô Hoàng Thục Anh", "Thầy Phan Thế Hiển"
    ]

    # Khối 10: 10A1 -> 10A11
    for i in range(1, 12):
        name = f"10A{i}"
        room = f"Phòng 10{i}" if i < 10 else f"Phòng 1{i}"
        teacher = teachers_10[i - 1]
        target_classes.append((name, 10, year_id, teacher, room))

    # Khối 11: 11B1 -> 11B11
    for i in range(1, 12):
        name = f"11B{i}"
        room = f"Phòng 20{i}" if i < 10 else f"Phòng 2{i}"
        teacher = teachers_11[i - 1]
        target_classes.append((name, 11, year_id, teacher, room))

    # Khối 12: 12C1 -> 12C11
    for i in range(1, 12):
        name = f"12C{i}"
        room = f"Phòng 30{i}" if i < 10 else f"Phòng 3{i}"
        teacher = teachers_12[i - 1]
        target_classes.append((name, 12, year_id, teacher, room))

    # Lấy ID của lớp 10A1 để nếu có học sinh ở các lớp cũ (như 11A1, 12A1) thì chuyển sang 10A1
    cursor.execute("SELECT id FROM classes WHERE name = '10A1' AND academic_year_id = ?", (year_id,))
    c_10a1 = cursor.fetchone()
    id_10a1 = c_10a1['id'] if c_10a1 else 1

    # Xóa các lớp cũ không nằm trong danh sách (11A1, 11A2, 12A1, 12A2...)
    target_names = [c[0] for c in target_classes]
    placeholders = ','.join('?' for _ in target_names)
    cursor.execute(f"SELECT id, name FROM classes WHERE name NOT IN ({placeholders}) AND academic_year_id = ?", (*target_names, year_id))
    old_classes = cursor.fetchall()

    for old in old_classes:
        cursor.execute("UPDATE students SET class_id = ? WHERE class_id = ?", (id_10a1, old['id']))
        cursor.execute("DELETE FROM classes WHERE id = ?", (old['id'],))

    # Thêm hoặc cập nhật từng lớp
    for name, grade, y_id, teacher, room in target_classes:
        cursor.execute("SELECT id FROM classes WHERE name = ? AND academic_year_id = ?", (name, y_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE classes SET grade_level = ?, room = ? WHERE id = ?", (grade, room, existing['id']))
        else:
            cursor.execute("INSERT INTO classes (name, grade_level, academic_year_id, teacher_name, room) VALUES (?, ?, ?, ?, ?)",
                           (name, grade, y_id, teacher, room))

    conn.commit()

    # Kiểm tra kết quả
    cursor.execute("SELECT grade_level, COUNT(*) as cnt FROM classes WHERE academic_year_id = ? GROUP BY grade_level ORDER BY grade_level", (year_id,))
    counts = cursor.fetchall()
    print("=== KẾT QUẢ CẬP NHẬT LỚP HỌC ===")
    for c in counts:
        print(f"Khối {c['grade_level']}: {c['cnt']} lớp")

    cursor.execute("SELECT name FROM classes WHERE academic_year_id = ? ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC", (year_id,))
    all_names = [r['name'] for r in cursor.fetchall()]
    print(f"Tổng số lớp: {len(all_names)} lớp")
    print("Danh sách lớp:")
    print("Khối 10:", ", ".join([n for n in all_names if n.startswith("10A")]))
    print("Khối 11:", ", ".join([n for n in all_names if n.startswith("11B")]))
    print("Khối 12:", ", ".join([n for n in all_names if n.startswith("12C")]))

    conn.close()

if __name__ == '__main__':
    update_school_classes()
