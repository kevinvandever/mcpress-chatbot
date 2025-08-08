#!/bin/bash

# MC Press Chatbot - Status Check Script

echo "🔍 MC Press Chatbot Status Check"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check backend
echo -n "Backend (port 8000): "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    DOC_COUNT=$(curl -s http://localhost:8000/documents | jq '.documents | length' 2>/dev/null || echo "?")
    echo -e "${GREEN}✅ Running${NC} - $DOC_COUNT documents loaded"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check frontend
echo -n "Frontend (port 3001): "
if lsof -ti:3001 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check proxy
echo -n "Proxy (port 9000): "
if lsof -ti:9000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check tunnel
echo -n "Tunnel: "
TUNNEL_PROCESS=$(ps aux | grep "lt --port" | grep -v grep | head -1)
if [ ! -z "$TUNNEL_PROCESS" ]; then
    SUBDOMAIN=$(echo "$TUNNEL_PROCESS" | grep -o "subdomain [^ ]*" | cut -d' ' -f2)
    if [ -z "$SUBDOMAIN" ]; then
        SUBDOMAIN="default"
    fi
    IP=$(curl -4 -s ifconfig.me 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✅ Running${NC}"
    echo ""
    echo "📋 Access Information:"
    echo "   URL: https://${SUBDOMAIN}.loca.lt"
    echo "   Password: $IP"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check logs for errors
echo ""
echo "📊 Recent Errors:"
ERROR_COUNT=0

if [ -f backend.log ]; then
    BACKEND_ERRORS=$(grep -i "error\|exception" backend.log | tail -3 | wc -l)
    if [ $BACKEND_ERRORS -gt 0 ]; then
        echo -e "   ${YELLOW}⚠️  Backend has $BACKEND_ERRORS recent errors (check backend.log)${NC}"
        ERROR_COUNT=$((ERROR_COUNT + BACKEND_ERRORS))
    fi
fi

if [ -f frontend.log ]; then
    FRONTEND_ERRORS=$(grep -i "error" frontend.log | tail -3 | wc -l)
    if [ $FRONTEND_ERRORS -gt 0 ]; then
        echo -e "   ${YELLOW}⚠️  Frontend has $FRONTEND_ERRORS recent errors (check frontend.log)${NC}"
        ERROR_COUNT=$((ERROR_COUNT + FRONTEND_ERRORS))
    fi
fi

if [ $ERROR_COUNT -eq 0 ]; then
    echo -e "   ${GREEN}✅ No recent errors${NC}"
fi

# Memory usage
echo ""
echo "💾 Memory Usage:"
ps aux | grep -E "(python.*main.py|node.*next|node.*proxy|lt --port)" | grep -v grep | awk '{printf "   %-20s %s MB\n", substr($11, 0, 20), int($6/1024)}'

echo ""
echo "🔧 Commands:"
echo "   Start: ./start_unified_demo.sh"
echo "   Stop:  ./stop_unified_demo.sh"
echo "   Status: ./check_status.sh"