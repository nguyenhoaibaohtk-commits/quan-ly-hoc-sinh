@echo off
chcp 65001 >nul
title Tạo Link Chia Sẻ Internet Cho Ứng Dụng
echo ================================================================
echo       TẠO ĐƯỜNG LINK CHIA SẺ RA INTERNET CHO MỌI NGƯỜI
echo ================================================================
echo.
echo * Lưu ý: Hãy đảm bảo bạn đã mở app bằng file "Chay_Ung_Dung.bat" trước!
echo.
echo Đang kết nối và tạo đường link công khai an toàn (HTTPS)...
echo Bạn có thể gửi đường link này cho bất kỳ ai để truy cập thử từ xa.
echo (Nhấn Ctrl+C để đóng link khi không muốn chia sẻ nữa)
echo ================================================================
echo.

ssh -p 443 -R0:localhost:5000 -o StrictHostKeyChecking=no a.pinggy.io

pause
