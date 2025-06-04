@echo off
REM Change directory to the project root
cd /d C:\Users\ADMIN\Documents\GitHub\courseware_autogen

REM Start Docker Desktop if not running
Tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I /N "Docker Desktop.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting 60 seconds for Docker Desktop to start...
    timeout /t 60 >nul
)

REM Build and start the container using docker compose
docker-compose up --build

pause 