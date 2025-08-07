#!/usr/bin/env python3
"""Test the API directly to debug timeout issue"""

import sys
import os
sys.path.insert(0, '/Users/kevinvandever/kev-dev/pdf-chatbot')
os.chdir('/Users/kevinvandever/kev-dev/pdf-chatbot')

# Set environment
from dotenv import load_dotenv
load_dotenv()

# Import the vector store
from backend.vector_store import VectorStore
import asyncio

async def test_list_documents():
    print("Creating VectorStore instance...")
    vs = VectorStore()
    
    print("Calling list_documents...")
    try:
        docs = await vs.list_documents()
        print(f"Success! Found {len(docs)} documents")
        if docs:
            print(f"First document: {docs[0]['filename']}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if vs.pool:
            await vs.pool.close()

if __name__ == "__main__":
    asyncio.run(test_list_documents())