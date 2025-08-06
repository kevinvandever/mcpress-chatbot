#!/usr/bin/env python3
"""
Analyze documents by comparing uploaded page counts with CSV expected pages
and chunk ratios to identify malformed documents
"""

import requests
import json
import csv
from datetime import datetime
import time

API_URL = "https://mcpress-chatbot-production.up.railway.app"
CSV_FILE = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/mc_press_categories.csv"

def load_csv_data():
    """Load expected page counts from CSV"""
    csv_data = {}
    
    try:
        with open(CSV_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Title') and row['Title'].strip():
                    title = row['Title'].strip() + '.pdf'
                    expected_pages = row.get('Pages', '').strip()
                    
                    # Convert to int if possible
                    try:
                        expected_pages = int(expected_pages) if expected_pages else None
                    except ValueError:
                        expected_pages = None
                    
                    csv_data[title] = {
                        'expected_pages': expected_pages,
                        'category': row.get('Original Category', '').strip(),
                        'filename': row.get('FileName', '').strip()
                    }
        
        print(f"📊 Loaded page data for {len(csv_data)} documents from CSV")
        return csv_data
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return {}

def get_all_documents():
    """Get all documents with their metadata"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            return response.json()['documents']
        else:
            print(f"Error getting documents: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def match_csv_to_documents(documents, csv_data):
    """Match uploaded documents with CSV data"""
    matched = []
    unmatched = []
    
    for doc in documents:
        filename = doc['filename']
        
        # Try exact match first
        csv_match = csv_data.get(filename)
        
        # If no exact match, try fuzzy matching
        if not csv_match:
            for csv_title in csv_data.keys():
                # Remove special characters and compare
                doc_clean = filename.replace(':', '-').replace('/', '-').lower()
                csv_clean = csv_title.replace(':', '-').replace('/', '-').lower()
                
                if doc_clean == csv_clean or doc_clean in csv_clean or csv_clean in doc_clean:
                    csv_match = csv_data[csv_title]
                    break
        
        if csv_match:
            matched.append({
                'filename': filename,
                'uploaded_pages': doc.get('total_pages', 0),
                'expected_pages': csv_match['expected_pages'],
                'chunks': doc.get('total_chunks', 0),
                'category': doc.get('category', 'Unknown'),
                'csv_category': csv_match['category']
            })
        else:
            unmatched.append({
                'filename': filename,
                'uploaded_pages': doc.get('total_pages', 0),
                'chunks': doc.get('total_chunks', 0),
                'category': doc.get('category', 'Unknown')
            })
    
    return matched, unmatched

def analyze_page_mismatches(matched_docs):
    """Analyze page count mismatches and chunk ratios"""
    page_mismatches = []
    chunk_anomalies = []
    good_docs = []
    
    for doc in matched_docs:
        filename = doc['filename']
        uploaded_pages = doc['uploaded_pages']
        expected_pages = doc['expected_pages']
        chunks = doc['chunks']
        
        # Skip if no expected pages data
        if expected_pages is None:
            continue
        
        # Calculate page difference
        page_diff = abs(uploaded_pages - expected_pages) if expected_pages > 0 else 0
        page_diff_percent = (page_diff / expected_pages * 100) if expected_pages > 0 else 0
        
        # Calculate chunks per page
        chunks_per_page = chunks / uploaded_pages if uploaded_pages > 0 else chunks
        
        # Categorize issues
        has_page_mismatch = page_diff > 5 or page_diff_percent > 10  # More than 5 pages or 10% off
        has_chunk_anomaly = chunks_per_page > 20  # More than 20 chunks per page
        
        doc_analysis = {
            **doc,
            'page_diff': page_diff,
            'page_diff_percent': page_diff_percent,
            'chunks_per_page': chunks_per_page,
            'has_page_mismatch': has_page_mismatch,
            'has_chunk_anomaly': has_chunk_anomaly
        }
        
        if has_page_mismatch and has_chunk_anomaly:
            page_mismatches.append(doc_analysis)  # Both issues - definitely problematic
        elif has_chunk_anomaly:
            chunk_anomalies.append(doc_analysis)  # Just chunk issues
        elif has_page_mismatch:
            page_mismatches.append(doc_analysis)  # Just page issues
        else:
            good_docs.append(doc_analysis)  # No issues
    
    return page_mismatches, chunk_anomalies, good_docs

def display_analysis(page_mismatches, chunk_anomalies, good_docs, unmatched):
    """Display comprehensive analysis results"""
    total_analyzed = len(page_mismatches) + len(chunk_anomalies) + len(good_docs)
    
    print(f"\n📊 Document Analysis Results:")
    print("="*100)
    print(f"✅ Good documents: {len(good_docs)} ({len(good_docs)/total_analyzed*100:.1f}%)")
    print(f"📄 Page mismatches only: {len([d for d in page_mismatches if not d['has_chunk_anomaly']])} documents")
    print(f"🔢 Chunk anomalies only: {len(chunk_anomalies)} documents")
    print(f"🚨 Both page & chunk issues: {len([d for d in page_mismatches if d['has_chunk_anomaly']])} documents")
    print(f"❓ Unmatched to CSV: {len(unmatched)} documents")
    
    # Show page mismatches
    if page_mismatches:
        print(f"\n🚨 PAGE & CHUNK ISSUES (Definitely need cleanup):")
        print("-"*100)
        print(f"{'Filename':<50} {'Expected':>8} {'Uploaded':>8} {'Diff':>6} {'Chunks':>8} {'C/P':>8} {'Issue':<20}")
        print("-"*100)
        
        for doc in sorted(page_mismatches, key=lambda x: x['chunks_per_page'], reverse=True)[:15]:
            issue_type = "PAGE+CHUNK" if doc['has_chunk_anomaly'] else "PAGE ONLY"
            print(f"{doc['filename'][:50]:<50} {doc['expected_pages']:>8} {doc['uploaded_pages']:>8} "
                  f"{doc['page_diff']:>6} {doc['chunks']:>8} {doc['chunks_per_page']:>8.1f} {issue_type:<20}")
    
    # Show chunk-only anomalies
    if chunk_anomalies:
        print(f"\n🔢 CHUNK ANOMALIES (Page count OK, but too many chunks):")
        print("-"*100)
        print(f"{'Filename':<50} {'Expected':>8} {'Uploaded':>8} {'Diff':>6} {'Chunks':>8} {'C/P':>8}")
        print("-"*100)
        
        for doc in sorted(chunk_anomalies, key=lambda x: x['chunks_per_page'], reverse=True)[:10]:
            print(f"{doc['filename'][:50]:<50} {doc['expected_pages']:>8} {doc['uploaded_pages']:>8} "
                  f"{doc['page_diff']:>6} {doc['chunks']:>8} {doc['chunks_per_page']:>8.1f}")
    
    # Show some good documents for reference
    if good_docs:
        print(f"\n✅ SAMPLE GOOD DOCUMENTS (for comparison):")
        print("-"*100)
        print(f"{'Filename':<50} {'Expected':>8} {'Uploaded':>8} {'Diff':>6} {'Chunks':>8} {'C/P':>8}")
        print("-"*100)
        
        for doc in sorted(good_docs, key=lambda x: x['chunks_per_page'], reverse=True)[:5]:
            print(f"{doc['filename'][:50]:<50} {doc['expected_pages']:>8} {doc['uploaded_pages']:>8} "
                  f"{doc['page_diff']:>6} {doc['chunks']:>8} {doc['chunks_per_page']:>8.1f}")

def create_cleanup_recommendations(page_mismatches, chunk_anomalies):
    """Create cleanup recommendations with different severity levels"""
    high_priority = []  # Definitely should delete
    medium_priority = []  # Probably should delete
    low_priority = []  # Maybe should delete
    
    # High priority: Both page and chunk issues, or extreme chunk ratios
    for doc in page_mismatches:
        if doc['has_chunk_anomaly'] and doc['chunks_per_page'] > 50:
            high_priority.append({
                'filename': doc['filename'],
                'reason': f"Page mismatch ({doc['page_diff']} pages off) + extreme chunks ({doc['chunks_per_page']:.1f}/page)",
                'chunks': doc['chunks'],
                'expected_pages': doc['expected_pages'],
                'uploaded_pages': doc['uploaded_pages'],
                'severity': 'HIGH'
            })
        elif doc['has_chunk_anomaly']:
            medium_priority.append({
                'filename': doc['filename'],
                'reason': f"Page mismatch ({doc['page_diff']} pages off) + high chunks ({doc['chunks_per_page']:.1f}/page)",
                'chunks': doc['chunks'],
                'expected_pages': doc['expected_pages'],
                'uploaded_pages': doc['uploaded_pages'],
                'severity': 'MEDIUM'
            })
        else:
            low_priority.append({
                'filename': doc['filename'],
                'reason': f"Page count off by {doc['page_diff']} pages ({doc['page_diff_percent']:.1f}%)",
                'chunks': doc['chunks'],
                'expected_pages': doc['expected_pages'],
                'uploaded_pages': doc['uploaded_pages'],
                'severity': 'LOW'
            })
    
    # Medium priority: Chunk anomalies only
    for doc in chunk_anomalies:
        if doc['chunks_per_page'] > 100:
            high_priority.append({
                'filename': doc['filename'],
                'reason': f"Extreme chunk ratio: {doc['chunks_per_page']:.1f} chunks/page",
                'chunks': doc['chunks'],
                'expected_pages': doc['expected_pages'],
                'uploaded_pages': doc['uploaded_pages'],
                'severity': 'HIGH'
            })
        else:
            medium_priority.append({
                'filename': doc['filename'],
                'reason': f"High chunk ratio: {doc['chunks_per_page']:.1f} chunks/page",
                'chunks': doc['chunks'],
                'expected_pages': doc['expected_pages'],
                'uploaded_pages': doc['uploaded_pages'],
                'severity': 'MEDIUM'
            })
    
    return high_priority, medium_priority, low_priority

def save_cleanup_recommendations(high_priority, medium_priority, low_priority):
    """Save cleanup recommendations to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cleanup_recommendations_{timestamp}.json"
    
    data = {
        'analysis_date': datetime.now().isoformat(),
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
        'summary': {
            'high_priority_count': len(high_priority),
            'medium_priority_count': len(medium_priority),
            'low_priority_count': len(low_priority),
            'total_recommended': len(high_priority) + len(medium_priority) + len(low_priority)
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Cleanup recommendations saved to: {filename}")
    return filename

def delete_documents_by_priority(high_priority, medium_priority, low_priority):
    """Allow user to delete documents by priority level"""
    print(f"\n🧹 Cleanup Options:")
    print(f"🚨 High Priority (definitely malformed): {len(high_priority)} documents")
    print(f"⚠️  Medium Priority (likely malformed): {len(medium_priority)} documents") 
    print(f"📋 Low Priority (page count discrepancies): {len(low_priority)} documents")
    
    # Show what we'd delete
    if high_priority:
        print(f"\n🚨 HIGH PRIORITY DELETIONS:")
        for doc in high_priority[:5]:
            print(f"   - {doc['filename'][:60]} ({doc['reason']})")
        if len(high_priority) > 5:
            print(f"   ... and {len(high_priority) - 5} more")
    
    print(f"\nChoose cleanup level:")
    print(f"1. Delete HIGH priority only ({len(high_priority)} docs)")
    print(f"2. Delete HIGH + MEDIUM priority ({len(high_priority) + len(medium_priority)} docs)")
    print(f"3. Delete ALL recommendations ({len(high_priority) + len(medium_priority) + len(low_priority)} docs)")
    print(f"4. No deletion (just analysis)")
    
    choice = input("Enter choice (1-4): ").strip()
    
    to_delete = []
    if choice == '1':
        to_delete = high_priority
    elif choice == '2':
        to_delete = high_priority + medium_priority
    elif choice == '3':
        to_delete = high_priority + medium_priority + low_priority
    else:
        print("No documents will be deleted.")
        return 0, 0
    
    if not to_delete:
        print("No documents selected for deletion.")
        return 0, 0
    
    # Confirm deletion
    total_chunks = sum(doc['chunks'] for doc in to_delete)
    print(f"\n⚠️  About to delete {len(to_delete)} documents ({total_chunks:,} chunks)")
    confirm = input("Proceed with deletion? (y/N): ")
    
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        return 0, 0
    
    # Perform deletions
    successful = 0
    failed = 0
    
    for i, doc in enumerate(to_delete, 1):
        print(f"\n[{i}/{len(to_delete)}] Deleting: {doc['filename']}")
        print(f"   Reason: {doc['reason']}")
        
        try:
            response = requests.delete(
                f"{API_URL}/documents/{doc['filename']}", 
                timeout=30
            )
            
            if response.status_code == 200:
                print("   ✅ Deleted successfully")
                successful += 1
            else:
                print(f"   ❌ Failed: {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1
        
        time.sleep(1)  # Small delay
    
    return successful, failed

def main():
    print("📊 Document Page & Chunk Analysis Tool")
    print("="*100)
    print("Compares uploaded documents with CSV expected page counts and analyzes chunk ratios")
    
    # Load CSV data
    csv_data = load_csv_data()
    if not csv_data:
        return
    
    # Get uploaded documents
    documents = get_all_documents()
    if not documents:
        print("❌ No documents found")
        return
    
    print(f"📄 Found {len(documents)} uploaded documents")
    
    # Match documents with CSV
    matched_docs, unmatched_docs = match_csv_to_documents(documents, csv_data)
    print(f"✅ Matched {len(matched_docs)} documents with CSV data")
    print(f"❓ {len(unmatched_docs)} documents not found in CSV")
    
    # Analyze mismatches
    page_mismatches, chunk_anomalies, good_docs = analyze_page_mismatches(matched_docs)
    
    # Display results
    display_analysis(page_mismatches, chunk_anomalies, good_docs, unmatched_docs)
    
    # Create cleanup recommendations
    high_priority, medium_priority, low_priority = create_cleanup_recommendations(page_mismatches, chunk_anomalies)
    
    # Save recommendations
    save_cleanup_recommendations(high_priority, medium_priority, low_priority)
    
    # Offer to clean up
    if high_priority or medium_priority or low_priority:
        successful, failed = delete_documents_by_priority(high_priority, medium_priority, low_priority)
        
        if successful > 0:
            print(f"\n✅ Successfully deleted {successful} documents")
            print(f"❌ Failed to delete {failed} documents")
            
            # Show new document count
            time.sleep(2)
            new_docs = get_all_documents()
            print(f"📊 New document count: {len(new_docs)}")
            print(f"💡 You may now be able to upload the remaining documents!")
    else:
        print("\n✅ No cleanup needed - all documents look good!")

if __name__ == "__main__":
    main()