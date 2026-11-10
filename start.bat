@echo off
cd /d "%~dp0"
if not exist .env copy .env.example .env
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto fail
py -3 main.py
pause
exit /b
:fail
echo Khong the cai thu vien. Kiem tra Python va Internet.
pause
