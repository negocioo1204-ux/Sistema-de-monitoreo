@echo off
cd /d "%~dp0"
echo ============================================
echo  Omada MCP - Centro de Control
echo  Modo: SIMULACION
echo ============================================
echo.
echo  NOTIFICACIONES POR EMAIL:
echo  Para activar, crear archivo monitoring/.env con:
echo    SMTP_HOST=smtp.gmail.com
echo    SMTP_PORT=587
echo    SMTP_USER=redsegura26@gmail.com
echo    SMTP_PASS=zahtbusoycqnfvif
echo    SMTP_TO=negocioo1204@gmail.com
echo    SMTP_USE_TLS=true (o false para SSL/465)
echo    NOTIFY_SEVERITY=warning (opcional: info/warning/critical)
echo    NOTIFY_COOLDOWN=300 (segundos entre correos de misma alerta)
echo.
set SIMULATE=true
echo [1/2] Iniciando servidor FastAPI...
start "Omada-MCP-Server" cmd /c "uvicorn server:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul
echo [2/2] Iniciando dashboard Streamlit...
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0
echo.
pause
