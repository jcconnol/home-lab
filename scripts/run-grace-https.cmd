@echo off
setlocal
cd /d "%~dp0.."
set /p PYTHON_EXE=< "%~dp0grace-python-path.txt"
start "G.R.A.C.E. HTTPS" /b "%PYTHON_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile .certs\grace-server-key.pem --ssl-certfile .certs\grace-server.crt 1>> "logs\grace-https.log" 2>> "logs\grace-https.error.log"
