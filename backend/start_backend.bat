@echo off

echo ========================================
echo   Starting PakWheels Backend
echo ========================================

cd /d C:\Projects\PakWheels_VoiceAgent\backend

echo.
echo Starting Docker containers...
docker compose up -d

echo.
echo Checking containers...*
docker compose ps

echo.
echo Backend running at:
echo http://localhost:8000
echo.

pause