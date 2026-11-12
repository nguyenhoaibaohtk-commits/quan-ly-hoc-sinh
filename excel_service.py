import os
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database import get_db

def create_student_template():
    """Tạo file Excel mẫu để nhập danh sách học sinh"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DanhSachHocSinh"

    # Style
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    guide_font = Font(name="Arial", size=10, italic=True, color="595959")
    border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # Tiêu đề file
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = "DANH SÁCH HỌC SINH MẪU (IMPORT VÀO HỆ THỐNG)"
    title_cell.font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:I2")
    guide_cell = ws["A2"]
    guide_cell.value = "* Hướng dẫn: Nhập đúng định dạng Ngày sinh (YYYY-MM-DD hoặc DD/MM/YYYY), Giới tính (Nam/Nữ). Không xóa dòng tiêu đề số 4."
    guide_cell.font = guide_font

    headers = [
        "Mã học sinh (*)", "Họ và tên (*)", "Ngày sinh", "Giới tính",
        "Địa chỉ", "Số ĐT học sinh", "Họ tên phụ huynh", "Số ĐT phụ huynh", "Email"
    ]

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Dòng mẫu
    sample_rows = [
        ["HS26101", "Nguyễn Tuấn Anh", "2011-04-12", "Nam", "12 Bà Triệu, Hoàn Kiếm, HN", "0901234001", "Nguyễn Văn Hùng", "0987111001", "tuananh@school.edu.vn"],
        ["HS26102", "Trần Mai Phương", "2011-09-25", "Nữ", "45 Hàng Bài, Hoàn Kiếm, HN", "0901234002", "Trần Quốc Tuấn", "0987111002", "maiphuong@school.edu.vn"],
        ["HS26103", "Lê Gia Hưng", "2011-02-18", "Nam", "78 Phố Huế, Hai Bà Trưng, HN", "0901234003", "Lê Văn Khoa", "0987111003", "giahung@school.edu.vn"]
    ]

    for r_idx, row_data in enumerate(sample_rows, 5):
        for c_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.value = val
            cell.font = Font(name="Arial", size=10)
            cell.border = border
            if c_idx in [1, 3, 4, 6, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Tự động điều chỉnh độ rộng cột
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row >= 4 and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 5, 14)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def import_students_from_excel(file_stream, class_id):
    """Đọc file Excel và nhập học sinh vào lớp học"""
    conn = get_db()
    cursor = conn.cursor()

    wb = openpyxl.load_workbook(file_stream, data_only=True)
    ws = wb.active

    # Tìm dòng tiêu đề (thường là dòng 4 hoặc dòng có chữ 'Mã' / 'Họ và tên')
    header_row = None
    for r in range(1, 10):
        row_vals = [str(ws.cell(row=r, column=c).value or '').lower() for c in range(1, 10)]
        if any('mã' in v for v in row_vals) or any('họ' in v for v in row_vals):
            header_row = r
            break

    if not header_row:
        header_row = 4

    success_count = 0
    updated_count = 0
    errors = []

    for r in range(header_row + 1, ws.max_row + 1):
        code = str(ws.cell(row=r, column=1).value or '').strip()
        full_name = str(ws.cell(row=r, column=2).value or '').strip()

        if not code and not full_name:
            continue

        if not full_name:
            errors.append(f"Dòng {r}: Thiếu họ tên học sinh")
            continue

        dob_val = ws.cell(row=r, column=3).value
        dob_str = None
        if isinstance(dob_val, datetime):
            dob_str = dob_val.strftime('%Y-%m-%d')
        elif dob_val:
            dob_str = str(dob_val).strip()
            if '/' in dob_str:
                parts = dob_str.split('/')
                if len(parts) == 3:
                    dob_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

        gender = str(ws.cell(row=r, column=4).value or 'Nam').strip()
        if gender.lower() in ['nữ', 'nu', 'female', 'f']:
            gender = 'Nữ'
        else:
            gender = 'Nam'

        address = str(ws.cell(row=r, column=5).value or '').strip()
        phone = str(ws.cell(row=r, column=6).value or '').strip()
        parent_name = str(ws.cell(row=r, column=7).value or '').strip()
        parent_phone = str(ws.cell(row=r, column=8).value or '').strip()
        email = str(ws.cell(row=r, column=9).value or '').strip()

        if not code:
            cursor.execute("SELECT COUNT(*) as cnt FROM students")
            cnt = cursor.fetchone()['cnt'] + 1
            code = f"HS26{cnt:04d}"

        try:
            cursor.execute("SELECT id FROM students WHERE student_code = ?", (code,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                UPDATE students SET
                    full_name = ?, date_of_birth = ?, gender = ?, address = ?,
                    phone = ?, parent_name = ?, parent_phone = ?, email = ?, class_id = ?
                WHERE id = ?
                ''', (full_name, dob_str, gender, address, phone, parent_name, parent_phone, email, class_id, existing['id']))
                updated_count += 1
            else:
                cursor.execute('''
                INSERT INTO students (student_code, full_name, date_of_birth, gender, address, phone, parent_name, parent_phone, email, status, class_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Đang học', ?)
                ''', (code, full_name, dob_str, gender, address, phone, parent_name, parent_phone, email, class_id))
                success_count += 1
        except Exception as e:
            errors.append(f"Dòng {r} ({full_name}): {str(e)}")

    conn.commit()
    conn.close()

    return {
        'success_count': success_count,
        'updated_count': updated_count,
        'errors': errors
    }

def export_students_by_class(class_id):
    """Xuất danh sách học sinh theo lớp ra file Excel định dạng đẹp"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT c.name as class_name, c.grade_level, c.teacher_name, c.room, y.name as year_name
    FROM classes c
    JOIN academic_years y ON c.academic_year_id = y.id
    WHERE c.id = ?
    ''', (class_id,))
    class_info = cursor.fetchone()

    cursor.execute("SELECT value FROM settings WHERE key = 'school_name'")
    school_name = cursor.fetchone()['value'] or 'Trường THPT'

    cursor.execute('''
    SELECT student_code, full_name, date_of_birth, gender, address, phone, parent_name, parent_phone, email, status
    FROM students
    WHERE class_id = ?
    ORDER BY full_name ASC
    ''', (class_id,))
    students = cursor.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Lớp {class_info['class_name']}"

    # Styles
    title_font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    border = Border(
        left=Side(style='thin', color='B0B0B0'),
        right=Side(style='thin', color='B0B0B0'),
        top=Side(style='thin', color='B0B0B0'),
        bottom=Side(style='thin', color='B0B0B0')
    )

    ws["A1"] = school_name.upper()
    ws["A1"].font = Font(name="Arial", size=11, bold=True)

    ws.merge_cells("A3:J3")
    ws["A3"] = f"DANH SÁCH HỌC SINH - LỚP {class_info['class_name']} (NĂM HỌC: {class_info['year_name']})"
    ws["A3"].font = title_font
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A4:J4")
    ws["A4"] = f"Giáo viên chủ nhiệm: {class_info['teacher_name'] or 'Chưa phân công'} | Phòng: {class_info['room'] or '---'} | Sĩ số: {len(students)} học sinh"
    ws["A4"].font = Font(name="Arial", size=10, italic=True)
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["STT", "Mã HS", "Họ và tên", "Ngày sinh", "Giới tính", "Địa chỉ", "Số ĐT", "Phụ huynh", "SĐT Phụ huynh", "Trạng thái"]
    for c_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=6, column=c_idx)
        cell.value = h
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx, s in enumerate(students, 7):
        stt = r_idx - 6
        dob = s['date_of_birth'] or ''
        data = [stt, s['student_code'], s['full_name'], dob, s['gender'], s['address'], s['phone'], s['parent_name'], s['parent_phone'], s['status']]
        for c_idx, val in enumerate(data, 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.value = val
            cell.font = Font(name="Arial", size=10)
            cell.border = border
            if c_idx in [1, 2, 4, 5, 7, 9, 10]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col if cell.row >= 6)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 11)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def export_grades_by_class_and_subject(class_id, subject_id, semester=1):
    """Xuất bảng điểm một môn học của cả lớp ra Excel"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT c.name as class_name, y.name as year_name, y.id as year_id
    FROM classes c
    JOIN academic_years y ON c.academic_year_id = y.id
    WHERE c.id = ?
    ''', (class_id,))
    cls = cursor.fetchone()

    cursor.execute("SELECT name, code FROM subjects WHERE id = ?", (subject_id,))
    subj = cursor.fetchone()

    cursor.execute("SELECT value FROM settings WHERE key = 'school_name'")
    school_name = cursor.fetchone()['value'] or 'Trường THPT'

    cursor.execute('''
    SELECT s.student_code, s.full_name, g.tx1, g.tx2, g.tx3, g.tx4, g.gk, g.ck, g.average
    FROM students s
    LEFT JOIN grades g ON g.subject_id = ? 
                       AND g.semester = ? 
                       AND g.academic_year_id = ?
    WHERE s.class_id = ? AND s.status = 'Đang học'
    ORDER BY s.full_name ASC
    ''', (subject_id, semester, cls['year_id'], class_id))
    rows = cursor.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Điểm {subj['code']}"

    ws["A1"] = school_name.upper()
    ws["A1"].font = Font(name="Arial", size=11, bold=True)

    ws.merge_cells("A3:J3")
    ws["A3"] = f"BẢNG ĐIỂM MÔN {subj['name'].upper()} - LỚP {cls['class_name']}"
    ws["A3"].font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A4:J4")
    ws["A4"] = f"Học kỳ: {semester} | Năm học: {cls['year_name']}"
    ws["A4"].font = Font(name="Arial", size=11, italic=True)
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["STT", "Mã HS", "Họ và tên", "TX 1", "TX 2", "TX 3", "TX 4", "Giữa kỳ (x2)", "Cuối kỳ (x3)", "ĐTB Môn"]
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    border = Border(
        left=Side(style='thin', color='B0B0B0'),
        right=Side(style='thin', color='B0B0B0'),
        top=Side(style='thin', color='B0B0B0'),
        bottom=Side(style='thin', color='B0B0B0')
    )

    for c_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=6, column=c_idx)
        cell.value = h
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx, r in enumerate(rows, 7):
        stt = r_idx - 6
        data = [stt, r['student_code'], r['full_name'], r['tx1'], r['tx2'], r['tx3'], r['tx4'], r['gk'], r['ck'], r['average']]
        for c_idx, val in enumerate(data, 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.value = val
            cell.font = Font(name="Arial", size=10)
            cell.border = border
            if c_idx == 3:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if c_idx == 10 and val is not None:
                cell.font = Font(name="Arial", size=10, bold=True, color="C00000" if float(val) < 5.0 else "006100")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col if cell.row >= 6)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 11)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def export_lesson_diary_by_class(class_id, base_date=None):
    """Xuất Sổ Đầu Bài tuần (từ Thứ 2 đến Thứ 7) ra file Excel"""
    import lesson_diary_service
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = 'school_name'")
    school_name = cursor.fetchone()['value'] or 'Trường THPT'

    diary_data = lesson_diary_service.get_class_diary(class_id, base_date=base_date)
    classroom = diary_data['classroom']
    week_days = diary_data['week_days']
    grid = diary_data['grid']
    summary = diary_data['summary']

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Sổ Đầu Bài - {classroom['name']}"

    # Styles
    title_font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    day_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    day_font = Font(name="Arial", size=10, bold=True, color="1F4E78")
    border = Border(
        left=Side(style='thin', color='B0B0B0'),
        right=Side(style='thin', color='B0B0B0'),
        top=Side(style='thin', color='B0B0B0'),
        bottom=Side(style='thin', color='B0B0B0')
    )

    ws["A1"] = school_name.upper()
    ws["A1"].font = Font(name="Arial", size=11, bold=True)

    ws.merge_cells("A3:J3")
    ws["A3"] = f"SỔ ĐẦU BÀI & ĐIỂM TIẾT HỌC (THỨ HAI - THỨ BẢY) - LỚP {classroom['name']}"
    ws["A3"].font = title_font
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A4:J4")
    ws["A4"] = f"Tuần lễ: Từ ngày {week_days[0]['formatted_date']} đến ngày {week_days[-1]['formatted_date']} | GVCN: {classroom['teacher_name'] or '---'}"
    ws["A4"].font = Font(name="Arial", size=11, italic=True)
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["Thứ", "Ngày", "Tiết", "Môn học", "Tên bài dạy / Nội dung bài học", "Học sinh vắng", "Điểm (thang 10)", "Xếp loại", "Giáo viên dạy", "Nhận xét nề nếp"]
    for c_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=6, column=c_idx)
        cell.value = h
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    current_row = 7
    for wd in week_days:
        d_str = wd['date']
        d_name = wd['day_name']
        start_row_for_day = current_row

        for p in range(1, 6):
            r = grid[d_str][p]
            sub_name = r['subject_name'] if r and r['subject_name'] else ''
            lesson_title = r['lesson_name'] if r and r['lesson_name'] else ''
            absent = r['absent_students'] if r and r['absent_students'] else ''
            score = r['score'] if r and r['score'] is not None else ''
            cls = r['classification'] if r and r['classification'] else ''
            teacher = r['teacher_name'] if r and r['teacher_name'] else ''
            note = r['note'] if r and r['note'] else ''

            ws.cell(row=current_row, column=1, value=d_name)
            ws.cell(row=current_row, column=2, value=wd['formatted_date'])
            ws.cell(row=current_row, column=3, value=f"Tiết {p}")
            ws.cell(row=current_row, column=4, value=sub_name)
            ws.cell(row=current_row, column=5, value=lesson_title)
            ws.cell(row=current_row, column=6, value=absent)
            ws.cell(row=current_row, column=7, value=score)
            ws.cell(row=current_row, column=8, value=cls)
            ws.cell(row=current_row, column=9, value=teacher)
            ws.cell(row=current_row, column=10, value=note)

            for c in range(1, 11):
                cell = ws.cell(row=current_row, column=c)
                cell.font = Font(name="Arial", size=10)
                cell.border = border
                if c in [1, 2, 3, 6, 7, 8]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                if c == 7 and score != '':
                    cell.font = Font(name="Arial", size=10, bold=True, color="006100" if float(score) >= 9.0 else "C00000" if float(score) < 5.0 else "000000")

            current_row += 1

        # Merge Thứ & Ngày cho 5 tiết trong ngày
        ws.merge_cells(start_row=start_row_for_day, start_column=1, end_row=current_row-1, end_column=1)
        ws.merge_cells(start_row=start_row_for_day, start_column=2, end_row=current_row-1, end_column=2)
        ws.cell(row=start_row_for_day, column=1).fill = day_fill
        ws.cell(row=start_row_for_day, column=1).font = day_font
        ws.cell(row=start_row_for_day, column=2).fill = day_fill
        ws.cell(row=start_row_for_day, column=2).font = day_font

    # Dòng tổng kết tuần
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
    summary_cell = ws.cell(row=current_row, column=1)
    summary_cell.value = f"TỔNG KẾT TUẦN: {summary['scored_periods']} tiết dạy | Tiết Tốt: {summary['count_tot']} | Tiết Khá: {summary['count_kha']} | Tiết Trung bình: {summary['count_tb']} | Tiết Yếu: {summary['count_yeu']}"
    summary_cell.font = Font(name="Arial", size=10, bold=True)
    summary_cell.alignment = Alignment(horizontal="left", vertical="center")

    avg_cell = ws.cell(row=current_row, column=7)
    avg_cell.value = f"ĐTB: {summary['avg_score']}"
    avg_cell.font = Font(name="Arial", size=10, bold=True, color="1F4E78")
    avg_cell.alignment = Alignment(horizontal="center", vertical="center")

    tot_cell = ws.cell(row=current_row, column=8)
    tot_cell.value = f"Tổng: {summary['total_score']}"
    tot_cell.font = Font(name="Arial", size=10, bold=True)
    tot_cell.alignment = Alignment(horizontal="center", vertical="center")

    for c in range(1, 11):
        ws.cell(row=current_row, column=c).border = border
        ws.cell(row=current_row, column=c).fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col if cell.row >= 6)
        ws.column_dimensions[col_letter].width = max(min(max_len + 4, 35), 10)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    conn.close()
    return output
