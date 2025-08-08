#!/bin/bash

# MC Press Chatbot Demo Startup Script
# This script starts both backend and frontend for demo purposes

echo "🚀 Starting MC Press Chatbot Demo..."

# Get local IP address for network access
LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
echo "📍 Local IP: $LOCAL_IP"

# Set environment variables
export OPENAI_API_KEY="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"

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3003 | xargs kill -9 2>/dev/null || true
sleep 2

# Start backend
echo "🔧 Starting backend on port 8000..."
cd /Users/kevinvandever/kev-dev/pdf-chatbot
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 5

# Start frontend
echo "🎨 Starting frontend on port 3003..."
cd /Users/kevinvandever/kev-dev/pdf-chatbot/frontend
nohup npm run dev -- --port 3003 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5

echo ""
echo "✅ MC Press Chatbot is running!"
echo ""
echo "📱 Access from this computer:"
echo "   http://localhost:3003"
echo ""
echo "📱 Access from other devices on your network:"
echo "   http://$LOCAL_IP:3003"
echo ""
echo "🛑 To stop the demo, run: ./stop_demo.sh"
echo ""
echo "📊 Logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend/frontend.log"
echo ""

# Save PIDs for stop script
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

echo "Demo is ready! Press Ctrl+C to exit (servers will keep running in background)"