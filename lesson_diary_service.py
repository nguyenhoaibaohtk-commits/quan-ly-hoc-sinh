from datetime import datetime, date, timedelta
from database import get_db

DAY_NAMES = [
    ('Thứ Hai', 0),
    ('Thứ Ba', 1),
    ('Thứ Tư', 2),
    ('Thứ Năm', 3),
    ('Thứ Sáu', 4),
    ('Thứ Bảy', 5)
]

def classify_score(score):
    """Xếp loại tiết học theo thang điểm 10"""
    if score is None:
        return None
    try:
        val = float(score)
        if val >= 9.0:
            return 'Tốt'
        elif val >= 7.0:
            return 'Khá'
        elif val >= 5.0:
            return 'Trung bình'
        else:
            return 'Yếu'
    except (ValueError, TypeError):
        return None

def get_week_dates(base_date=None):
    """
    Lấy danh sách 6 ngày từ Thứ Hai đến Thứ Bảy của tuần chứa base_date.
    Nếu base_date không truyền, lấy ngày hôm nay.
    """
    if base_date is None:
        target_dt = date.today()
    elif isinstance(base_date, str):
        target_dt = datetime.strptime(base_date, '%Y-%m-%d').date()
    else:
        target_dt = base_date

    # target_dt.weekday(): Thứ Hai là 0, Chủ Nhật là 6
    # Nếu rơi vào Chủ Nhật (6), lùi về tuần đó (lùi 6 ngày về Thứ Hai)
    start_monday = target_dt - timedelta(days=target_dt.weekday())

    week_days = []
    for day_name, offset in DAY_NAMES:
        d = start_monday + timedelta(days=offset)
        week_days.append({
            'day_name': day_name,
            'date': d.isoformat(),
            'formatted_date': d.strftime('%d/%m/%Y')
        })
    return week_days

def get_class_diary(class_id, week_number=1, semester=1, academic_year_id=None, base_date=None):
    """
    Lấy toàn bộ sổ đầu bài từ Thứ 2 đến Thứ 7 của 1 lớp trong 1 tuần
    """
    conn = get_db()
    cursor = conn.cursor()

    if not academic_year_id:
        cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
        row = cursor.fetchone()
        academic_year_id = row['id'] if row else 1

    cursor.execute('''
    SELECT c.*, y.name as year_name
    FROM classes c
    JOIN academic_years y ON c.academic_year_id = y.id
    WHERE c.id = ?
    ''', (class_id,))
    classroom = cursor.fetchone()

    week_days = get_week_dates(base_date)
    week_start = week_days[0]['date']
    week_end = week_days[-1]['date']

    cursor.execute('''
    SELECT lr.*, s.name as subject_name, s.code as subject_code
    FROM lesson_records lr
    LEFT JOIN subjects s ON lr.subject_id = s.id
    WHERE lr.class_id = ? AND lr.date BETWEEN ? AND ?
    ORDER BY lr.date ASC, lr.period ASC
    ''', (class_id, week_start, week_end))
    records = cursor.fetchall()

    # Tổ chức theo bảng: {date_str: {period: record}}
    grid = {}
    for wd in week_days:
        grid[wd['date']] = {}
        for p in range(1, 6):
            grid[wd['date']][p] = None

    total_score = 0.0
    scored_periods = 0
    count_tot = 0
    count_kha = 0
    count_tb = 0
    count_yeu = 0

    for r in records:
        d_str = r['date']
        p = r['period']
        if d_str in grid:
            grid[d_str][p] = r
        if r['score'] is not None:
            total_score += float(r['score'])
            scored_periods += 1
            cls = r['classification']
            if cls == 'Tốt':
                count_tot += 1
            elif cls == 'Khá':
                count_kha += 1
            elif cls == 'Trung bình':
                count_tb += 1
            elif cls == 'Yếu':
                count_yeu += 1

    avg_score = round(total_score / scored_periods, 2) if scored_periods > 0 else 0.0

    conn.close()

    return {
        'classroom': classroom,
        'week_days': week_days,
        'grid': grid,
        'summary': {
            'total_score': round(total_score, 1),
            'scored_periods': scored_periods,
            'avg_score': avg_score,
            'count_tot': count_tot,
            'count_kha': count_kha,
            'count_tb': count_tb,
            'count_yeu': count_yeu
        }
    }

