from database import get_db

def calculate_subject_average(tx1, tx2, tx3, tx4, gk, ck):
    """
    Tính điểm trung bình môn theo quy chế:
    TX hệ số 1, GK hệ số 2, CK hệ số 3.
    """
    tx_vals = [float(x) for x in [tx1, tx2, tx3, tx4] if x is not None and str(x).strip() != '']
    if not tx_vals and gk is None and ck is None:
        return None

    total_weight = len(tx_vals)
    total_score = sum(tx_vals)

    if gk is not None and str(gk).strip() != '':
        total_weight += 2
        total_score += float(gk) * 2

    if ck is not None and str(ck).strip() != '':
        total_weight += 3
        total_score += float(ck) * 3

    if total_weight == 0:
        return None

    return round(total_score / total_weight, 1)

def evaluate_academic_performance(scores):
    """
    Xếp loại học lực theo Thông tư 22/2021/TT-BGDĐT:
    - Tốt: Tất cả >= 6.5, trong đó >= 6 môn đạt >= 8.0
    - Khá: Tất cả >= 5.0, trong đó >= 6 môn đạt >= 6.5
    - Đạt: Nhiều nhất 1 môn < 5.0 (nhưng >= 3.5), các môn khác >= 5.0
    - Chưa đạt: Còn lại
    """
    valid_scores = [s for s in scores if s is not None]
    if not valid_scores:
        return "Chưa xếp loại"

    total_subjects = len(valid_scores)
    count_gte_8 = sum(1 for s in valid_scores if s >= 8.0)
    count_gte_65 = sum(1 for s in valid_scores if s >= 6.5)
    count_gte_5 = sum(1 for s in valid_scores if s >= 5.0)
    count_lt_5 = sum(1 for s in valid_scores if s < 5.0)
    min_score = min(valid_scores)

    # Nếu số môn còn ít (chưa nhập đủ), xếp loại theo mức tương đối
    target_good = min(6, total_subjects)

    if min_score >= 6.5 and count_gte_8 >= target_good:
        return "Tốt"
    elif min_score >= 5.0 and count_gte_65 >= target_good:
        return "Khá"
    elif count_lt_5 <= 1 and min_score >= 3.5:
        return "Đạt"
    else:
        return "Chưa đạt"

def get_student_summary(student_id, semester=1, academic_year_id=None):
    """Lấy tổng hợp điểm và chuyên cần của 1 học sinh"""
    conn = get_db()
    cursor = conn.cursor()

    if not academic_year_id:
        cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
        row = cursor.fetchone()
        academic_year_id = row['id'] if row else 1

    # Lấy thông tin học sinh & lớp
    cursor.execute('''
    SELECT s.*, c.name as class_name, c.grade_level, c.teacher_name
    FROM students s
    LEFT JOIN classes c ON s.class_id = c.id
    WHERE s.id = ?
    ''', (student_id,))
    student = cursor.fetchone()

    # Lấy bảng điểm tất cả các môn
    cursor.execute('''
    SELECT sub.id as subject_id, sub.name as subject_name, sub.code as subject_code,
           sub.coefficient, g.tx1, g.tx2, g.tx3, g.tx4, g.gk, g.ck, g.average
    FROM subjects sub
    LEFT JOIN grades g ON g.subject_id = sub.id 
                       AND g.student_id = ? 
                       AND g.semester = ? 
                       AND g.academic_year_id = ?
    ORDER BY sub.id ASC
    ''', (student_id, semester, academic_year_id))
    grade_rows = cursor.fetchall()

    # Tính điểm trung bình chung
    scores = []
    total_weighted = 0.0
    total_coef = 0
    for r in grade_rows:
        if r['average'] is not None:
            scores.append(r['average'])
            coef = r['coefficient'] or 1
            total_weighted += r['average'] * coef
            total_coef += coef

    gpa = round(total_weighted / total_coef, 2) if total_coef > 0 else None
    academic_rank = evaluate_academic_performance(scores) if scores else "Chưa đánh giá"

    # Thống kê điểm danh
    cursor.execute('''
    SELECT 
        COUNT(CASE WHEN status = 'P' THEN 1 END) as present_count,
        COUNT(CASE WHEN status = 'CP' THEN 1 END) as excused_absence_count,
        COUNT(CASE WHEN status = 'KP' THEN 1 END) as unexcused_absence_count,
        COUNT(CASE WHEN status = 'T' THEN 1 END) as late_count,
        COUNT(*) as total_attendance_records
    FROM attendance
    WHERE student_id = ?
    ''', (student_id,))
    att_stats = cursor.fetchone()

    conn.close()

    return {
        'student': student,
        'grades': grade_rows,
        'gpa': gpa,
        'academic_rank': academic_rank,
        'attendance_stats': att_stats
    }

def get_class_statistics(class_id, semester=1, academic_year_id=None):
    """Thống kê chất lượng học tập và sĩ số lớp"""
    conn = get_db()
    cursor = conn.cursor()

    if not academic_year_id:
        cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
        row = cursor.fetchone()
        academic_year_id = row['id'] if row else 1

    cursor.execute("SELECT id, full_name, student_code FROM students WHERE class_id = ? AND status = 'Đang học'", (class_id,))
    students = cursor.fetchall()

    rank_counts = {"Tốt": 0, "Khá": 0, "Đạt": 0, "Chưa đạt": 0, "Chưa đánh giá": 0}
    student_results = []

    for st in students:
        summary = get_student_summary(st['id'], semester, academic_year_id)
        rank = summary['academic_rank']
        if rank in rank_counts:
            rank_counts[rank] += 1
        else:
            rank_counts["Chưa đánh giá"] += 1

        student_results.append({
            'student_id': st['id'],
            'student_code': st['student_code'],
            'full_name': st['full_name'],
            'gpa': summary['gpa'],
            'rank': rank,
            'attendance': summary['attendance_stats']
        })

    conn.close()

    return {
        'total_students': len(students),
        'rank_counts': rank_counts,
        'student_results': student_results
    }
