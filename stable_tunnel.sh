#!/bin/bash

echo "🚀 Starting stable tunnel for MC Press Chatbot..."

while true; do
    echo "⚡ Starting ngrok tunnel..."
    ngrok http 3003 --log=stdout 2>&1 | tee ngrok.log &
    NGROK_PID=$!
    
    # Wait for tunnel to establish
    sleep 5
    
    # Get the URL
    URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ ! -z "$URL" ]; then
        echo "✅ Tunnel active: $URL"
        echo "📋 Share this URL with your partner: $URL"
        echo "🔄 Monitoring tunnel... (Ctrl+C to stop)"
        
        # Monitor ngrok process
        wait $NGROK_PID
        echo "⚠️  Tunnel died, restarting in 3 seconds..."
        sleep 3
    else
        echo "❌ Failed to get tunnel URL, retrying..."
        kill $NGROK_PID 2>/dev/null
        sleep 5
    fi
done