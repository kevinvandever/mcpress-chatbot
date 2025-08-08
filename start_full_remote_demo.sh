#!/bin/bash

# Complete Remote Demo Setup
# Creates public tunnels for both frontend and backend

echo "🌍 Starting Complete Remote MC Press Chatbot Demo..."

# Kill existing processes
echo "🧹 Cleaning up..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3003 | xargs kill -9 2>/dev/null || true
pkill -f ngrok 2>/dev/null || true
sleep 2

# Set environment
export OPENAI_API_KEY="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"

# Start backend
echo "🔧 Starting backend..."
cd /Users/kevinvandever/kev-dev/pdf-chatbot
nohup uvicorn backend.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
sleep 8

# Start backend ngrok tunnel
echo "🌐 Creating backend tunnel..."
nohup ngrok http 8000 --log ngrok_backend.log > /dev/null 2>&1 &
sleep 5

# Get backend URL
BACKEND_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels') and len(data['tunnels']) > 0:
        print(data['tunnels'][0]['public_url'])
    else:
        print('ERROR')
except:
    print('ERROR')
" 2>/dev/null)

if [ "$BACKEND_URL" = "ERROR" ] || [ "$BACKEND_URL" = "" ]; then
    echo "❌ Could not get backend tunnel URL"
    echo "Visit http://localhost:4040 to see ngrok dashboard"
    exit 1
fi

echo "✅ Backend tunnel: $BACKEND_URL"

# Update API config with backend URL
cd /Users/kevinvandever/kev-dev/pdf-chatbot/frontend
cat > config/api.ts << EOF
// API configuration - AUTO-GENERATED for remote demo
export const API_URL = '$BACKEND_URL';
EOF

echo "✅ Updated frontend API config"

# Start frontend
echo "🎨 Starting frontend..."
nohup npm run dev -- --port 3003 > frontend.log 2>&1 &
sleep 10

# Start frontend ngrok tunnel on different port
echo "🌐 Creating frontend tunnel..."
nohup ngrok http 3003 --web-addr 127.0.0.1:4041 > ngrok_frontend.log 2>&1 &
sleep 5

# Get frontend URL
FRONTEND_URL=$(curl -s http://localhost:4041/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels') and len(data['tunnels']) > 0:
        print(data['tunnels'][0]['public_url'])
    else:
        print('ERROR')
except:
    print('ERROR')
" 2>/dev/null)

if [ "$FRONTEND_URL" = "ERROR" ] || [ "$FRONTEND_URL" = "" ]; then
    echo "❌ Could not get frontend tunnel URL"
    echo "Visit http://localhost:4041 to see frontend ngrok dashboard"
    exit 1
fi

echo ""
echo "🎉 COMPLETE REMOTE DEMO IS READY!"
echo ""
echo "📤 Send this URL to your partner:"
echo "   $FRONTEND_URL"
echo ""
echo "🔧 Backend tunnel: $BACKEND_URL"
echo "🎨 Frontend tunnel: $FRONTEND_URL"
echo ""
echo "📊 Monitor:"
echo "   • Backend dashboard: http://localhost:4040"
echo "   • Frontend dashboard: http://localhost:4041"
echo ""
echo "🛑 To stop: ./stop_full_remote_demo.sh"
echo ""

# Save URLs for stop script
echo "$FRONTEND_URL" > .frontend_url
echo "$BACKEND_URL" > .backend_url

echo "Demo ready! Your partner can access from anywhere in the world."