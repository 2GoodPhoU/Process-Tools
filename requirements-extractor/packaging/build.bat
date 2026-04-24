@echo off
REM =====================================================================
REM Build DocumentDataExtractor.exe on Windows.
REM
REM Prereqs (run once per machine, from the requirements-extractor folder):
REM     python -m venv .venv
REM     .venv\Scripts\activate.bat
REM     pip install -r requirements.txt
REM     pip install -r requirements-optional.txt
REM     pip install -r packaging\build-requirements.txt
REM     pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
REM
REM (The pinned model-wheel URL is preferred over `python -m spacy
REM download` so the build is reproducible and does not depend on
REM spaCy's download CLI being able to reach the internet.  See the
REM "Packaging to a Windows .exe" section of README.md.)
REM
REM Then from the requirements-extractor folder:
REM     packaging\build.bat
REM
REM Output:
REM     dist\DocumentDataExtractor.exe
REM =====================================================================

setlocal
cd /d "%~dp0.."

echo === Cleaning previous build artifacts ===
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo === Running PyInstaller ===
pyinstaller packaging\DocumentDataExtractor.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo BUILD FAILED. See PyInstaller output above.
    exit /b 1
)

echo.
echo === Build complete ===
echo Executable: %CD%\dist\DocumentDataExtractor.exe
echo.
echo Tip: the first launch unpacks a few MB into %%TEMP%%, so it can take
echo a couple of seconds.  Subsequent launches are faster.
endlocal
