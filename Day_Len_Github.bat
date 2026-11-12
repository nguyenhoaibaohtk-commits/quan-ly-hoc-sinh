@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Đẩy Code Lên GitHub - Quản Lý Học Sinh THPT
echo ======================================================================
echo          ĐẨY MÃ NGUỒN QUẢN LÝ HỌC SINH LÊN GITHUB ĐỂ LÊN RENDER
echo ======================================================================
echo.
echo * HƯỚNG DẪN:
echo   1. Truy cập https://github.com/new để tạo một Repository mới (đặt tên: quan-ly-hoc-sinh)
echo   2. Dán link GitHub Repository của bạn vào bên dưới.
echo.

set DEFAULT_URL=https://github.com/nguyenhoaibaohtk-commits/quan-ly-hoc-sinh.git
set /p REPO_URL="Nhập link GitHub (Nhấn Enter để dùng mặc định: %DEFAULT_URL%): "
if "%REPO_URL%"=="" set REPO_URL=%DEFAULT_URL%

echo.
echo Đang kết nối tới: %REPO_URL%
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
git add .
git commit -m "Cap nhat ung dung Quan Ly Hoc Sinh va So Dau Bai" 2>nul

echo.
echo Đang đẩy mã nguồn lên GitHub...
git push -u origin main

echo.
if %errorlevel% equ 0 (
    echo ======================================================================
    echo   [THÀNH CÔNG] Đã đẩy code lên GitHub thành công!
    echo   Bây giờ bạn chỉ cần vào https://dashboard.render.com bấm:
    echo   "New +" -> "Web Service" -> Chọn repository "quan-ly-hoc-sinh"
    echo   -> Bấm "Deploy Web Service" là xong!
    echo ======================================================================
) else (
    echo ======================================================================
    echo   [LƯU Ý] Nếu đẩy thất bại:
    echo   1. Hãy chắc chắn bạn đã tạo kho lưu trữ trên https://github.com/new
    echo   2. Kiểm tra lại đường dẫn link kho lưu trữ đã nhập đúng chưa.
    echo   3. Đăng nhập tài khoản GitHub nếu có cửa sổ yêu cầu hiện ra.
    echo ======================================================================
)
echo.
pause
