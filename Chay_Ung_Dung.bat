@echo off
chcp 65001 >nul
title Hệ Thống Quản Lý Học Sinh & Sổ Đầu Bài
echo ================================================================
echo        KHỞI ĐỘNG HỆ THỐNG QUẢN LÝ HỌC SINH (SCHOOLFLOW)
echo ================================================================
echo.
echo [1/3] Đang kiểm tra cơ sở dữ liệu và dữ liệu sổ đầu bài...
python database.py
echo.
echo [2/3] Địa chỉ IP mạng nội bộ của máy bạn:
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "0.0.0.0.*0.0.0.0"') do (
    set LOCAL_IP=%%a
)
echo       -> Dành cho máy này:          http://127.0.0.1:5000
echo       -> Dành cho đồng nghiệp/Wi-Fi: http://%LOCAL_IP%:5000
echo.
echo [3/3] Đang khởi động máy chủ Flask (host: 0.0.0.0:5000)...
echo       Trình duyệt sẽ tự động mở trong giây lát...
echo       (Nhấn Ctrl+C để dừng ứng dụng)
echo ================================================================
echo.

start "" "http://127.0.0.1:5000"
python app.py

pause
