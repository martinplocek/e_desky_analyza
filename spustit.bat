@echo off
title STYLGROUP analyza

cd /d "%~dp0"

if not exist .env (
    echo EDESKY_API_KEY=R0Mek8f0ePnpOmh9188oFRFNvz6Uq8hW>.env
    echo CUZK_WSDP_USER=>>.env
    echo CUZK_WSDP_PASS=>>.env
)

python --version >nul 2>&1
if errorlevel 1 (
    echo CHYBA: Python neni nalezen. Nainstalujte z https://python.org
    pause
    exit /b 1
)

pip install -r requirements.txt -q

python main.py

if exist report.txt (
    notepad report.txt
)

pause
