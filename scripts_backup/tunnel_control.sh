#!/bin/bash

# MC Press Chatbot - Tunnel Control Script

show_usage() {
    echo "Usage: ./tunnel_control.sh [start|stop|restart|status]"
    echo ""
    echo "Commands:"
    echo "  start   - Start the tunnel"
    echo "  stop    - Stop the tunnel"
    echo "  restart - Restart the tunnel"
    echo "  status  - Check tunnel status"
}

start_tunnel() {
    echo "🚀 Starting MC Press Chatbot tunnel..."
    
    # Check if frontend is running
    if ! lsof -ti:3003 > /dev/null 2>&1; then
        echo "❌ Frontend not running on port 3003!"
        echo "Run: cd frontend && npm run dev"
        exit 1
    fi
    
    # Kill any existing tunnel
    pkill -f "lt --port 3003" 2>/dev/null
    sleep 2
    
    # Start new tunnel
    lt --port 3003 --subdomain mcpress-stable > tunnel.log 2>&1 &
    echo "⏳ Starting tunnel..."
    sleep 3
    
    # Get current IP
    IP=$(curl -4 -s ifconfig.me)
    
    echo "✅ Tunnel started!"
    echo "📋 Share with your partner:"
    echo "   URL: https://mcpress-stable.loca.lt"
    echo "   Password: $IP"
    echo ""
    echo "💡 Tunnel logs saved to: tunnel.log"
}

stop_tunnel() {
    echo "🛑 Stopping tunnel..."
    pkill -f "lt --port 3003"
    rm -f tunnel.log
    echo "✅ Tunnel stopped!"
}

restart_tunnel() {
    stop_tunnel
    sleep 2
    start_tunnel
}

check_status() {
    if pgrep -f "lt --port 3003" > /dev/null; then
        IP=$(curl -4 -s ifconfig.me)
        echo "✅ Tunnel is RUNNING"
        echo "   URL: https://mcpress-stable.loca.lt"
        echo "   Password: $IP"
    else
        echo "❌ Tunnel is NOT running"
    fi
    
    if lsof -ti:3003 > /dev/null 2>&1; then
        echo "✅ Frontend is running on port 3003"
    else
        echo "❌ Frontend is NOT running on port 3003"
    fi
}

case "$1" in
    start)
        start_tunnel
        ;;
    stop)
        stop_tunnel
        ;;
    restart)
        restart_tunnel
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac