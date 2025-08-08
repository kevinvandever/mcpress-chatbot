#!/bin/bash

echo "🚀 Starting PDF Chatbot servers..."

# Start backend server
echo "Starting backend server..."
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 5

# Start frontend server
echo "Starting frontend server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Servers started!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "To stop servers, run: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop watching logs..."

# Keep script running to show logs
wait