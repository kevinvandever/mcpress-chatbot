#!/bin/bash
# Quick migration progress checker

echo "📊 Migration Progress"
echo "===================="

# Check if progress file exists
if [ -f migration_progress.json ]; then
    LAST_ID=$(python3 -c "import json; print(json.load(open('migration_progress.json'))['last_migrated_id'])")
    TOTAL=$(python3 -c "import json; print(json.load(open('migration_progress.json'))['total_migrated'])")
    PERCENT=$(python3 -c "print(round($TOTAL / 235409 * 100, 2))")

    echo "✅ Documents migrated: $TOTAL / 235,409"
    echo "📈 Progress: $PERCENT%"
    echo "🔢 Last ID processed: $LAST_ID"

    REMAINING=$((235409 - TOTAL))
    RATE=16  # docs per second (approximate)
    ETA_SECONDS=$((REMAINING / RATE))
    ETA_HOURS=$((ETA_SECONDS / 3600))
    ETA_MINUTES=$(((ETA_SECONDS % 3600) / 60))

    echo "⏱️  Estimated time remaining: ${ETA_HOURS}h ${ETA_MINUTES}m"
else
    echo "⚠️  No progress file found - migration may not have started yet"
fi

echo ""
echo "💡 Run this script again anytime to check progress:"
echo "   ./check_migration_progress.sh"
