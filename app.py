import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from database import get_db, init_db, seed_sample_data
from statistics_service import calculate_subject_average, evaluate_academic_performance, get_student_summary, get_class_statistics
import excel_service
import lesson_diary_service

app = Flask(__name__)
app.secret_key = 'school_management_secret_key_2026'

# Custom Jinja filters
@app.template_filter('format_date')
def format_date_filter(value):
    if not value:
        return '---'
    try:
        if isinstance(value, str):
            dt = datetime.strptime(value.split(' ')[0], '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        return value.strftime('%d/%m/%Y')
    except Exception:
        return value

@app.template_filter('grade_format')
def grade_format_filter(value):
    if value is None or str(value).strip() == '':
        return '---'
    try:
        val = float(value)
        return f"{val:.1f}"
    except (ValueError, TypeError):
        return value

# Context processor để truyền thông tin trường học & năm học vào tất cả templates
@app.context_processor
def inject_global_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings_dict = {row['key']: row['value'] for row in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM academic_years WHERE is_active = 1")
    curr_year = cursor.fetchone()

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    all_classes = cursor.fetchall()
    conn.close()

    return {
        'settings': settings_dict,
        'current_year': curr_year,
        'all_nav_classes': all_classes,
        'today_date': date.today().isoformat()
    }

# ==================== DASHBOARD ====================
@app.route('/')
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    # Thống kê tổng quan
    cursor.execute("SELECT COUNT(*) as count FROM students WHERE status = 'Đang học'")
    active_students_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM students")
    total_students_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM classes")
    total_classes_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM subjects")
    total_subjects_count = cursor.fetchone()['count']

    # Thống kê điểm danh hôm nay
    today_str = date.today().isoformat()
    cursor.execute('''
    SELECT 
        COUNT(CASE WHEN status = 'P' THEN 1 END) as present,
        COUNT(CASE WHEN status = 'CP' THEN 1 END) as excused,
        COUNT(CASE WHEN status = 'KP' THEN 1 END) as unexcused,
        COUNT(CASE WHEN status = 'T' THEN 1 END) as late,
        COUNT(*) as total
    FROM attendance
    WHERE date = ?
    ''', (today_str,))
    att_today = cursor.fetchone()

    # Danh sách 6 học sinh mới nhất
    cursor.execute('''
    SELECT s.*, c.name as class_name
    FROM students s
    LEFT JOIN classes c ON s.class_id = c.id
    ORDER BY s.id DESC LIMIT 6
    ''')
    recent_students = cursor.fetchall()

    # Lấy phân bố học lực tổng hợp
    cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
    year_row = cursor.fetchone()
    curr_year_id = year_row['id'] if year_row else 1

    cursor.execute("SELECT id FROM students WHERE status = 'Đang học' LIMIT 60")
    students_sample = cursor.fetchall()

    ranks = {"Tốt": 0, "Khá": 0, "Đạt": 0, "Chưa đạt": 0}
    for st in students_sample:
        summary = get_student_summary(st['id'], semester=1, academic_year_id=curr_year_id)
        r = summary['academic_rank']
        if r in ranks:
            ranks[r] += 1

    conn.close()

    return render_template('dashboard.html',
                           active_students=active_students_count,
                           total_students=total_students_count,
                           total_classes=total_classes_count,
                           total_subjects=total_subjects_count,
                           att_today=att_today,
                           recent_students=recent_students,
                           ranks=ranks)

# ==================== QUẢN LÝ HỌC SINH ====================
@app.route('/students')
def student_list():
    keyword = request.args.get('keyword', '').strip()
    grade = request.args.get('grade', '').strip()
    class_id = request.args.get('class_id', '').strip()
    gender = request.args.get('gender', '').strip()
    status = request.args.get('status', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    query = '''
    SELECT s.*, c.name as class_name, c.grade_level
    FROM students s
    LEFT JOIN classes c ON s.class_id = c.id
    WHERE 1=1
    '''
    params = []

    if keyword:
        query += " AND (s.full_name LIKE ? OR s.student_code LIKE ? OR s.phone LIKE ?)"
        pattern = f"%{keyword}%"
        params.extend([pattern, pattern, pattern])

    if grade:
        query += " AND c.grade_level = ?"
        params.append(grade)

    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)

    if gender:
        query += " AND s.gender = ?"
        params.append(gender)

    if status:
        query += " AND s.status = ?"
        params.append(status)

    query += " ORDER BY c.grade_level ASC, LENGTH(c.name) ASC, c.name ASC, s.full_name ASC"
    cursor.execute(query, params)
    students = cursor.fetchall()

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()
    conn.close()

    return render_template('students/index.html',
                           students=students,
                           classes=classes,
                           keyword=keyword,
                           selected_grade=grade,
                           selected_class=class_id,
                           selected_gender=gender,
                           selected_status=status)

@app.route('/students/new', methods=['GET', 'POST'])
def student_create():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        student_code = request.form.get('student_code', '').strip()
        full_name = request.form.get('full_name', '').strip()
        dob = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', 'Nam')
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        parent_name = request.form.get('parent_name', '').strip()
        parent_phone = request.form.get('parent_phone', '').strip()
        email = request.form.get('email', '').strip()
        class_id = request.form.get('class_id') or None
        status = request.form.get('status', 'Đang học')

        if not student_code:
            cursor.execute("SELECT COUNT(*) as count FROM students")
            cnt = cursor.fetchone()['count'] + 1
            student_code = f"HS26{cnt:04d}"

        if not full_name:
            flash('Vui lòng nhập họ và tên học sinh!', 'danger')
            return redirect(url_for('student_create'))

        try:
            cursor.execute('''
            INSERT INTO students (student_code, full_name, date_of_birth, gender, address, phone, parent_name, parent_phone, email, class_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (student_code, full_name, dob, gender, address, phone, parent_name, parent_phone, email, class_id, status))
            conn.commit()
            new_id = cursor.lastrowid
            flash(f'Thêm học sinh {full_name} ({student_code}) thành công!', 'success')
            conn.close()
            return redirect(url_for('student_detail', student_id=new_id))
        except Exception as e:
            conn.rollback()
            flash(f'Lỗi khi thêm học sinh: {str(e)}', 'danger')

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()
    conn.close()
    return render_template('students/form.html', student=None, classes=classes, title="Thêm học sinh mới")

@app.route('/students/<int:student_id>')
def student_detail(student_id):
    semester = request.args.get('semester', '1')
    try:
        semester = int(semester)
    except ValueError:
        semester = 1

    summary = get_student_summary(student_id, semester=semester)
    if not summary['student']:
        flash('Không tìm thấy thông tin học sinh!', 'danger')
        return redirect(url_for('student_list'))

    # Lấy lịch sử điểm danh gần nhất
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT date, status, note 
    FROM attendance 
    WHERE student_id = ? 
    ORDER BY date DESC LIMIT 15
    ''', (student_id,))
    recent_attendance = cursor.fetchall()
    conn.close()

    return render_template('students/detail.html',
                           student=summary['student'],
                           grades=summary['grades'],
                           gpa=summary['gpa'],
                           academic_rank=summary['academic_rank'],
                           att_stats=summary['attendance_stats'],
                           recent_attendance=recent_attendance,
                           semester=semester)

@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
def student_edit(student_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        flash('Học sinh không tồn tại!', 'danger')
        return redirect(url_for('student_list'))

    if request.method == 'POST':
        student_code = request.form.get('student_code', '').strip()
        full_name = request.form.get('full_name', '').strip()
        dob = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', 'Nam')
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        parent_name = request.form.get('parent_name', '').strip()
        parent_phone = request.form.get('parent_phone', '').strip()
        email = request.form.get('email', '').strip()
        class_id = request.form.get('class_id') or None
        status = request.form.get('status', 'Đang học')

        try:
            cursor.execute('''
            UPDATE students SET
                student_code = ?, full_name = ?, date_of_birth = ?, gender = ?,
                address = ?, phone = ?, parent_name = ?, parent_phone = ?,
                email = ?, class_id = ?, status = ?
            WHERE id = ?
            ''', (student_code, full_name, dob, gender, address, phone, parent_name, parent_phone, email, class_id, status, student_id))
            conn.commit()
            conn.close()
            flash(f'Cập nhật thông tin học sinh {full_name} thành công!', 'success')
            return redirect(url_for('student_detail', student_id=student_id))
        except Exception as e:
            conn.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()
    conn.close()
    return render_template('students/form.html', student=student, classes=classes, title=f"Sửa hồ sơ - {student['full_name']}")

@app.route('/students/<int:student_id>/delete', methods=['POST'])
def student_delete(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if student:
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        flash(f'Đã xóa học sinh {student["full_name"]}!', 'warning')
    conn.close()
    return redirect(url_for('student_list'))

# ==================== EXCEL IMPORT / EXPORT ====================
@app.route('/students/template')
def download_student_template():
    stream = excel_service.create_student_template()
    return send_file(
        stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='Mau_Nhap_Hoc_Sinh.xlsx'
    )

@app.route('/students/import', methods=['GET', 'POST'])
def student_import():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        class_id = request.form.get('class_id')
        if not class_id:
            flash('Vui lòng chọn lớp học để nhập danh sách!', 'danger')
            return redirect(url_for('student_import'))

        file = request.files.get('excel_file')
        if not file or file.filename == '':
            flash('Vui lòng chọn file Excel (.xlsx)!', 'danger')
            return redirect(url_for('student_import'))

        try:
            result = excel_service.import_students_from_excel(file.stream, class_id)
            msg = f"Đã nhập thành công: {result['success_count']} học sinh mới, cập nhật: {result['updated_count']} học sinh."
            if result['errors']:
                msg += f" (Có {len(result['errors'])} lỗi nhỏ: {', '.join(result['errors'][:3])})"
            flash(msg, 'success')
            return redirect(url_for('classroom_detail', class_id=class_id))
        except Exception as e:
            flash(f'Lỗi khi xử lý file Excel: {str(e)}', 'danger')

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()
    conn.close()
    return render_template('students/import.html', classes=classes)

@app.route('/students/export/<int:class_id>')
def student_export(class_id):
    stream = excel_service.export_students_by_class(class_id)
    return send_file(
        stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Danh_sach_lop_{class_id}.xlsx'
    )

# ==================== QUẢN LÝ LỚP HỌC ====================
@app.route('/classrooms')
def classroom_list():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT c.*, y.name as year_name,
           COUNT(s.id) as total_students,
           COUNT(CASE WHEN s.gender = 'Nam' THEN 1 END) as male_count,
           COUNT(CASE WHEN s.gender = 'Nữ' THEN 1 END) as female_count
    FROM classes c
    JOIN academic_years y ON c.academic_year_id = y.id
    LEFT JOIN students s ON s.class_id = c.id AND s.status = 'Đang học'
    GROUP BY c.id
    ORDER BY c.grade_level ASC, LENGTH(c.name) ASC, c.name ASC
    ''')
    classes = cursor.fetchall()

    cursor.execute("SELECT id, name FROM academic_years ORDER BY id DESC")
    years = cursor.fetchall()
    conn.close()

    return render_template('classrooms/index.html', classes=classes, years=years)

@app.route('/classrooms/new', methods=['POST'])
def classroom_create():
    name = request.form.get('name', '').strip()
    grade_level = request.form.get('grade_level', 10)
    teacher_name = request.form.get('teacher_name', '').strip()
    room = request.form.get('room', '').strip()
    academic_year_id = request.form.get('academic_year_id')

    if not name:
        flash('Vui lòng nhập tên lớp!', 'danger')
        return redirect(url_for('classroom_list'))

    conn = get_db()
    cursor = conn.cursor()
    if not academic_year_id:
        cursor.execute("SELECT id FROM academic_years WHERE is_active = 1")
        row = cursor.fetchone()
        academic_year_id = row['id'] if row else 1

    try:
        cursor.execute('''
        INSERT INTO classes (name, grade_level, academic_year_id, teacher_name, room)
        VALUES (?, ?, ?, ?, ?)
        ''', (name, grade_level, academic_year_id, teacher_name, room))
        conn.commit()
        flash(f'Tạo lớp {name} thành công!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Lỗi tạo lớp: {str(e)}', 'danger')

    conn.close()
    return redirect(url_for('classroom_list'))

@app.route('/classrooms/<int:class_id>')
def classroom_detail(class_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT c.*, y.name as year_name
    FROM classes c
    JOIN academic_years y ON c.academic_year_id = y.id
    WHERE c.id = ?
    ''', (class_id,))
    classroom = cursor.fetchone()

    if not classroom:
        conn.close()
        flash('Không tìm thấy lớp học!', 'danger')
        return redirect(url_for('classroom_list'))

    cursor.execute('''
    SELECT * FROM students 
    WHERE class_id = ? 
    ORDER BY status ASC, full_name ASC
    ''', (class_id,))
    students = cursor.fetchall()

    # Thống kê nhanh của lớp
    stats = get_class_statistics(class_id, semester=1, academic_year_id=classroom['academic_year_id'])

    cursor.execute("SELECT id, name, grade_level FROM classes WHERE id != ? ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC", (class_id,))
    other_classes = cursor.fetchall()

    conn.close()
    return render_template('classrooms/detail.html',
                           classroom=classroom,
                           students=students,
                           stats=stats,
                           other_classes=other_classes)

@app.route('/classrooms/<int:class_id>/edit', methods=['POST'])
def classroom_edit(class_id):
    name = request.form.get('name', '').strip()
    grade_level = request.form.get('grade_level')
    teacher_name = request.form.get('teacher_name', '').strip()
    room = request.form.get('room', '').strip()

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        UPDATE classes SET name = ?, grade_level = ?, teacher_name = ?, room = ?
        WHERE id = ?
        ''', (name, grade_level, teacher_name, room, class_id))
        conn.commit()
        flash(f'Cập nhật thông tin lớp {name} thành công!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')

    conn.close()
    return redirect(url_for('classroom_detail', class_id=class_id))

# ==================== SỔ ĐIỂM & ĐÁNH GIÁ ====================
@app.route('/grades')
def grade_list():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, name, code FROM subjects ORDER BY id ASC")
    subjects = cursor.fetchall()

    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    semester = request.args.get('semester', '1')

    try:
        semester = int(semester)
    except ValueError:
        semester = 1

    if not class_id and classes:
        class_id = str(classes[0]['id'])
    if not subject_id and subjects:
        subject_id = str(subjects[0]['id'])

    current_class = None
    current_subject = None
    grades_data = []

    if class_id and subject_id:
        cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        current_class = cursor.fetchone()

        cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        current_subject = cursor.fetchone()

        cursor.execute('''
        SELECT s.id as student_id, s.student_code, s.full_name,
               g.id as grade_id, g.tx1, g.tx2, g.tx3, g.tx4, g.gk, g.ck, g.average
        FROM students s
        LEFT JOIN grades g ON g.student_id = s.id 
                           AND g.subject_id = ? 
                           AND g.semester = ?
                           AND g.academic_year_id = ?
        WHERE s.class_id = ? AND s.status = 'Đang học'
        ORDER BY s.full_name ASC
        ''', (subject_id, semester, current_class['academic_year_id'] if current_class else 1, class_id))
        grades_data = cursor.fetchall()

    conn.close()

    return render_template('grades/index.html',
                           classes=classes,
                           subjects=subjects,
                           selected_class_id=int(class_id) if class_id else None,
                           selected_subject_id=int(subject_id) if subject_id else None,
                           current_class=current_class,
                           current_subject=current_subject,
                           semester=semester,
                           grades_data=grades_data)

@app.route('/grades/input')
def grade_input():
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    semester = request.args.get('semester', '1')

    try:
        semester = int(semester)
    except ValueError:
        semester = 1

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, name, code FROM subjects ORDER BY id ASC")
    subjects = cursor.fetchall()

    if not class_id and classes:
        class_id = str(classes[0]['id'])
    if not subject_id and subjects:
        subject_id = str(subjects[0]['id'])

    cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
    current_class = cursor.fetchone()

    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    current_subject = cursor.fetchone()

    cursor.execute('''
    SELECT s.id as student_id, s.student_code, s.full_name,
           g.tx1, g.tx2, g.tx3, g.tx4, g.gk, g.ck, g.average
    FROM students s
    LEFT JOIN grades g ON g.student_id = s.id 
                       AND g.subject_id = ? 
                       AND g.semester = ?
                       AND g.academic_year_id = ?
    WHERE s.class_id = ? AND s.status = 'Đang học'
    ORDER BY s.full_name ASC
    ''', (subject_id, semester, current_class['academic_year_id'] if current_class else 1, class_id))
    students_grades = cursor.fetchall()

    conn.close()

    return render_template('grades/input_grade.html',
                           classes=classes,
                           subjects=subjects,
                           selected_class_id=int(class_id) if class_id else None,
                           selected_subject_id=int(subject_id) if subject_id else None,
                           current_class=current_class,
                           current_subject=current_subject,
                           semester=semester,
                           students_grades=students_grades)

@app.route('/grades/save_bulk', methods=['POST'])
def grade_save_bulk():
    class_id = request.form.get('class_id')
    subject_id = request.form.get('subject_id')
    semester = int(request.form.get('semester', 1))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT academic_year_id FROM classes WHERE id = ?", (class_id,))
    class_row = cursor.fetchone()
    year_id = class_row['academic_year_id'] if class_row else 1

    student_ids = request.form.getlist('student_id')

    def parse_float(val):
        if val is None or str(val).strip() == '':
            return None
        try:
            v = float(val)
            return min(max(v, 0.0), 10.0) # Kẹp điểm từ 0.0 đến 10.0
        except ValueError:
            return None

    saved_count = 0
    for sid in student_ids:
        tx1 = parse_float(request.form.get(f'tx1_{sid}'))
        tx2 = parse_float(request.form.get(f'tx2_{sid}'))
        tx3 = parse_float(request.form.get(f'tx3_{sid}'))
        tx4 = parse_float(request.form.get(f'tx4_{sid}'))
        gk = parse_float(request.form.get(f'gk_{sid}'))
        ck = parse_float(request.form.get(f'ck_{sid}'))

        avg = calculate_subject_average(tx1, tx2, tx3, tx4, gk, ck)

        cursor.execute('''
        INSERT INTO grades (student_id, subject_id, semester, academic_year_id, tx1, tx2, tx3, tx4, gk, ck, average)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, subject_id, semester, academic_year_id) DO UPDATE SET
            tx1 = excluded.tx1,
            tx2 = excluded.tx2,
            tx3 = excluded.tx3,
            tx4 = excluded.tx4,
            gk = excluded.gk,
            ck = excluded.ck,
            average = excluded.average,
            updated_at = CURRENT_TIMESTAMP
        ''', (sid, subject_id, semester, year_id, tx1, tx2, tx3, tx4, gk, ck, avg))
        saved_count += 1

    conn.commit()
    conn.close()

    flash(f'Đã lưu bảng điểm thành công cho {saved_count} học sinh!', 'success')
    return redirect(url_for('grade_list', class_id=class_id, subject_id=subject_id, semester=semester))

@app.route('/grades/export/<int:class_id>/<int:subject_id>/<int:semester>')
def grade_export_subject(class_id, subject_id, semester):
    stream = excel_service.export_grades_by_class_and_subject(class_id, subject_id, semester)
    return send_file(
        stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Bang_diem_lop_{class_id}_mon_{subject_id}_hk{semester}.xlsx'
    )

@app.route('/grades/report-card/<int:student_id>')
def grade_report_card(student_id):
    semester = request.args.get('semester', '1')
    try:
        semester = int(semester)
    except ValueError:
        semester = 1

    summary = get_student_summary(student_id, semester=semester)
    if not summary['student']:
        flash('Không tìm thấy học sinh!', 'danger')
        return redirect(url_for('student_list'))

    return render_template('grades/report_card.html',
                           student=summary['student'],
                           grades=summary['grades'],
                           gpa=summary['gpa'],
                           academic_rank=summary['academic_rank'],
                           att_stats=summary['attendance_stats'],
                           semester=semester)

# ==================== ĐIỂM DANH & CHUYÊN CẦN ====================
@app.route('/attendance')
def attendance_index():
    date_str = request.args.get('date', date.today().isoformat())
    class_id = request.args.get('class_id')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    if not class_id and classes:
        class_id = str(classes[0]['id'])

    current_class = None
    attendance_records = []

    if class_id:
        cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        current_class = cursor.fetchone()

        cursor.execute('''
        SELECT s.id as student_id, s.student_code, s.full_name, s.gender,
               a.status, a.note
        FROM students s
        LEFT JOIN attendance a ON a.student_id = s.id AND a.date = ?
        WHERE s.class_id = ? AND s.status = 'Đang học'
        ORDER BY s.full_name ASC
        ''', (date_str, class_id))
        attendance_records = cursor.fetchall()

    conn.close()

    return render_template('attendance/index.html',
                           classes=classes,
                           current_class=current_class,
                           selected_class_id=int(class_id) if class_id else None,
                           selected_date=date_str,
                           records=attendance_records)

@app.route('/attendance/save', methods=['POST'])
def attendance_save():
    class_id = request.form.get('class_id')
    date_str = request.form.get('date')

    student_ids = request.form.getlist('student_id')

    conn = get_db()
    cursor = conn.cursor()

    count = 0
    for sid in student_ids:
        status = request.form.get(f'status_{sid}', 'P')
        note = request.form.get(f'note_{sid}', '').strip()

        cursor.execute('''
        INSERT INTO attendance (student_id, class_id, date, status, note)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(student_id, date) DO UPDATE SET
            status = excluded.status,
            note = excluded.note
        ''', (sid, class_id, date_str, status, note))
        count += 1

    conn.commit()
    conn.close()

    flash(f'Đã cập nhật điểm danh ngày {date_str} cho {count} học sinh!', 'success')
    return redirect(url_for('attendance_index', class_id=class_id, date=date_str))

@app.route('/attendance/report')
def attendance_report():
    class_id = request.args.get('class_id')
    month = request.args.get('month', datetime.today().strftime('%Y-%m'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    if not class_id and classes:
        class_id = str(classes[0]['id'])

    report_data = []
    current_class = None

    if class_id:
        cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        current_class = cursor.fetchone()

        # Thống kê điểm danh trong tháng
        cursor.execute('''
        SELECT s.id, s.student_code, s.full_name,
               COUNT(CASE WHEN a.status = 'P' THEN 1 END) as present_count,
               COUNT(CASE WHEN a.status = 'CP' THEN 1 END) as cp_count,
               COUNT(CASE WHEN a.status = 'KP' THEN 1 END) as kp_count,
               COUNT(CASE WHEN a.status = 'T' THEN 1 END) as late_count
        FROM students s
        LEFT JOIN attendance a ON a.student_id = s.id AND strftime('%Y-%m', a.date) = ?
        WHERE s.class_id = ? AND s.status = 'Đang học'
        GROUP BY s.id
        ORDER BY s.full_name ASC
        ''', (month, class_id))
        report_data = cursor.fetchall()

    conn.close()

    return render_template('attendance/report.html',
                           classes=classes,
                           current_class=current_class,
                           selected_class_id=int(class_id) if class_id else None,
                           selected_month=month,
                           report_data=report_data)

# ==================== MÔN HỌC ====================
@app.route('/subjects', methods=['GET', 'POST'])
def subject_list():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            code = request.form.get('code', '').strip().upper()
            name = request.form.get('name', '').strip()
            category = request.form.get('category', 'Khoa học tự nhiên')
            coef = int(request.form.get('coefficient', 1))
            periods = int(request.form.get('periods', 70))

            if code and name:
                try:
                    cursor.execute('''
                    INSERT INTO subjects (code, name, category, coefficient, periods)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (code, name, category, coef, periods))
                    conn.commit()
                    flash(f'Thêm môn {name} ({code}) thành công!', 'success')
                except Exception as e:
                    conn.rollback()
                    flash(f'Lỗi thêm môn: {str(e)}', 'danger')

        elif action == 'edit':
            sub_id = request.form.get('subject_id')
            name = request.form.get('name', '').strip()
            category = request.form.get('category')
            coef = int(request.form.get('coefficient', 1))
            periods = int(request.form.get('periods', 70))
            try:
                cursor.execute('''
                UPDATE subjects SET name = ?, category = ?, coefficient = ?, periods = ?
                WHERE id = ?
                ''', (name, category, coef, periods, sub_id))
                conn.commit()
                flash('Cập nhật môn học thành công!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    cursor.execute("SELECT * FROM subjects ORDER BY id ASC")
    subjects = cursor.fetchall()
    conn.close()

    return render_template('subjects/index.html', subjects=subjects)

# ==================== CÀI ĐẶT TRƯỜNG HỌC ====================
@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        settings_to_update = [
            'school_name', 'school_address', 'school_phone',
            'school_email', 'principal_name', 'current_semester'
        ]
        for key in settings_to_update:
            val = request.form.get(key, '').strip()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))

        # Năm học kích hoạt
        active_year_id = request.form.get('active_year_id')
        if active_year_id:
            cursor.execute("UPDATE academic_years SET is_active = 0")
            cursor.execute("UPDATE academic_years SET is_active = 1 WHERE id = ?", (active_year_id,))
            cursor.execute("SELECT name FROM academic_years WHERE id = ?", (active_year_id,))
            yr_name = cursor.fetchone()['name']
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_academic_year', ?)", (yr_name,))

        # Thêm năm học mới nếu có
        new_year_name = request.form.get('new_year_name', '').strip()
        if new_year_name:
            try:
                cursor.execute("INSERT INTO academic_years (name, is_active) VALUES (?, 0)", (new_year_name,))
                flash(f'Đã thêm năm học mới: {new_year_name}', 'info')
            except Exception:
                pass

        conn.commit()
        flash('Đã lưu cài đặt trường học thành công!', 'success')

    cursor.execute("SELECT key, value FROM settings")
    settings_dict = {row['key']: row['value'] for row in cursor.fetchall()}

    cursor.execute("SELECT * FROM academic_years ORDER BY id DESC")
    years = cursor.fetchall()
    conn.close()

    return render_template('settings/index.html', settings_data=settings_dict, years=years)

