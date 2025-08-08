#!/bin/bash

# Dual Tunnel Setup for MC Press Chatbot
# Creates separate tunnels for frontend and backend

show_usage() {
    echo "Usage: ./dual_tunnel.sh [start|stop|status]"
    echo ""
    echo "Creates two tunnels:"
    echo "  - Frontend (port 3003) -> mcpress-app.loca.lt"  
    echo "  - Backend (port 8000) -> mcpress-api.loca.lt"
}

start_tunnels() {
    echo "🚀 Starting dual tunnels for MC Press Chatbot..."
    
    # Check if both services are running
    if ! lsof -ti:3003 > /dev/null 2>&1; then
        echo "❌ Frontend not running on port 3003!"
        echo "Run: cd frontend && npm run dev"
        exit 1
    fi
    
    if ! lsof -ti:8000 > /dev/null 2>&1; then
        echo "❌ Backend not running on port 8000!"
        echo "Run: cd backend && python main.py"
        exit 1
    fi
    
    # Kill existing tunnels
    pkill -f "lt --port 3003" 2>/dev/null
    pkill -f "lt --port 8000" 2>/dev/null
    sleep 2
    
    # Start frontend tunnel
    echo "⚡ Starting frontend tunnel..."
    lt --port 3003 --subdomain mcpress-app > frontend_tunnel.log 2>&1 &
    sleep 2
    
    # Start backend tunnel  
    echo "⚡ Starting backend tunnel..."
    lt --port 8000 --subdomain mcpress-api > backend_tunnel.log 2>&1 &
    sleep 3
    
    # Get current IP
    IP=$(curl -4 -s ifconfig.me)
    
    # Update frontend API config
    export NEXT_PUBLIC_API_URL="https://mcpress-api.loca.lt"
    
    echo "✅ Dual tunnels started!"
    echo ""
    echo "📋 Share with your partner:"
    echo "   Frontend: https://mcpress-app.loca.lt"
    echo "   Password: $IP"
    echo ""
    echo "🔧 Backend API: https://mcpress-api.loca.lt"
    echo "   Password: $IP"
    echo ""
    echo "💡 Make sure to set: export NEXT_PUBLIC_API_URL=https://mcpress-api.loca.lt"
    echo "💡 Then restart frontend: cd frontend && npm run dev"
}

stop_tunnels() {
    echo "🛑 Stopping all tunnels..."
    pkill -f "lt --port 3003"
    pkill -f "lt --port 8000"
    rm -f frontend_tunnel.log backend_tunnel.log
    echo "✅ All tunnels stopped!"
    echo "💡 Reset API config: unset NEXT_PUBLIC_API_URL"
}

check_status() {
    IP=$(curl -4 -s ifconfig.me)
    
    if pgrep -f "lt --port 3003" > /dev/null; then
        echo "✅ Frontend tunnel RUNNING: https://mcpress-app.loca.lt (password: $IP)"
    else
        echo "❌ Frontend tunnel NOT running"
    fi
    
    if pgrep -f "lt --port 8000" > /dev/null; then
        echo "✅ Backend tunnel RUNNING: https://mcpress-api.loca.lt (password: $IP)"
    else
        echo "❌ Backend tunnel NOT running"
    fi
    
    if lsof -ti:3003 > /dev/null 2>&1; then
        echo "✅ Frontend service running on port 3003"
    else
        echo "❌ Frontend service NOT running"
    fi
    
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo "✅ Backend service running on port 8000"
    else
        echo "❌ Backend service NOT running"
    fi
    
    echo ""
    echo "Current API URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
}

case "$1" in
    start)
        start_tunnels
        ;;
    stop)
        stop_tunnels
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac