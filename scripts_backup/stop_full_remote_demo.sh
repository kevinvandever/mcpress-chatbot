#!/bin/bash

# Stop Complete Remote Demo

echo "🛑 Stopping Complete Remote Demo..."

# Kill all processes
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Backend stopped"
lsof -ti:3003 | xargs kill -9 2>/dev/null && echo "✅ Frontend stopped"
pkill -f ngrok && echo "✅ ngrok tunnels stopped"

# Restore original API config
cd /Users/kevinvandever/kev-dev/pdf-chatbot/frontend
cat > config/api.ts << 'EOF'
// API configuration
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
EOF

echo "✅ Restored local API config"

# Clean up
rm -f .frontend_url .backend_url ngrok*.log 2>/dev/null

echo "✅ Complete remote demo stopped!"
echo "🔒 All public URLs are no longer accessible"