# ==================== SỔ ĐẦU BÀI & CHẤM ĐIỂM TIẾT HỌC ====================
@app.route('/class-diary')
def class_diary_index():
    class_id = request.args.get('class_id')
    base_date = request.args.get('date', date.today().isoformat())

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, grade_level FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    if not class_id and classes:
        class_id = str(classes[0]['id'])

    diary_data = None
    if class_id:
        diary_data = lesson_diary_service.get_class_diary(int(class_id), base_date=base_date)

    cursor.execute("SELECT id, name, code FROM subjects ORDER BY id ASC")
    subjects = cursor.fetchall()
    conn.close()

    return render_template('class_diary/index.html',
                           classes=classes,
                           selected_class_id=int(class_id) if class_id else None,
                           base_date=base_date,
                           diary_data=diary_data,
                           subjects=subjects)

@app.route('/class-diary/input')
def class_diary_input():
    class_id = request.args.get('class_id')
    date_str = request.args.get('date', date.today().isoformat())
    period = request.args.get('period', '1')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, grade_level, teacher_name FROM classes ORDER BY grade_level ASC, LENGTH(name) ASC, name ASC")
    classes = cursor.fetchall()

    cursor.execute("SELECT id, name, code FROM subjects ORDER BY id ASC")
    subjects = cursor.fetchall()

    if not class_id and classes:
        class_id = str(classes[0]['id'])

    # Lấy thông tin tiết học hiện tại nếu đã có
    cursor.execute('''
    SELECT * FROM lesson_records 
    WHERE class_id = ? AND date = ? AND period = ?
    ''', (class_id, date_str, period))
    existing_record = cursor.fetchone()

    # Xác định Thứ trong tuần
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_map = {0: 'Thứ Hai', 1: 'Thứ Ba', 2: 'Thứ Tư', 3: 'Thứ Năm', 4: 'Thứ Sáu', 5: 'Thứ Bảy', 6: 'Chủ Nhật'}
        day_of_week = day_map.get(dt.weekday(), 'Thứ Hai')
    except Exception:
        day_of_week = 'Thứ Hai'

    cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
    current_class = cursor.fetchone()
    conn.close()

    return render_template('class_diary/input.html',
                           classes=classes,
                           subjects=subjects,
                           selected_class_id=int(class_id) if class_id else None,
                           current_class=current_class,
                           selected_date=date_str,
                           selected_period=int(period),
                           day_of_week=day_of_week,
                           record=existing_record)

