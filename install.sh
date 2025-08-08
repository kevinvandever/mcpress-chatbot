#!/bin/bash
set -e

echo "📦 Installing Node.js..."
apt-get update
apt-get install -y nodejs npm tesseract-ocr

echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Installing frontend dependencies..."
cd frontend
npm install

echo "🔨 Building frontend..."
npm run build

echo "✅ Installation complete!"