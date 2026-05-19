@echo off
chcp 65001 >nul
title STYLGROUP – Analýza stavebních řízení

echo ============================================================
echo   STYLGROUP – Analýza stavebních řízení v k.ú. Kukleny
echo ============================================================
echo.

:: Přejít do složky s tímto souborem
cd /d "%~dp0"

:: Vytvořit .env s API klíčem (pokud ještě neexistuje)
if not exist .env (
    echo Vytvářím konfigurační soubor .env...
    echo EDESKY_API_KEY=R0Mek8f0ePnpOmh9188oFRFNvz6Uq8hW> .env
    echo CUZK_WSDP_USER=>> .env
    echo CUZK_WSDP_PASS=>> .env
    echo Hotovo.
    echo.
)

:: Zkontrolovat Python
python --version >nul 2>&1
if errorlevel 1 (
    echo CHYBA: Python není nainstalován nebo není v PATH.
    echo Stáhněte ho z https://python.org a při instalaci
    echo zaškrtněte "Add Python to PATH".
    pause
    exit /b 1
)

:: Nainstalovat závislosti
echo Instaluji potřebné knihovny (jen při prvním spuštění)...
pip install -r requirements.txt -q
echo.

:: Spustit analýzu
echo Spouštím analýzu – prosím čekejte (2–5 minut)...
echo ============================================================
echo.
python main.py

echo.
echo ============================================================
echo Hotovo! Report byl uložen do souboru report.txt
echo Otevírám report...
echo ============================================================
echo.

:: Otevřít report v Poznámkovém bloku
if exist report.txt (
    notepad report.txt
) else (
    echo Soubor report.txt nebyl vytvořen – zkontrolujte chyby výše.
)

pause
