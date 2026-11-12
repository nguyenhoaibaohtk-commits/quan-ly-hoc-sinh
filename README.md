# HỆ THỐNG QUẢN LÝ HỌC SINH TRƯỜNG HỌC (SCHOOLFLOW)

Ứng dụng web nội bộ chuyên nghiệp dành cho trường học, được xây dựng bằng **Python Flask**, **SQLite**, **Bootstrap 5** và **Excel Service**.

---

## 🌟 TÍNH NĂNG CHÍNH

1. **Quản lý Hồ sơ Học sinh**:
   - Thêm, sửa, xóa, tìm kiếm học sinh nhanh theo tên, mã HS, số điện thoại.
   - Lọc học sinh theo Khối (10, 11, 12), Lớp học, Giới tính, Trạng thái (Đang học, Chuyển trường, Thôi học, Tốt nghiệp).
   - Trang hồ sơ cá nhân chi tiết: thông tin liên hệ gia đình, sổ điểm các môn, chuyên cần.

2. **Quản lý Lớp học & Niên khóa**:
   - Quản lý danh sách lớp theo khối, giáo viên chủ nhiệm, phòng học, thống kê sĩ số nam/nữ.
   - Thống kê tỷ lệ học lực từng lớp.

3. **Sổ Điểm & Đánh giá (Chuẩn TT 22/2021/TT-BGDĐT)**:
   - Quản lý điểm ĐĐGtx (TX1, TX2, TX3, TX4), ĐĐGgk (hệ số 2), ĐĐGck (hệ số 3).
   - Tự động tính Điểm trung bình môn học kỳ và Điểm trung bình các môn (ĐTBhk).
   - Tự động xếp loại học lực: **Tốt**, **Khá**, **Đạt**, **Chưa đạt**.
   - **Giao diện nhập điểm nhanh (Grid view)**: Nhập điểm trực tiếp như bảng tính Excel, tự động tính điểm trung bình thời gian thực (realtime) bằng JavaScript.

4. **Điểm danh & Chuyên cần**:
   - Điểm danh theo ngày cho từng lớp với 1 chạm: **Có mặt (P)**, **Có phép (CP)**, **Không phép (KP)**, **Đi trễ (T)**.
   - Nút **"Tất cả có mặt"** để điểm danh nhanh chỉ trong vài giây.
   - Báo cáo tổng hợp chuyên cần theo tháng của cả lớp.

5. **Nhập / Xuất Excel & In ấn Học bạ**:
   - Tải file Excel mẫu chuẩn (.xlsx) để nhập danh sách học sinh.
   - Tự động import danh sách học sinh từ file Excel vào lớp.
   - Xuất danh sách học sinh theo lớp ra file Excel định dạng đẹp.
   - Xuất bảng điểm môn học ra file Excel.
   - In **Phiếu báo điểm / Sổ liên lạc** cá nhân chuẩn khổ giấy in A4 (Print to PDF).

6. **Sổ Đầu Bài & Chấm Điểm Tiết Học (Thứ Hai - Thứ Bảy)**:
   - Theo dõi từng tiết học (Tiết 1 đến Tiết 5) trong suốt 6 ngày trong tuần: **từ Thứ Hai đến Thứ Bảy** cho tất cả 33 lớp (10A1-10A11, 11B1-11B11, 12C1-12C11).
   - **Chấm điểm tiết học theo thang điểm 10**:
     - *9.0 - 10.0*: Tiết Tốt (A)
     - *7.0 - 8.9*: Tiết Khá (B)
     - *5.0 - 6.9*: Tiết Trung bình (C)
     - *Dưới 5.0*: Tiết Yếu (D)
   - Lưu tên bài dạy, giáo viên giảng dạy, học sinh vắng trong tiết, nhận xét nề nếp.
   - Tự động tính điểm trung bình tiết học, tổng điểm tuần của từng lớp.
   - **Bảng xếp hạng thi đua tuần giữa 33 lớp**: Trao cúp Vàng 🥇, Bạc 🥈, Đồng 🥉 cho các lớp dẫn đầu thi đua nề nếp.
   - Xuất Sổ Đầu Bài tuần ra file Excel (.xlsx) chuẩn.

7. **Danh mục Môn học & Cài đặt trường**:
   - Quản lý danh mục môn học, hệ số tính điểm, số tiết/năm.
   - Cài đặt thông tin trường (Tên trường, Hiệu trưởng, Địa chỉ, Số điện thoại).
   - Quản lý năm học và học kỳ đang áp dụng.

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY 1-CLICK

Chỉ cần nhấp đúp vào file:
```
Chay_Ung_Dung.bat
```
Hệ thống sẽ tự khởi tạo cơ sở dữ liệu (nếu chưa có) và tự động mở trình duyệt web tại địa chỉ:
```
http://127.0.0.1:5000
```

Hoặc chạy bằng dòng lệnh:
```bash
cd "e:\lam de\quan_ly_hoc_sinh"
python app.py
```
