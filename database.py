import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'school.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Bảng Cài đặt hệ thống
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    # Bảng Năm học
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS academic_years (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        is_active INTEGER DEFAULT 0
    )
    ''')

    # Bảng Lớp học
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        grade_level INTEGER NOT NULL,
        academic_year_id INTEGER NOT NULL,
        teacher_name TEXT,
        room TEXT,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
        UNIQUE(name, academic_year_id)
    )
    ''')

    # Bảng Môn học
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'Tự nhiên',
        coefficient INTEGER DEFAULT 1,
        periods INTEGER DEFAULT 70
    )
    ''')

    # Bảng Học sinh
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_code TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        date_of_birth TEXT,
        gender TEXT CHECK(gender IN ('Nam', 'Nữ')),
        address TEXT,
        phone TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        email TEXT,
        status TEXT DEFAULT 'Đang học',
        class_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
    )
    ''')

    # Bảng Điểm số
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        semester INTEGER NOT NULL CHECK(semester IN (1, 2)),
        academic_year_id INTEGER NOT NULL,
        tx1 REAL,
        tx2 REAL,
        tx3 REAL,
        tx4 REAL,
        gk REAL,
        ck REAL,
        average REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
        UNIQUE(student_id, subject_id, semester, academic_year_id)
    )
    ''')

    # Bảng Điểm danh
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('P', 'CP', 'KP', 'T')),
        note TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        UNIQUE(student_id, date)
    )
    ''')

    # Bảng Đánh giá & Rèn luyện tổng hợp
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conducts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        semester INTEGER NOT NULL CHECK(semester IN (1, 2)),
        academic_year_id INTEGER NOT NULL,
        academic_rank TEXT,
        conduct_rank TEXT DEFAULT 'Tốt',
        reward_discipline TEXT,
        notes TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
        UNIQUE(student_id, semester, academic_year_id)
    )
    ''')

    # Bảng Sổ Đầu Bài & Chấm điểm tiết học từng lớp (Thứ 2 đến Thứ 7)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lesson_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        academic_year_id INTEGER NOT NULL,
        semester INTEGER NOT NULL CHECK(semester IN (1, 2)),
        week_number INTEGER NOT NULL,
        date TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        period INTEGER NOT NULL CHECK(period BETWEEN 1 AND 5),
        subject_id INTEGER,
        teacher_name TEXT,
        lesson_name TEXT,
        absent_students TEXT,
        score REAL CHECK(score >= 0 AND score <= 10),
        classification TEXT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
        UNIQUE(class_id, date, period)
    )
    ''')

    conn.commit()
    conn.close()