def save_lesson_record(class_id, academic_year_id, semester, week_number, date_str, day_of_week, period, subject_id, teacher_name, lesson_name, absent_students, score, note):
    """Lưu hoặc cập nhật một tiết học trong sổ đầu bài"""
    classification = classify_score(score)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO lesson_records (
        class_id, academic_year_id, semester, week_number, date, day_of_week,
        period, subject_id, teacher_name, lesson_name, absent_students, score, classification, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(class_id, date, period) DO UPDATE SET
        academic_year_id = excluded.academic_year_id,
        semester = excluded.semester,
        week_number = excluded.week_number,
        day_of_week = excluded.day_of_week,
        subject_id = excluded.subject_id,
        teacher_name = excluded.teacher_name,
        lesson_name = excluded.lesson_name,
        absent_students = excluded.absent_students,
        score = excluded.score,
        classification = excluded.classification,
        note = excluded.note
    ''', (class_id, academic_year_id, semester, week_number, date_str, day_of_week, period, subject_id, teacher_name, lesson_name, absent_students, score, classification, note))

    conn.commit()
    conn.close()

def get_weekly_ranking(week_start_date=None, academic_year_id=None):
    """
    Tính bảng xếp hạng thi đua nề nếp sổ đầu bài giữa 33 lớp trong tuần
    """
    week_days = get_week_dates(week_start_date)
    week_start = week_days[0]['date']
    week_end = week_days[-1]['date']

    conn = get_db()
    cursor = conn.cursor()

    if not academic_year_id:
        cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
        row = cursor.fetchone()
        academic_year_id = row['id'] if row else 1

    cursor.execute('''
    SELECT c.id, c.name, c.grade_level, c.teacher_name,
           COUNT(lr.id) as total_recorded,
           SUM(lr.score) as total_score,
           AVG(lr.score) as avg_score,
           COUNT(CASE WHEN lr.classification = 'Tốt' THEN 1 END) as count_tot,
           COUNT(CASE WHEN lr.classification = 'Khá' THEN 1 END) as count_kha,
           COUNT(CASE WHEN lr.classification = 'Trung bình' THEN 1 END) as count_tb,
           COUNT(CASE WHEN lr.classification = 'Yếu' THEN 1 END) as count_yeu
    FROM classes c
    LEFT JOIN lesson_records lr ON lr.class_id = c.id AND lr.date BETWEEN ? AND ?
    WHERE c.academic_year_id = ?
    GROUP BY c.id
    ORDER BY avg_score DESC NULLS LAST, total_score DESC NULLS LAST, c.grade_level ASC, LENGTH(c.name) ASC, c.name ASC
    ''', (week_start, week_end, academic_year_id))
    results = cursor.fetchall()
    conn.close()

    ranking_list = []
    for rank, r in enumerate(results, 1):
        item = dict(r)
        item['rank'] = rank
        item['avg_score'] = round(item['avg_score'], 2) if item['avg_score'] is not None else 0.0
        item['total_score'] = round(item['total_score'], 1) if item['total_score'] is not None else 0.0
        ranking_list.append(item)

    return {
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_end,
        'ranking': ranking_list
    }

def seed_sample_diary():
    """Tạo dữ liệu mẫu điểm số đầu bài cho các lớp trong tuần hiện tại"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM lesson_records")
    if cursor.fetchone()['cnt'] > 0:
        conn.close()
        return

    cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
    year_row = cursor.fetchone()
    year_id = year_row['id'] if year_row else 1

    cursor.execute("SELECT id, name, grade_level, teacher_name FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, name FROM subjects")
    subjects = cursor.fetchall()
    sub_map = {s['name']: s['id'] for s in subjects}

    week_days = get_week_dates()

    # Mẫu lịch học chuẩn THPT từ Thứ 2 đến Thứ 7 (mỗi ngày 5 tiết)
    sample_timetable = [
        # Thứ Hai
        [
            ('Toán học', 'Chào cờ & Đại số: Hàm số lượng giác', 10.0, 'Cả lớp chuẩn bị bài tốt, nghiêm túc'),
            ('Toán học', 'Luyện tập phương trình lượng giác', 9.5, 'Sôi nổi, nhiều em lên bảng làm đúng'),
            ('Ngữ văn', 'Tác phẩm văn học hiện đại', 9.0, 'Phát biểu tốt'),
            ('Tiếng Anh', 'Unit 1: Reading comprehension', 9.5, 'Tương tác sôi nổi'),
            ('Vật lí', 'Chuyển động thẳng biến đổi đều', 8.5, 'Còn 1 em quên mang sách bài tập')
        ],
        # Thứ Ba
        [
            ('Hóa học', 'Liên kết hóa học & Bảng tuần hoàn', 10.0, 'Tiết học sôi nổi, hiểu bài nhanh'),
            ('Hóa học', 'Thí nghiệm thực hành hóa học', 10.0, 'Thực hiện an toàn, ghi chép đầy đủ'),
            ('Lịch sử', 'Cách mạng công nghiệp thế kỷ XVIII', 9.0, 'Tập trung chú ý nghe giảng'),
            ('Sinh học', 'Cấu trúc và chức năng của tế bào', 9.5, 'Trả lời câu hỏi tốt'),
            ('Tin học', 'Thực hành lập trình Python', 9.0, 'Làm bài tập đầy đủ trên máy')
        ],
        # Thứ Tư
        [
            ('Ngữ văn', 'Nghị luận xã hội & Đọc hiểu văn bản', 9.5, 'Nhiều bài viết khá sâu sắc'),
            ('Ngữ văn', 'Rèn luyện kỹ năng viết đoạn văn', 9.0, 'Chăm chỉ làm bài'),
            ('Toán học', 'Hình học không gian: Góc và khoảng cách', 8.0, 'Một vài em chưa nắm vững công thức'),
            ('Tiếng Anh', 'Listening & Speaking practice', 9.0, 'Phát âm tiến bộ'),
            ('Giáo dục thể chất', 'Chạy cự ly ngắn & Thể dục nhịp điệu', 10.0, 'Tác phong nhanh nhẹn, đầy đủ đồng phục')
        ],
        # Thứ Năm
        [
            ('Vật lí', 'Định luật Newton & Lực ma sát', 9.5, 'Làm bài tập tốt'),
            ('Địa lí', 'Địa lý tự nhiên và khí hậu Việt Nam', 9.0, 'Đọc Atlat địa lý tốt'),
            ('GDKT & PL', 'Pháp luật và đời sống công dân', 9.5, 'Thảo luận nhóm tích cực'),
            ('Tiếng Anh', 'Grammar review & Unit test', 8.5, 'Điểm kiểm tra đồng đều'),
            ('GD Quốc phòng & An ninh', 'Đội ngũ từng người không có súng', 10.0, 'Nghiêm túc, đúng điều lệnh')
        ],
        # Thứ Sáu
        [
            ('Toán học', 'Kiểm tra 15 phút & Sửa bài', 9.0, 'Lớp nghiêm túc làm bài'),
            ('Hóa học', 'Phản ứng oxy hóa khử', 9.5, 'Cân bằng phương trình tốt'),
            ('Lịch sử', 'Lịch sử Việt Nam thời cận đại', 8.5, 'Còn 2 em nói chuyện riêng'),
            ('Sinh học', 'Trao đổi chất và năng lượng', 9.0, 'Hiểu bài'),
            ('Ngữ văn', 'Trả bài kiểm tra văn số 1', 9.5, 'Đánh giá chung tốt')
        ],
        # Thứ Bảy
        [
            ('Tiếng Anh', 'Speaking & Presentation skills', 9.5, 'Thuyết trình tự tin bằng tiếng Anh'),
            ('Tin học', 'Cấu trúc rẽ nhánh và vòng lặp', 9.0, 'Chạy chương trình tốt'),
            ('Vật lí', 'Bài tập tổng hợp động lực học', 8.5, 'Tập trung làm bài'),
            ('Giáo dục thể chất', 'Bóng chuyền & Cầu lông', 10.0, 'Tinh thần thể thao rất tốt'),
            ('GD Quốc phòng & An ninh', 'Sinh hoạt lớp & Đánh giá thi đua tuần', 10.0, 'GVCN sinh hoạt nề nếp tuần đầy đủ')
        ]
    ]

    # Tạo sổ đầu bài tuần cho các lớp hàng đầu: 10A1, 10A2, 10A3, 11B1, 12C1...
    for c in classes[:8]: # 8 lớp đầu tiên
        cid = c['id']
        base_teacher = c['teacher_name'] or 'Thầy Cô'

        for day_idx, wd in enumerate(week_days):
            d_str = wd['date']
            d_name = wd['day_name']
            daily_lessons = sample_timetable[day_idx]

            for p_idx, lesson in enumerate(daily_lessons, 1):
                sub_name, l_title, default_score, note = lesson
                sub_id = sub_map.get(sub_name)

                # Biến thiên điểm số nhẹ giữa các lớp để bảng xếp hạng thi đua sinh động
                score_mod = (cid * 0.3 + p_idx * 0.2) % 1.5
                score = round(min(10.0, max(6.0, default_score - (0.5 if cid % 2 == 0 and p_idx == 3 else 0.0))), 1)
                cls = classify_score(score)

                cursor.execute('''
                INSERT OR REPLACE INTO lesson_records (
                    class_id, academic_year_id, semester, week_number, date, day_of_week,
                    period, subject_id, teacher_name, lesson_name, absent_students, score, classification, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cid, year_id, 1, 1, d_str, d_name, p_idx, sub_id, base_teacher, l_title, 'Không', score, cls, note))

    conn.commit()
    conn.close()
