#!/usr/bin/env python3
"""
Test script to verify pgvector integration and search quality
"""

import requests
import json
import time

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_health():
    """Test if the API is up"""
    print("1️⃣ Testing API health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ API is healthy")
            data = response.json()
            print(f"   📊 Vector store: {data.get('vector_store', 'unknown')}")
            print(f"   📊 OpenAI: {data.get('openai', 'unknown')}")
            return True
        else:
            print(f"   ❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        return False

def test_chat_query(query):
    """Test a chat query"""
    print(f"\n2️⃣ Testing query: '{query}'")
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"message": query, "conversation_id": "test-123"},
            timeout=30,
            stream=True
        )

        if response.status_code == 200:
            print("   ✅ Query successful")

            # Collect response
            full_response = ""
            sources = []
            metadata = {}

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8').replace('data: ', ''))

                        if data.get('type') == 'content':
                            full_response += data.get('content', '')
                        elif data.get('type') == 'metadata':
                            metadata = data
                        elif data.get('type') == 'done':
                            sources = data.get('sources', [])
                    except:
                        continue

            print(f"\n   📝 Response preview: {full_response[:200]}...")
            print(f"\n   📊 Metadata:")
            print(f"      - Source count: {metadata.get('source_count', 0)}")
            print(f"      - Confidence: {metadata.get('confidence', 0):.2f}")
            print(f"      - Model: {metadata.get('model_used', 'unknown')}")
            print(f"      - Threshold used: {metadata.get('threshold_used', 0):.2f}")
            print(f"      - Context tokens: {metadata.get('context_tokens', 0)}")

            if sources:
                print(f"\n   📚 Sources ({len(sources)}):")
                for i, src in enumerate(sources[:3]):
                    print(f"      {i+1}. {src.get('filename', 'Unknown')} (Page {src.get('page', 'N/A')})")
                    print(f"         Distance: {src.get('distance', 0):.3f}")

            return True
        else:
            print(f"   ❌ Query failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return False

def check_logs_for_pgvector():
    """Instructions to check logs"""
    print("\n3️⃣ To verify pgvector is enabled, check Railway logs for:")
    print("   ✅ '✅ pgvector extension enabled - using vector similarity'")
    print("   ✅ '✅ Using PostgreSQL with semantic embeddings'")
    print("\n   ❌ If you see '⚠️ pgvector not available', the DATABASE_URL is wrong")

def main():
    print("="*60)
    print("🧪 MC Press Chatbot - PGVector Integration Test")
    print("="*60)
    print()

    # Test API health
    if not test_health():
        print("\n⚠️ API is not responding. Wait for deployment to complete.")
        return

    print("\n" + "="*60)

    # Test some queries
    test_queries = [
        "What is RPG programming?",
        "How do I use SQL in DB2?",
        "Explain IBM i security"
    ]

    for query in test_queries:
        test_chat_query(query)
        time.sleep(2)  # Brief pause between queries
        print("\n" + "="*60)

    # Instructions for log checking
    check_logs_for_pgvector()

    print("\n✅ Testing complete!")
    print("\n📝 Next steps:")
    print("   1. Check Railway logs to confirm pgvector is enabled")
    print("   2. Try more queries in the actual chatbot UI")
    print("   3. Compare answer quality to before")

if __name__ == "__main__":
    main()
