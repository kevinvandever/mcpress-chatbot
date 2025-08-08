#!/bin/bash

# MC Press Chatbot Remote Demo Script
# This creates a public URL your partner can access from anywhere

echo "🌍 Starting MC Press Chatbot for Remote Demo..."

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3003 | xargs kill -9 2>/dev/null || true
pkill -f ngrok 2>/dev/null || true
sleep 2

# Set environment variables
export OPENAI_API_KEY="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"

# Start backend
echo "🔧 Starting backend on port 8000..."
cd /Users/kevinvandever/kev-dev/pdf-chatbot
nohup uvicorn backend.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
echo "   Backend starting..."

# Start frontend  
echo "🎨 Starting frontend on port 3003..."
cd /Users/kevinvandever/kev-dev/pdf-chatbot/frontend
nohup npm run dev -- --port 3003 > frontend.log 2>&1 &
echo "   Frontend starting..."

# Wait for services to start
echo "⏳ Waiting for services to start (15 seconds)..."
sleep 15

# Test if services are running
echo "🔍 Checking services..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend failed to start"
    exit 1
fi

if curl -s http://localhost:3003/ > /dev/null; then
    echo "   ✅ Frontend is running"
else
    echo "   ❌ Frontend failed to start"
    exit 1
fi

# Start ngrok tunnel
echo "🌐 Creating public tunnel with ngrok..."
echo "   This may take a moment..."

# Start ngrok in background and capture the URL
nohup ngrok http 3003 > ngrok.log 2>&1 &
sleep 5

# Try to get the public URL from ngrok API
echo "📡 Getting public URL..."
sleep 3

# Get the ngrok URL from the API
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['tunnels']:
        print(data['tunnels'][0]['public_url'])
    else:
        print('No tunnels found')
except:
    print('Error getting URL')
" 2>/dev/null)

if [ "$PUBLIC_URL" != "" ] && [ "$PUBLIC_URL" != "No tunnels found" ] && [ "$PUBLIC_URL" != "Error getting URL" ]; then
    echo ""
    echo "🎉 SUCCESS! Your remote demo is ready!"
    echo ""
    echo "📤 Send this URL to your partner:"
    echo "   $PUBLIC_URL"
    echo ""
    echo "📱 Your partner can access it from anywhere in the world!"
    echo ""
    echo "📊 Monitor:"
    echo "   • ngrok dashboard: http://localhost:4040"
    echo "   • Backend logs: tail -f backend.log" 
    echo "   • Frontend logs: tail -f frontend/frontend.log"
    echo ""
    echo "🛑 To stop: ./stop_remote_demo.sh"
    echo ""
else
    echo ""
    echo "⚠️  Could not automatically get ngrok URL"
    echo ""
    echo "📋 Manual steps:"
    echo "   1. Visit http://localhost:4040 in your browser"
    echo "   2. Copy the 'https://*.ngrok.io' URL"
    echo "   3. Send that URL to your partner"
    echo ""
fi

echo "🏃‍♂️ Demo is running! Press Ctrl+C to exit (services continue in background)"

# Keep script running
while true; do
    sleep 300  # Check every 5 minutes
    if ! pgrep -f "ngrok" > /dev/null; then
        echo "⚠️  ngrok tunnel stopped, restarting..."
        nohup ngrok http 3003 > ngrok.log 2>&1 &
    fi
done