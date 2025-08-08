#!/bin/bash

# Simple Local Development Startup
# No proxy, no tunnels - just backend + frontend

echo "🚀 Starting MC Press Chatbot - Simple Local Development"

# Check if ports are in use and kill if necessary
echo "🔧 Checking ports..."
for port in 8000 3000; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠️  Port $port is in use. Stopping existing process..."
        lsof -ti:$port | xargs kill
        sleep 2
    fi
done

# Start backend
echo "🔧 Starting backend (port 8000)..."
DATA_DIR="/Users/kevinvandever/kev-dev/pdf-chatbot/data" \
PYTHONPATH="/Users/kevinvandever/kev-dev/pdf-chatbot" \
python backend/main.py > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend started successfully"
        break
    fi
    sleep 1
done

# Start frontend
echo "🎨 Starting frontend (port 3000)..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend
echo "⏳ Waiting for frontend..."
sleep 8

echo ""
echo "✅ Local development started successfully!"
echo ""
echo "🖥️  Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 Health Check: http://localhost:8000/health"
echo ""
echo "🔧 Process IDs:"
echo "   Backend: $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo ""
echo "📊 Logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop: pkill -f 'python backend/main.py' && pkill -f 'next dev'"