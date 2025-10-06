#!/bin/bash

# MC Press Chatbot - Embedding Regeneration Monitor
# Monitors the embedding regeneration job and auto-restarts if it stops
# Usage: ./monitor_embeddings.sh

API_URL="https://mcpress-chatbot-production.up.railway.app"
BATCH_SIZE=500
CHECK_INTERVAL=60  # Check every 60 seconds

echo "🚀 MC Press Embedding Regeneration Monitor"
echo "=========================================="
echo "API URL: $API_URL"
echo "Batch Size: $BATCH_SIZE"
echo "Check Interval: ${CHECK_INTERVAL}s"
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counter for stats
RESTART_COUNT=0
LAST_PROCESSED=0

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    # Try to start the job (will fail if already running)
    RESPONSE=$(curl -s -X POST "$API_URL/admin/regenerate-embeddings-start?batch_size=$BATCH_SIZE")

    # Parse the response
    RUNNING=$(echo "$RESPONSE" | grep -o '"running":[^,}]*' | cut -d':' -f2)
    PROCESSED=$(echo "$RESPONSE" | grep -o '"processed":[0-9]*' | cut -d':' -f2)
    TOTAL=$(echo "$RESPONSE" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    ERRORS=$(echo "$RESPONSE" | grep -o '"errors":[0-9]*' | cut -d':' -f2)
    CURRENT_BATCH=$(echo "$RESPONSE" | grep -o '"current_batch":[0-9]*' | cut -d':' -f2)
    TOTAL_BATCHES=$(echo "$RESPONSE" | grep -o '"total_batches":[0-9]*' | cut -d':' -f2)

    # Check if we have valid data
    if [ -z "$PROCESSED" ] || [ -z "$TOTAL" ]; then
        echo -e "${RED}[$TIMESTAMP] ❌ Error: Could not get status${NC}"
        echo "Response: $RESPONSE"
        sleep $CHECK_INTERVAL
        continue
    fi

    # Calculate progress
    PROGRESS=$(echo "scale=2; ($PROCESSED * 100) / $TOTAL" | bc)
    REMAINING=$((TOTAL - PROCESSED))

    # Check if we made progress since last check
    if [ "$PROCESSED" -gt "$LAST_PROCESSED" ]; then
        DOCS_PROCESSED=$((PROCESSED - LAST_PROCESSED))
        echo -e "${GREEN}[$TIMESTAMP] 📈 Progress: +$DOCS_PROCESSED docs${NC}"
    fi
    LAST_PROCESSED=$PROCESSED

    # Check if it's already running
    if echo "$RESPONSE" | grep -q "already running"; then
        echo -e "${BLUE}[$TIMESTAMP] ✅ Running${NC} | Batch: $CURRENT_BATCH/$TOTAL_BATCHES | Docs: $PROCESSED/$TOTAL ($PROGRESS%) | Errors: $ERRORS | Remaining: $REMAINING"
    else
        # Job was not running, so we just started it
        RESTART_COUNT=$((RESTART_COUNT + 1))
        echo -e "${YELLOW}[$TIMESTAMP] 🔄 Restarted${NC} (restart #$RESTART_COUNT) | Batch: $CURRENT_BATCH/$TOTAL_BATCHES | Docs: $PROCESSED/$TOTAL ($PROGRESS%) | Errors: $ERRORS"
    fi

    # Check if we're done
    if [ "$PROCESSED" -eq "$TOTAL" ]; then
        echo ""
        echo -e "${GREEN}=========================================="
        echo "🎉 COMPLETE!"
        echo "=========================================="
        echo "Total Documents: $TOTAL"
        echo "Errors: $ERRORS"
        echo "Total Restarts: $RESTART_COUNT"
        echo "==========================================${NC}"
        exit 0
    fi

    # Wait before next check
    sleep $CHECK_INTERVAL
done
