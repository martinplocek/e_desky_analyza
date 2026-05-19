@echo off
title STYLGROUP analyza
cd /d "%~dp0"

:: Vytvorit .env (vzdy prepsat, aby byl spravny obsah)
echo EDESKY_API_KEY=R0Mek8f0ePnpOmh9188oFRFNvz6Uq8hW>.env
echo CUZK_WSDP_USER=>>.env
echo CUZK_WSDP_PASS=>>.env

:: Zkusit python primo z PATH
set PYTHON=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :run
)

:: Zkusit py launcher (Microsoft Store Python)
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :run
)

:: Hledat v beznych umisteni Windows
for /d %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python3*"
    "%LOCALAPPDATA%\Programs\Python\Python*"
    "C:\Python3*"
    "C:\Python*"
    "%PROGRAMFILES%\Python3*"
    "%PROGRAMFILES(X86)%\Python3*"
) do (
    if exist "%%D\python.exe" (
        set PYTHON=%%D\python.exe
        goto :run
    )
)

echo.
echo Python neni nalezen. Provedte nasledujici kroky:
echo.
echo 1. Jdete na https://python.org/downloads
echo 2. Kliknete na "Download Python"
echo 3. Spustte instalaci a ZATRHETE "Add Python to PATH"
echo 4. Po instalaci spustte tento soubor znovu
echo.
pause
exit /b 1

:run
echo Pouzivam: %PYTHON%
echo.

"%PYTHON%" -m pip install -r requirements.txt -q
"%PYTHON%" main.py

if exist report.txt (
    notepad report.txt
)

pause
