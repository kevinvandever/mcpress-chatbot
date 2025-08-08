#!/bin/bash

# Unified Demo Startup Script
# Starts backend, frontend, proxy, and tunnel

echo "🚀 Starting MC Press Chatbot - Unified Demo"

# Check if required ports are free
for port in 8000 3001 9000; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠️  Port $port is in use. Stopping existing process..."
        lsof -ti:$port | xargs kill
        sleep 2
    fi
done

# Start backend
echo "🔧 Starting backend (port 8000)..."
DATA_DIR=/Users/kevinvandever/kev-dev/pdf-chatbot/data PYTHONPATH=/Users/kevinvandever/kev-dev/pdf-chatbot python backend/main.py > backend.log 2>&1 &
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
echo "🎨 Starting frontend (port 3001)..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend..."
sleep 8

# Start proxy
echo "🔄 Starting proxy server (port 9000)..."
node proxy_server.js > proxy.log 2>&1 &
PROXY_PID=$!

# Wait for proxy to start
sleep 3

# Start tunnel
echo "🌐 Creating tunnel..."
lt --port 9000 --subdomain mcpress-unified > tunnel.log 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel to establish
sleep 5

# Get current IP
IP=$(curl -4 -s ifconfig.me 2>/dev/null || echo "unknown")

echo ""
echo "✅ Unified demo started successfully!"
echo ""
echo "📋 Share with your partner:"
echo "   URL: https://mcpress-unified.loca.lt"
echo "   Password: $IP"
echo ""
echo "🔧 Process IDs:"
echo "   Backend: $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"  
echo "   Proxy: $PROXY_PID"
echo "   Tunnel: $TUNNEL_PID"
echo ""
echo "📊 Logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo "   Proxy: tail -f proxy.log"
echo "   Tunnel: tail -f tunnel.log"
echo ""
echo "🛑 To stop: ./stop_unified_demo.sh"