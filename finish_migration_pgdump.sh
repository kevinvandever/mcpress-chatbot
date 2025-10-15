#!/bin/bash
# Complete the migration using pg_dump and pg_restore (much faster!)

echo "🚀 Finishing migration using PostgreSQL native tools"
echo "===================================================="

OLD_DB="postgresql://postgres:MHmKuNmWWbYhOujBeIFsfgbQFkNAJjHG@ballast.proxy.rlwy.net:41917/railway"
NEW_DB="postgresql://postgres:OxATCwPVTNVdadKbPNTGvUyrktrTObOh@shortline.proxy.rlwy.net:18459/railway"

echo "📊 Current progress: 220,569 / 235,409 migrated (93.7%)"
echo "📦 Remaining: ~14,840 documents"
echo ""
echo "🔄 Using pg_dump to export remaining documents..."

# Dump only documents with ID > 365807 (last migrated ID)
pg_dump "$OLD_DB" \
  --table=documents \
  --data-only \
  --column-inserts \
  --no-owner \
  --no-privileges \
  2>/dev/null | \
  grep "INSERT INTO" | \
  grep -E "VALUES \([0-9]*,.*\)" | \
  awk -F'(' '{if ($2 > 365807) print}' > remaining_documents.sql

if [ -f remaining_documents.sql ]; then
    LINE_COUNT=$(wc -l < remaining_documents.sql)
    echo "✅ Exported $LINE_COUNT remaining documents"
    echo ""
    echo "📥 Importing into new database..."

    # Import into new database
    psql "$NEW_DB" -f remaining_documents.sql 2>&1 | grep -E "INSERT|ERROR" | head -20

    echo ""
    echo "✅ Import complete!"
else
    echo "❌ Failed to export documents"
    exit 1
fi

echo ""
echo "📊 Verifying final counts..."

echo "Old database:"
psql "$OLD_DB" -t -c "SELECT COUNT(*) FROM documents" 2>/dev/null

echo "New database:"
psql "$NEW_DB" -t -c "SELECT COUNT(*) FROM documents" 2>/dev/null

echo ""
echo "🎉 Migration complete! Proceed to update DATABASE_URL in Railway."
