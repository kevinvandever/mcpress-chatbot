#!/usr/bin/env python3
"""
Analyze and clean up documents with abnormal chunk counts
"""

import requests
import json
from datetime import datetime
import time

API_URL = "https://mcpress-chatbot-production.up.railway.app"

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

def analyze_chunk_ratios(documents):
    """Analyze chunk to page ratios and identify anomalies"""
    print("🔍 Analyzing chunk distributions...")
    print("="*80)
    
    abnormal_docs = []
    suspicious_docs = []
    normal_docs = []
    
    for doc in documents:
        filename = doc['filename']
        try:
            total_chunks = int(doc.get('total_chunks', 0))
            total_pages_raw = doc.get('total_pages', 1)
            total_pages = int(total_pages_raw) if total_pages_raw != 'N/A' else 1
        except (ValueError, TypeError):
            total_chunks = 0
            total_pages = 1

        if total_pages == 0:
            total_pages = 1  # Avoid division by zero

        chunks_per_page = total_chunks / total_pages
        
        # Categorize documents
        if chunks_per_page > 100:  # Definitely abnormal
            abnormal_docs.append({
                'filename': filename,
                'pages': total_pages,
                'chunks': total_chunks,
                'ratio': chunks_per_page,
                'category': doc.get('category', 'Unknown')
            })
        elif chunks_per_page > 20:  # Suspicious
            suspicious_docs.append({
                'filename': filename,
                'pages': total_pages,
                'chunks': total_chunks,
                'ratio': chunks_per_page,
                'category': doc.get('category', 'Unknown')
            })
        else:  # Normal
            normal_docs.append({
                'filename': filename,
                'pages': total_pages,
                'chunks': total_chunks,
                'ratio': chunks_per_page,
                'category': doc.get('category', 'Unknown')
            })
    
    return abnormal_docs, suspicious_docs, normal_docs

def display_analysis(abnormal_docs, suspicious_docs, normal_docs):
    """Display analysis results"""
    total_docs = len(abnormal_docs) + len(suspicious_docs) + len(normal_docs)
    
    print(f"\n📊 Document Analysis Summary:")
    print(f"Total documents: {total_docs}")
    print(f"✅ Normal: {len(normal_docs)} ({len(normal_docs)/total_docs*100:.1f}%)")
    print(f"⚠️  Suspicious: {len(suspicious_docs)} ({len(suspicious_docs)/total_docs*100:.1f}%)")
    print(f"🚨 Abnormal: {len(abnormal_docs)} ({len(abnormal_docs)/total_docs*100:.1f}%)")
    
    # Show abnormal documents
    if abnormal_docs:
        print(f"\n🚨 ABNORMAL DOCUMENTS (>{100} chunks/page):")
        print("-"*80)
        print(f"{'Filename':<50} {'Pages':>6} {'Chunks':>8} {'Ratio':>10} {'Category':<20}")
        print("-"*80)
        for doc in sorted(abnormal_docs, key=lambda x: x['ratio'], reverse=True)[:20]:
            print(f"{doc['filename'][:50]:<50} {doc['pages']:>6} {doc['chunks']:>8} {doc['ratio']:>10.1f} {doc['category']:<20}")
    
    # Show suspicious documents
    if suspicious_docs:
        print(f"\n⚠️  SUSPICIOUS DOCUMENTS (20-100 chunks/page):")
        print("-"*80)
        print(f"{'Filename':<50} {'Pages':>6} {'Chunks':>8} {'Ratio':>10} {'Category':<20}")
        print("-"*80)
        for doc in sorted(suspicious_docs, key=lambda x: x['ratio'], reverse=True)[:10]:
            print(f"{doc['filename'][:50]:<50} {doc['pages']:>6} {doc['chunks']:>8} {doc['ratio']:>10.1f} {doc['category']:<20}")
    
    # Calculate space usage
    total_abnormal_chunks = sum(d['chunks'] for d in abnormal_docs)
    total_suspicious_chunks = sum(d['chunks'] for d in suspicious_docs)
    total_normal_chunks = sum(d['chunks'] for d in normal_docs)
    total_chunks = total_abnormal_chunks + total_suspicious_chunks + total_normal_chunks
    
    print(f"\n💾 Chunk Distribution:")
    print(f"Normal documents: {total_normal_chunks:,} chunks ({total_normal_chunks/total_chunks*100:.1f}%)")
    print(f"Suspicious documents: {total_suspicious_chunks:,} chunks ({total_suspicious_chunks/total_chunks*100:.1f}%)")
    print(f"Abnormal documents: {total_abnormal_chunks:,} chunks ({total_abnormal_chunks/total_chunks*100:.1f}%)")
    print(f"Total chunks in database: {total_chunks:,}")
    
    return abnormal_docs, suspicious_docs

