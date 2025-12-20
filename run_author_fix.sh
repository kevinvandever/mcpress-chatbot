#!/bin/bash

echo "🚀 Running Author Fix on Railway..."
echo "=================================="

# Check if Railway CLI is available
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Login to Railway (if not already logged in)
echo "🔐 Ensuring Railway login..."
railway whoami || railway login

# Run the author fix script
echo "🛠️  Executing author fix..."
railway run python3 fix_specific_author_issues.py

echo "✅ Author fix completed!"
echo ""
echo "Next steps:"
echo "1. Test chat interface with: 'Complete CL programming'"
echo "2. Test chat interface with: 'Subfiles RPG'"
echo "3. Test chat interface with: 'Control Language Programming'"
echo "4. Verify authors show correctly (not 'annegrubb' or 'admin')"