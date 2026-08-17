@echo off
setlocal
cd /d "%~dp0.."
set /p PYTHON_EXE=< "%~dp0grace-python-path.txt"
start "G.R.A.C.E. HTTP" /b "%PYTHON_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 1>> "logs\grace-http.log" 2>> "logs\grace-http.error.log"
