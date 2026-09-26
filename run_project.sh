#!/bin/bash

# Check if uv is installed (it manages Python for the backend)
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. See https://docs.astral.sh/uv/ to install it."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install it before running this script."
    exit 1
fi

# Start Postgres
echo "Starting Postgres..."
docker compose up -d

# Set up the backend
echo "Setting up the backend..."
cd backend

# Install backend dependencies from uv.lock
echo "Installing backend dependencies..."
uv sync

# Start backend server in the background
echo "Starting backend server..."
uv run uvicorn app.main:app --reload &
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