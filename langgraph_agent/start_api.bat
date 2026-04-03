@echo off
REM Start Pal 3D Agent API Server

echo Starting Pal 3D Agent API Server...
echo API will be available at http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found. Creating from .env.example...
    copy .env.example .env
    echo Please edit .env file and add your API keys
)

REM Start the API server
python api_server.py

pause
