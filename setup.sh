#!/bin/bash

echo "========================================"
echo "TaskFlow CRM - Quick Setup (Linux/Mac)"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "[1/6] Creating virtual environment..."
python3 -m venv crm_env
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create virtual environment${NC}"
    exit 1
fi

echo "[2/6] Activating virtual environment..."
source crm_env/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to activate virtual environment${NC}"
    exit 1
fi

echo "[3/6] Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install Python dependencies${NC}"
    exit 1
fi

echo "[4/6] Installing Node.js dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install Node.js dependencies${NC}"
    exit 1
fi

echo "[5/6] Building Tailwind CSS..."
npm run build:css
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to build Tailwind CSS${NC}"
    exit 1
fi

echo "[6/6] Initializing database..."
flask db upgrade
if [ $? -ne 0 ]; then
    echo "Warning: Database migration failed. Creating fresh database..."
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
fi

echo ""
echo -e "${GREEN}========================================"
echo "Setup completed successfully!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Run: python seed_data.py (optional - creates demo users)"
echo "  2. Run: flask run"
echo "  3. Open: http://localhost:5000"
echo ""
echo "Demo credentials (after seeding):"
echo "  Admin:    admin / admin123"
echo "  Manager:  manager / manager123"
echo "  Auditor:  auditor / auditor123"
echo "  Assignee: user / user123"
echo ""