def seed_sample_data():
    conn = get_db()
    cursor = conn.cursor()

    # Kiểm tra xem đã có dữ liệu chưa
    cursor.execute("SELECT COUNT(*) as count FROM settings")
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return

    # 1. Cài đặt mặc định
    default_settings = [
        ('school_name', 'Trường THPT Chu Văn An'),
        ('school_address', 'Số 10 Thụy Khuê, Tây Hồ, Hà Nội'),
        ('school_phone', '024 3823 3164'),
        ('school_email', 'c3chuvanan@hanoi.edu.vn'),
        ('principal_name', 'TS. Nguyễn Văn Hùng'),
        ('current_academic_year', '2026-2027'),
        ('current_semester', '1'),
        ('grade_system', 'TT22') # Chuẩn Thông tư 22 (Tốt, Khá, Đạt, Chưa đạt)
    ]
    cursor.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", default_settings)

    # 2. Năm học
    years = [('2025-2026', 0), ('2026-2027', 1), ('2027-2028', 0)]
    cursor.executemany("INSERT INTO academic_years (name, is_active) VALUES (?, ?)", years)
    cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
    curr_year_id = cursor.fetchone()['id']

    # 3. Danh sách 33 lớp học (Khối 10: 10A1-10A11, Khối 11: 11B1-11B11, Khối 12: 12C1-12C11)
    classes = []
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

    for i in range(1, 12):
        classes.append((f'10A{i}', 10, curr_year_id, teachers_10[i - 1], f'Phòng 10{i}' if i < 10 else f'Phòng 1{i}'))
    for i in range(1, 12):
        classes.append((f'11B{i}', 11, curr_year_id, teachers_11[i - 1], f'Phòng 20{i}' if i < 10 else f'Phòng 2{i}'))
    for i in range(1, 12):
        classes.append((f'12C{i}', 12, curr_year_id, teachers_12[i - 1], f'Phòng 30{i}' if i < 10 else f'Phòng 3{i}'))

    cursor.executemany("INSERT INTO classes (name, grade_level, academic_year_id, teacher_name, room) VALUES (?, ?, ?, ?, ?)", classes)

    # 4. Danh mục môn học chuẩn THPT
    subjects = [
        ('TOAN', 'Toán học', 'Khoa học tự nhiên', 1, 105),
        ('VAN', 'Ngữ văn', 'Khoa học xã hội', 1, 105),
        ('ANH', 'Tiếng Anh', 'Ngoại ngữ', 1, 105),
        ('LY', 'Vật lí', 'Khoa học tự nhiên', 1, 70),
        ('HOA', 'Hóa học', 'Khoa học tự nhiên', 1, 70),
        ('SINH', 'Sinh học', 'Khoa học tự nhiên', 1, 70),
        ('SU', 'Lịch sử', 'Khoa học xã hội', 1, 52),
        ('DIA', 'Địa lí', 'Khoa học xã hội', 1, 52),
        ('TIN', 'Tin học', 'Công nghệ', 1, 35),
        ('GDCD', 'GDKT & PL', 'Khoa học xã hội', 1, 35),
        ('GDTC', 'Giáo dục thể chất', 'Thể chất & Nghệ thuật', 1, 70),
        ('QPAN', 'GD Quốc phòng & An ninh', 'Khác', 1, 35)
    ]
    cursor.executemany("INSERT INTO subjects (code, name, category, coefficient, periods) VALUES (?, ?, ?, ?, ?)", subjects)

    # Lấy class 10A1 id
    cursor.execute("SELECT id FROM classes WHERE name = '10A1' AND academic_year_id = ?", (curr_year_id,))
    class_10a1_id = cursor.fetchone()['id']

    # 5. Danh sách học sinh mẫu cho lớp 10A1
    sample_students = [
        ('HS26001', 'Nguyễn Minh Anh', '2011-03-15', 'Nữ', '15 Hoàng Hoa Thám, Ba Đình, HN', '0912345601', 'Nguyễn Văn Minh', '0988111221', '10a1.minhanh@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26002', 'Trần Hoàng Bảo', '2011-08-20', 'Nam', '42 Đội Cấn, Ba Đình, HN', '0912345602', 'Trần Hoàng Dũng', '0988111222', '10a1.bao@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26003', 'Lê Khánh Chi', '2011-01-10', 'Nữ', '88 Thụy Khuê, Tây Hồ, HN', '0912345603', 'Lê Khắc Chung', '0988111223', '10a1.chi@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26004', 'Phạm Quốc Đạt', '2011-05-25', 'Nam', '105 Lạc Long Quân, Tây Hồ, HN', '0912345604', 'Phạm Văn Nam', '0988111224', '10a1.dat@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26005', 'Vũ Thị Hải Yến', '2011-11-02', 'Nữ', '22 Kim Mã, Ba Đình, HN', '0912345605', 'Vũ Đình Hải', '0988111225', '10a1.yen@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26006', 'Đỗ Quang Huy', '2011-09-18', 'Nam', '67 Quán Thánh, Ba Đình, HN', '0912345606', 'Đỗ Quang Minh', '0988111226', '10a1.huy@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26007', 'Bùi Ngọc Lan', '2011-04-30', 'Nữ', '12 Nguyễn Thái Học, Ba Đình, HN', '0912345607', 'Bùi Văn Tiến', '0988111227', '10a1.lan@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26008', 'Hoàng Tuấn Kiệt', '2011-07-12', 'Nam', '55 Phan Đình Phùng, Ba Đình, HN', '0912345608', 'Hoàng Văn Khiêm', '0988111228', '10a1.kiet@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26009', 'Đặng Thảo Linh', '2011-12-05', 'Nữ', '33 Yên Phụ, Tây Hồ, HN', '0912345609', 'Đặng Quốc Hưng', '0988111229', '10a1.linh@school.edu.vn', 'Đang học', class_10a1_id),
        ('HS26010', 'Ngô Gia Phong', '2011-02-28', 'Nam', '91 Văn Cao, Ba Đình, HN', '0912345610', 'Ngô Gia Thịnh', '0988111230', '10a1.phong@school.edu.vn', 'Đang học', class_10a1_id)
    ]
    cursor.executemany('''
    INSERT INTO students (student_code, full_name, date_of_birth, gender, address, phone, parent_name, parent_phone, email, status, class_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_students)

    # 6. Điểm mẫu cho một số môn học
    cursor.execute("SELECT id FROM subjects WHERE code IN ('TOAN', 'VAN', 'ANH', 'HOA')")
    sample_subjs = [row['id'] for row in cursor.fetchall()]

    cursor.execute("SELECT id FROM students WHERE class_id = ?", (class_10a1_id,))
    st_ids = [row['id'] for row in cursor.fetchall()]

    sample_grade_data = [
        # (tx1, tx2, tx3, tx4, gk, ck)
        (8.5, 9.0, 8.0, 9.5, 8.5, 9.0),
        (7.0, 7.5, 8.0, 7.0, 7.5, 8.0),
        (9.0, 9.5, 9.0, 10.0, 9.5, 9.5),
        (6.0, 6.5, 7.0, None, 6.5, 7.0),
        (8.0, 8.5, 8.0, 9.0, 8.5, 8.5),
        (7.5, 8.0, 7.5, 8.0, 8.0, 8.5),
        (9.5, 9.0, 9.5, 9.0, 9.0, 9.5),
        (5.5, 6.0, 6.5, 6.0, 6.0, 6.5),
        (8.0, 8.0, 8.5, 9.0, 8.5, 9.0),
        (7.0, 7.0, 7.5, 8.0, 7.5, 8.0)
    ]

    for s_idx, st_id in enumerate(st_ids):
        for sub_id in sample_subjs:
            g = sample_grade_data[(s_idx + sub_id) % len(sample_grade_data)]
            tx_vals = [x for x in [g[0], g[1], g[2], g[3]] if x is not None]
            cnt = len(tx_vals)
            gk_val = g[4] if g[4] is not None else 0
            ck_val = g[5] if g[5] is not None else 0
            avg = round((sum(tx_vals) + gk_val * 2 + ck_val * 3) / (cnt + 2 + 3), 1)

            cursor.execute('''
            INSERT INTO grades (student_id, subject_id, semester, academic_year_id, tx1, tx2, tx3, tx4, gk, ck, average)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (st_id, sub_id, 1, curr_year_id, g[0], g[1], g[2], g[3], g[4], g[5], avg))

    # 7. Dữ liệu điểm danh mẫu cho ngày hôm nay và hôm qua
    today_str = date.today().isoformat()
    for idx, st_id in enumerate(st_ids):
        status = 'P'
        if idx == 3:
            status = 'CP' # Có phép
        elif idx == 7:
            status = 'KP' # Không phép
        elif idx == 5:
            status = 'T'  # Trễ
        cursor.execute('''
        INSERT OR REPLACE INTO attendance (student_id, class_id, date, status, note)
        VALUES (?, ?, ?, ?, ?)
        ''', (st_id, class_10a1_id, today_str, status, 'Mẫu điểm danh tự động'))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_sample_data()
    print("Khởi tạo cơ sở dữ liệu và nạp dữ liệu mẫu thành công!")
