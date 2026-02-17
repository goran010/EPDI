#!/bin/bash

# FIDIT AI Assistant - Run Script

echo " FIDIT AI Assistant - Starting Application"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python3; then
    echo " Python 3 is not installed!"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo " Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo " Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo " Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "  Please edit .env file and add your API keys!"
fi

# Initialize database
echo "  Initializing database..."
python src/database/database.py

# Ask if user wants demo data
read -p " Do you want to create demo data? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo " Creating demo data..."
    python src/utils/create_demo_data.py
fi

# Start services
echo ""
echo " Starting services..."
echo "=============================================="

# Start backend in background
echo "  Starting FastAPI backend..."
python src/api/main.py &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
sleep 3

# Start frontend
echo "▶️  Starting Streamlit frontend..."
streamlit run frontend/app.py &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "=============================================="
echo " Application started successfully!"
echo "=============================================="
echo ""
echo " API:        http://localhost:8000"
echo " API Docs:   http://localhost:8000/docs"
echo " Dashboard:  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=============================================="

# Function to cleanup on exit
cleanup() {
    echo ""
    echo " Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "  Services stopped"
    exit 0
}

# Set trap to catch Ctrl+C
trap cleanup INT TERM

# Wait for processes
wait
