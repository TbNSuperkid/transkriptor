@echo off
title Transkriptor EXE Builder
color 0A

echo.
echo =============================================
echo     🎙️ TRANSKRIPTOR EXE BUILDER
echo =============================================
echo.

echo [1/5] Installiere PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo FEHLER: PyInstaller Installation fehlgeschlagen
    pause
    exit /b 1
)

echo.
echo [2/5] Erstelle Output-Ordner...
if not exist "output" mkdir output

echo.
echo [3/5] Lade Whisper-Modelle herunter...
echo (Das kann einige Minuten dauern...)
python -c "import whisper; [whisper.load_model(m) for m in ['tiny', 'base', 'small', 'medium', 'large']]"

echo.
echo [4/5] Lösche alte Build-Dateien...
if exist "exe_build" rmdir /s /q "exe_build"
if exist "temp_build" rmdir /s /q "temp_build"
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [5/5] Erstelle EXE-Datei...
echo (Das kann 10-20 Minuten dauern - bitte warten...)
echo.

:: Finde Python-Script automatisch
for %%f in (*.py) do (
    if not "%%f"=="build_exe.py" (
        set SCRIPT=%%f
        goto :found
    )
)

:found
echo Script gefunden: %SCRIPT%
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Transkriptor" ^
    --add-data "output;output" ^
    --hidden-import=whisper ^
    --hidden-import=customtkinter ^
    --hidden-import=tkinter ^
    --hidden-import=torch ^
    --hidden-import=torchaudio ^
    --hidden-import=numpy ^
    --hidden-import=librosa ^
    --collect-all=whisper ^
    --collect-all=customtkinter ^
    --collect-all=torch ^
    --collect-all=torchaudio ^
    --collect-submodules=whisper ^
    --distpath="./exe_build" ^
    --workpath="./temp_build" ^
    --clean ^
    --noconfirm ^
    %SCRIPT%

if %errorlevel% equ 0 (
    echo.
    echo ✅ BUILD ERFOLGREICH!
    echo 📁 EXE-Datei: ./exe_build/Transkriptor.exe
    echo.
    
    :: Dateigröße anzeigen
    for %%A in ("exe_build\Transkriptor.exe") do (
        set /a size=%%~zA/1024/1024
        echo 📊 Dateigröße: !size! MB
    )
    
    echo.
    echo 🚀 Öffne Build-Ordner...
    start explorer "exe_build"
) else (
    echo.
    echo ❌ BUILD FEHLGESCHLAGEN!
    echo Überprüfe die Fehlermeldungen oben.
)

echo.
pause