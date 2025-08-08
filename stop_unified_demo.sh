#!/bin/bash

# Stop Unified Demo

echo "🛑 Stopping MC Press Chatbot - Unified Demo"

# Kill processes by port
echo "⏹️  Stopping backend (port 8000)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Backend stopped"

echo "⏹️  Stopping frontend (port 3001)..."  
lsof -ti:3001 | xargs kill -9 2>/dev/null && echo "✅ Frontend stopped"

echo "⏹️  Stopping proxy (port 9000)..."
lsof -ti:9000 | xargs kill -9 2>/dev/null && echo "✅ Proxy stopped"

echo "⏹️  Stopping tunnel..."
pkill -f "lt --port 9000" && echo "✅ Tunnel stopped"

# Clean up log files
echo "🧹 Cleaning up logs..."
rm -f backend.log frontend.log proxy.log tunnel.log

echo ""
echo "✅ All services stopped!"
echo "🔒 Tunnel URL is no longer accessible"