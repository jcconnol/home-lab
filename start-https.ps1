$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".certs\grace-ca.crt") -or -not (Test-Path ".certs\grace-server.crt") -or -not (Test-Path ".certs\grace-server-key.pem")) {
    py scripts\create_https_cert.py
}

py -m uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile .certs\grace-server-key.pem --ssl-certfile .certs\grace-server.crt
