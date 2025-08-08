#!/bin/bash

# Stop the Remote MC Press Chatbot Demo

echo "🛑 Stopping Remote MC Press Chatbot Demo..."

# Kill ngrok
pkill -f ngrok && echo "✅ ngrok tunnel stopped"

# Kill backend
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Backend stopped (port 8000)"

# Kill frontend  
lsof -ti:3003 | xargs kill -9 2>/dev/null && echo "✅ Frontend stopped (port 3003)"

# Clean up log files
rm -f ngrok.log 2>/dev/null

echo "✅ Remote demo stopped successfully!"
echo "🔒 Public URL is no longer accessible"