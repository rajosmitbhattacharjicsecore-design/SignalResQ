@echo off
setlocal
cd /d "%~dp0"
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do set IP=%%A
set IP=%IP: =%
if "%IP%"=="" set IP=127.0.0.1
set SIGNALRESCUE_HOST=0.0.0.0
set SIGNALRESCUE_PORT=8765
cls
echo ==============================================
echo       SIGNALRESCUE REAL DEVICE GATEWAY
echo ==============================================
echo Gateway:   http://%IP%:8765
echo API state: http://%IP%:8765/api/state
echo Pair URL:  http://%IP%:8765/api/pair
echo.
echo Keep this window open while testing phones.
echo ==============================================
python server.py
pause
