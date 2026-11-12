@echo off
chcp 65001 >nul
cd /d "%~dp0"
title He Thong Quan Ly Hoc Sinh va So Dau Bai THPT

echo ================================================================
echo        KHOI DONG HE THONG QUAN LY HOC SINH (SCHOOLFLOW)
echo ================================================================
echo.
echo [*] Dang kiem tra co so du lieu...
python database.py
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the ket noi co so du lieu Python!
    echo Vui long kiem tra lai moi truong Python tren may.
    pause
    exit /b 1
)

echo.
echo [*] Dang khoi dong may chu ung dung...
echo [*] Trinh duyet se tu dong mo ngay khi may chu san sang...
echo.
echo ================================================================
echo.

python app.py

if %errorlevel% neq 0 (
    echo.
    echo ================================================================
    echo [LOI] Ung dung da dung lai voi ma loi: %errorlevel%
    echo ================================================================
    pause
)
