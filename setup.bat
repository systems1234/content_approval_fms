@echo off
echo ========================================
echo TaskFlow CRM - Quick Setup (Windows)
echo ========================================
echo.

echo [1/6] Creating virtual environment...
python -m venv crm_env
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/6] Activating virtual environment...
call crm_env\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [3/6] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install Python dependencies
    pause
    exit /b 1
)

echo [4/6] Installing Node.js dependencies...
call npm install
if errorlevel 1 (
    echo Error: Failed to install Node.js dependencies
    pause
    exit /b 1
)

echo [5/6] Building Tailwind CSS...
call npm run build:css
if errorlevel 1 (
    echo Error: Failed to build Tailwind CSS
    pause
    exit /b 1
)

echo [6/6] Initializing database...
flask db upgrade
if errorlevel 1 (
    echo Warning: Database migration failed. Creating fresh database...
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo   1. Run: python seed_data.py (optional - creates demo users)
echo   2. Run: flask run
echo   3. Open: http://localhost:5000
echo.
echo Demo credentials (after seeding):
echo   Admin:    admin / admin123
echo   Manager:  manager / manager123
echo   Auditor:  auditor / auditor123
echo   Assignee: user / user123
echo.
pause
