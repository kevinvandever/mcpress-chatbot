#!/bin/bash

# Stop the MC Press Chatbot Demo

echo "🛑 Stopping MC Press Chatbot Demo..."

# Kill backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    kill -9 $BACKEND_PID 2>/dev/null && echo "✅ Backend stopped (PID: $BACKEND_PID)"
    rm .backend.pid
else
    # Fallback: kill by port
    lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Backend stopped (port 8000)"
fi

# Kill frontend
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    kill -9 $FRONTEND_PID 2>/dev/null && echo "✅ Frontend stopped (PID: $FRONTEND_PID)"
    rm .frontend.pid
else
    # Fallback: kill by port
    lsof -ti:3003 | xargs kill -9 2>/dev/null && echo "✅ Frontend stopped (port 3003)"
fi

echo "✅ Demo stopped successfully!"