@app.route('/class-diary/save', methods=['POST'])
def class_diary_save():
    class_id = int(request.form.get('class_id'))
    date_str = request.form.get('date')
    day_of_week = request.form.get('day_of_week')
    period = int(request.form.get('period'))
    subject_id = request.form.get('subject_id') or None
    teacher_name = request.form.get('teacher_name', '').strip()
    lesson_name = request.form.get('lesson_name', '').strip()
    absent_students = request.form.get('absent_students', '').strip() or 'Không'
    score_str = request.form.get('score', '').strip()
    note = request.form.get('note', '').strip()

    score = None
    if score_str:
        try:
            score = float(score_str)
            score = min(max(score, 0.0), 10.0)
        except ValueError:
            score = None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT academic_year_id FROM classes WHERE id = ?", (class_id,))
    c_row = cursor.fetchone()
    year_id = c_row['academic_year_id'] if c_row else 1
    conn.close()

    lesson_diary_service.save_lesson_record(
        class_id=class_id,
        academic_year_id=year_id,
        semester=1,
        week_number=1,
        date_str=date_str,
        day_of_week=day_of_week,
        period=period,
        subject_id=subject_id,
        teacher_name=teacher_name,
        lesson_name=lesson_name,
        absent_students=absent_students,
        score=score,
        note=note
    )

    flash(f'Đã cập nhật sổ đầu bài: {day_of_week} - Tiết {period} (Điểm: {score if score is not None else "---"})', 'success')
    return redirect(url_for('class_diary_index', class_id=class_id, date=date_str))