def create_cleanup_list(abnormal_docs, suspicious_docs):
    """Create a list of documents to clean up"""
    cleanup_list = []
    
    # Add all abnormal documents
    for doc in abnormal_docs:
        cleanup_list.append({
            'filename': doc['filename'],
            'reason': f"Abnormal ratio: {doc['ratio']:.1f} chunks/page",
            'chunks': doc['chunks'],
            'pages': doc['pages']
        })
    
    # Optionally add very suspicious documents (>50 chunks/page)
    for doc in suspicious_docs:
        if doc['ratio'] > 50:
            cleanup_list.append({
                'filename': doc['filename'],
                'reason': f"High ratio: {doc['ratio']:.1f} chunks/page",
                'chunks': doc['chunks'],
                'pages': doc['pages']
            })
    
    return cleanup_list

def save_cleanup_list(cleanup_list):
    """Save cleanup list to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cleanup_list_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(cleanup_list, f, indent=2)
    
    print(f"\n💾 Cleanup list saved to: {filename}")
    return filename

def delete_documents(cleanup_list):
    """Delete documents from the system"""
    print(f"\n🗑️  Preparing to delete {len(cleanup_list)} documents...")
    
    # Confirm before deletion
    total_chunks = sum(doc['chunks'] for doc in cleanup_list)
    print(f"This will remove {total_chunks:,} chunks from the database.")
    response = input("Proceed with deletion? (y/N): ")
    
    if response.lower() != 'y':
        print("Deletion cancelled.")
        return
    
    successful = 0
    failed = 0
    
    for i, doc in enumerate(cleanup_list, 1):
        print(f"\n[{i}/{len(cleanup_list)}] Deleting: {doc['filename']}")
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
        
        # Small delay between deletions
        time.sleep(1)
    
    print(f"\n📊 Deletion Summary:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    return successful, failed

def main():
    print("🔍 Document Chunk Analysis Tool")
    print("="*80)
    
    # Get all documents
    documents = get_all_documents()
    if not documents:
        print("❌ No documents found or error connecting to API")
        return
    
    # Analyze chunk ratios
    abnormal_docs, suspicious_docs, normal_docs = analyze_chunk_ratios(documents)
    
    # Display analysis
    abnormal_docs, suspicious_docs = display_analysis(abnormal_docs, suspicious_docs, normal_docs)
    
    # Create cleanup list
    cleanup_list = create_cleanup_list(abnormal_docs, suspicious_docs)
    
    if cleanup_list:
        print(f"\n🧹 Recommended cleanup: {len(cleanup_list)} documents")
        
        # Save cleanup list
        cleanup_file = save_cleanup_list(cleanup_list)
        
        # Ask if user wants to proceed with cleanup
        print(f"\n⚠️  Found {len(cleanup_list)} documents that should be removed")
        response = input("Do you want to delete these documents now? (y/N): ")
        
        if response.lower() == 'y':
            delete_documents(cleanup_list)
            
            # Show final count
            time.sleep(2)
            new_docs = get_all_documents()
            print(f"\n📊 Final document count: {len(new_docs)}")
            
            # Suggest re-uploading
            print("\n💡 Suggestion: After cleanup, try re-uploading the deleted documents.")
            print("   They should process correctly this time.")
    else:
        print("\n✅ No documents need cleanup!")

if __name__ == "__main__":
    main()