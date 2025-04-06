#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it before running this script."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install it before running this script."
    exit 1
fi

# Set up the backend
echo "Setting up the backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
pip install -r requirements.txt

# Start backend server in the background
echo "Starting backend server..."
uvicorn app.main:app --reload &
BACKEND_PID=$!

# Go back to root directory
cd ..

# Set up the frontend
echo "Setting up the frontend..."
cd frontend

# Install frontend dependencies
echo "Installing frontend dependencies..."
npm install

# Start frontend server
echo "Starting frontend server..."
npm start &
FRONTEND_PID=$!

echo ""
echo "=================================================="
echo "Memoir AI is now running!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "=================================================="
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for user to press Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait 