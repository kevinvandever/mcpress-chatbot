#!/bin/bash

# MC Press Chatbot - Hybrid Setup Script
# This script helps you set up the hybrid deployment

echo "🚀 MC Press Chatbot - Hybrid Setup"
echo "=================================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 --version 2>&1)
echo "   Found: $python_version"

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "   Please create a .env file with your Railway DATABASE_URL:"
    echo "   DATABASE_URL=postgresql://user:pass@host/database"
    echo ""
    echo "   You can get this from Railway dashboard:"
    echo "   1. Go to your Railway project"
    echo "   2. Click on the PostgreSQL service"
    echo "   3. Go to 'Connect' tab"
    echo "   4. Copy the DATABASE_URL"
    exit 1
fi

echo "✅ Found .env file"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -q asyncpg sentence-transformers tqdm python-dotenv pandas pdfplumber PyMuPDF pillow pytesseract

# Check for PDFs
pdf_count=$(find backend/uploads -name "*.pdf" -type f | wc -l | tr -d ' ')
echo ""
echo "📚 Found $pdf_count PDF files in backend/uploads/"

if [ "$pdf_count" -eq "0" ]; then
    echo "⚠️  No PDFs found! Please add PDFs to backend/uploads/"
    exit 1
fi

# Ask user what to do
echo ""
echo "What would you like to do?"
echo "1) Run local preprocessing (process all PDFs)"
echo "2) Test query-only backend locally"
echo "3) Check deployment status"
echo "4) Exit"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🔄 Starting PDF preprocessing..."
        echo "This will process all $pdf_count PDFs and upload to Railway PostgreSQL"
        echo "This may take 10-30 minutes depending on your machine."
        echo ""
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            python3 preprocess_books_locally.py
        fi
        ;;
    2)
        echo ""
        echo "🧪 Starting local query-only backend..."
        echo "Backend will be available at http://localhost:8000"
        echo "Press Ctrl+C to stop"
        echo ""
        python3 backend/main_query_only.py
        ;;
    3)
        echo ""
        echo "📊 Checking deployment status..."
        echo ""
        
        # Check if Railway CLI is installed
        if command -v railway &> /dev/null; then
            echo "Railway deployment status:"
            railway status
        else
            echo "Railway CLI not installed. Install with: npm install -g @railway/cli"
        fi
        
        echo ""
        echo "To check backend health:"
        echo "curl https://your-railway-app.railway.app/"
        ;;
    4)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac