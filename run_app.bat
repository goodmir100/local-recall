@echo off
setlocal
cd /d "%~dp0" || goto :error

echo ===================================
echo      Starting Local Recall...
echo ===================================

:: Check for Python 3.12 or newer on PATH.
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.12+ and add it to PATH.
    pause
    exit /b 1
)
python -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 or newer is required.
    pause
    exit /b 1
)

:: Check if Node.js is available.
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not found in PATH. Please install Node.js 20+ and add it to PATH.
    pause
    exit /b 1
)
node -e "process.exit(Number(process.versions.node.split('.')[0]) < 20 ? 1 : 0)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 20 or newer is required.
    pause
    exit /b 1
)

:: Set up the Python virtual environment if it does not exist.
if not exist "backend\venv\Scripts\python.exe" (
    echo [+] Creating Python virtual environment in backend\venv...
    python -m venv backend\venv || goto :error
    backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :error
)

:: Populate the embedding-model cache once; runtime inference stays offline.
backend\venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', local_files_only=True)" >nul 2>&1
if errorlevel 1 (
    echo [+] Downloading the multilingual embedding model for first-time setup...
    backend\venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" || goto :error
)

:: Install frontend dependencies if needed.
if not exist "frontend\node_modules" (
    echo [+] Installing frontend dependencies via npm...
    pushd frontend || goto :error
    call npm ci || goto :error
    popd
)

echo [+] Launching Backend (FastAPI) and Frontend (Vite)...
start "Local Recall Backend" /D "%~dp0backend" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765"
start "Local Recall Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo Local Recall is running! Open your browser at http://localhost:5173
exit /b 0

:error
echo [ERROR] Setup failed. Check the message above and run this file again.
pause
exit /b 1
