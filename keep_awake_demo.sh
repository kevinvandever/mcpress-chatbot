#!/bin/bash

# Keep Mac awake and run demo indefinitely
# Useful for long-running demos

echo "🌙 Starting MC Press Chatbot with caffeinate (keeps Mac awake)..."

# Start the demo and keep Mac awake
caffeinate -s ./start_demo.sh

echo ""
echo "💤 Keeping Mac awake while demo runs..."
echo "   Press Ctrl+C to stop and allow sleep"
echo ""

# Keep running indefinitely while preventing sleep
caffeinate -d -i -m -u