#!/bin/bash
# Batch fix categories for all miscategorized books

echo "🔧 Starting Category Fixes..."
echo "============================"

# RPG → Programming
echo -e "\n📚 Moving RPG books to Programming:"
echo "-----------------------------------"

books_to_programming=(
    "The RPG Programmers Guide to RPG IV and ILE.pdf"
    "Free-Format RPG IV- Third Edition.pdf"
    "21st Century RPG- -Free, ILE, and MVC.pdf"
    "Complete CL- Sixth Edition.pdf"
    "Evolve Your RPG Coding- Move from OPM to ILE ... and Beyond.pdf"
    "Free-Format RPG IV- Second Edition.pdf"
    "Complete CL- Fifth Edition.pdf"
    "Free-Format RPG IV- First Edition.pdf"
)

for book in "${books_to_programming[@]}"; do
    echo "Updating: $book"
    # URL encode the filename
    encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$book'))")
    
    # Get current metadata
    current=$(curl -s "http://localhost:8000/documents" | jq -r --arg filename "$book" '.documents[] | select(.filename == $filename)')
    title=$(echo "$current" | jq -r '.filename' | sed 's/.pdf$//')
    author=$(echo "$current" | jq -r '.author')
    
    # Update category
    curl -X PUT "http://localhost:8000/documents/$encoded/metadata" \
        -H "Content-Type: application/json" \
        -d "{\"filename\": \"$book\", \"title\": \"$title\", \"author\": \"$author\", \"category\": \"Programming\"}" \
        2>/dev/null | jq -r '.message' || echo "Failed"
    
    sleep 1
done

# RPG → Database (special case)
echo -e "\n💾 Moving DB2 book to Database:"
echo "-------------------------------"

book="DB2 11- The Ultimate Database for Cloud, Analytics, and Mobile.pdf"
encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$book'))")
current=$(curl -s "http://localhost:8000/documents" | jq -r --arg filename "$book" '.documents[] | select(.filename == $filename)')
title=$(echo "$current" | jq -r '.filename' | sed 's/.pdf$//')
author=$(echo "$current" | jq -r '.author')

curl -X PUT "http://localhost:8000/documents/$encoded/metadata" \
    -H "Content-Type: application/json" \
    -d "{\"filename\": \"$book\", \"title\": \"$title\", \"author\": \"$author\", \"category\": \"Database\"}" \
    2>/dev/null | jq -r '.message' || echo "Failed"

# Other fixes
echo -e "\n🔄 Fixing other mismatches:"
echo "---------------------------"

# Data Fabric book
book="Data Fabric- An Intelligent Data Architecutre for AI.pdf"
encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$book'))")
current=$(curl -s "http://localhost:8000/documents" | jq -r --arg filename "$book" '.documents[] | select(.filename == $filename)')
title=$(echo "$current" | jq -r '.filename' | sed 's/.pdf$//')
author=$(echo "$current" | jq -r '.author')

echo "Updating: $book"
curl -X PUT "http://localhost:8000/documents/$encoded/metadata" \
    -H "Content-Type: application/json" \
    -d "{\"filename\": \"$book\", \"title\": \"$title\", \"author\": \"$author\", \"category\": \"Database\"}" \
    2>/dev/null | jq -r '.message' || echo "Failed"

sleep 1

# AI book
book="Artificial Intelligence- Evolution and Revolution.pdf"
encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$book'))")
current=$(curl -s "http://localhost:8000/documents" | jq -r --arg filename "$book" '.documents[] | select(.filename == $filename)')
title=$(echo "$current" | jq -r '.filename' | sed 's/.pdf$//')
author=$(echo "$current" | jq -r '.author')

echo "Updating: $book"
curl -X PUT "http://localhost:8000/documents/$encoded/metadata" \
    -H "Content-Type: application/json" \
    -d "{\"filename\": \"$book\", \"title\": \"$title\", \"author\": \"$author\", \"category\": \"Database\"}" \
    2>/dev/null | jq -r '.message' || echo "Failed"

echo -e "\n✅ Category fixes complete!"
echo ""

# Verify final state
echo "📊 Final Category Distribution:"
echo "------------------------------"
curl -s "http://localhost:8000/documents" | jq '.documents[].category' | sort | uniq -c | sort -nr