@app.route('/class-diary/ranking')
def class_diary_ranking():
    base_date = request.args.get('date', date.today().isoformat())
    ranking_data = lesson_diary_service.get_weekly_ranking(base_date)

    return render_template('class_diary/ranking.html',
                           ranking_data=ranking_data,
                           base_date=base_date)

@app.route('/class-diary/export/<int:class_id>')
def class_diary_export(class_id):
    base_date = request.args.get('date', date.today().isoformat())
    stream = excel_service.export_lesson_diary_by_class(class_id, base_date=base_date)
    return send_file(
        stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'So_Dau_Bai_Lop_{class_id}.xlsx'
    )

# ==================== ENTRY POINT ====================
def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    init_db()
    seed_sample_data()
    lesson_diary_service.seed_sample_diary()
    local_ip = get_local_ip()
    print("="*65)
    print("  ỨNG DỤNG QUẢN LÝ HỌC SINH & SỔ ĐẦU BÀI ĐANG CHẠY...")
    print(f"  [1] Truy cập từ máy tính này:  http://127.0.0.1:5000")
    print(f"  [2] Chia sẻ qua Wi-Fi / LAN:   http://{local_ip}:5000")
    print("  (Các thầy cô kết nối cùng Wi-Fi chỉ cần mở link [2] trên điện thoại/laptop)")
    print("="*65)
    app.run(host='0.0.0.0', port=5000, debug=True)
