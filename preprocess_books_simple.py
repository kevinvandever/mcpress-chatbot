#!/usr/bin/env python3
"""
Local PDF Preprocessing Script for MC Press Books (Simple Version)
Processes PDFs locally and uploads to Railway PostgreSQL using array storage
Works without pgvector extension
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime
import hashlib
from tqdm import tqdm
from dotenv import load_dotenv
import numpy as np

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.pdf_processor_full import PDFProcessorFull
from backend.category_mapper import get_category_mapper
from sentence_transformers import SentenceTransformer

load_dotenv()

class LocalPreprocessor:
    def __init__(self):
        self.pdf_processor = PDFProcessorFull()
        self.category_mapper = get_category_mapper()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in .env file")
        
        self.uploads_dir = Path("backend/uploads")
        self.processed_log = Path("preprocessing_log.json")
        self.processed_books = self.load_processed_log()
        
    def load_processed_log(self) -> Dict:
        """Load log of already processed books"""
        if self.processed_log.exists():
            with open(self.processed_log, 'r') as f:
                return json.load(f)
        return {"processed": [], "failed": [], "timestamp": None}
    
    def save_processed_log(self):
        """Save processing log"""
        self.processed_books["timestamp"] = datetime.now().isoformat()
        with open(self.processed_log, 'w') as f:
            json.dump(self.processed_books, f, indent=2)
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate hash of file for duplicate detection"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    async def process_single_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Process a single PDF file"""
        try:
            print(f"\n📚 Processing: {file_path.name}")
            
            # Extract PDF data
            pdf_data = await self.pdf_processor.process_pdf(str(file_path))
            
            # Extract metadata
            title = pdf_data.get('title', file_path.stem)
            author = pdf_data.get('author', 'Unknown')
            
            # Get category
            category = self.category_mapper.get_category(title, pdf_data.get('text', ''))
            
            # Generate embeddings for chunks
            chunks = pdf_data.get('chunks', [])
            embeddings = []
            
            print(f"   📝 Generating embeddings for {len(chunks)} chunks...")
            for chunk in tqdm(chunks, desc="   Chunks", leave=False):
                # Generate embedding and convert to list for storage
                embedding = self.embedding_model.encode(chunk['text']).tolist()
                embeddings.append({
                    'text': chunk['text'],
                    'embedding': embedding,  # Already a list
                    'page': chunk.get('page', 0)
                })
            
            return {
                'success': True,
                'filename': file_path.name,
                'title': title,
                'author': author,
                'category': category,
                'total_pages': pdf_data.get('total_pages', 0),
                'chunks_count': len(chunks),
                'embeddings': embeddings,
                'file_hash': self.get_file_hash(file_path)
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {str(e)}")
            return {
                'success': False,
                'filename': file_path.name,
                'error': str(e)
            }
    
    async def store_to_database(self, book_data: Dict[str, Any], conn: asyncpg.Connection):
        """Store processed book data to PostgreSQL using array storage"""
        try:
            # Insert book record
            book_id = await conn.fetchval("""
                INSERT INTO books (filename, title, author, category, total_pages, file_hash, processed_at)
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                ON CONFLICT (filename) DO UPDATE
                SET title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    category = EXCLUDED.category,
                    total_pages = EXCLUDED.total_pages,
                    file_hash = EXCLUDED.file_hash,
                    processed_at = CURRENT_TIMESTAMP
                RETURNING id
            """, book_data['filename'], book_data['title'], book_data['author'],
                book_data['category'], book_data['total_pages'], book_data['file_hash'])
            
            # Delete old embeddings for this book
            await conn.execute("DELETE FROM embeddings WHERE book_id = $1", book_id)
            
            # Prepare embeddings data for batch insert
            embeddings_data = []
            for i, emb in enumerate(book_data['embeddings']):
                embeddings_data.append((
                    book_id,
                    i,
                    emb['text'],
                    emb['embedding'],  # Already a list
                    emb['page']
                ))
            
            # Insert embeddings in batches (array storage)
            await conn.executemany("""
                INSERT INTO embeddings (book_id, chunk_index, content, embedding, page_number)
                VALUES ($1, $2, $3, $4::real[], $5)
            """, embeddings_data)
            
            print(f"   ✅ Stored {len(embeddings_data)} embeddings for {book_data['title']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Database error: {str(e)}")
            return False
    
    async def setup_database(self, conn: asyncpg.Connection):
        """Ensure database tables exist (array-based storage)"""
        
        # Create books table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                category TEXT,
                total_pages INTEGER,
                file_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create embeddings table with array storage
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                chunk_index INTEGER,
                content TEXT,
                embedding REAL[],
                page_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_book_id 
            ON embeddings(book_id);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_category 
            ON books(category);
        """)
        
        print("✅ Database schema ready (array-based storage)")
    
    async def run(self):
        """Main processing loop"""
        print("🚀 MC Press Books Local Preprocessor (Simple Version)")
        print(f"📁 Processing PDFs from: {self.uploads_dir}")
        print(f"🗄️  Storing to: Railway PostgreSQL (array storage)")
        
        # Get all PDF files
        pdf_files = list(self.uploads_dir.glob("*.pdf"))
        print(f"📚 Found {len(pdf_files)} PDF files")
        
        # Filter already processed
        if self.processed_books['processed']:
            already_processed = set(self.processed_books['processed'])
            pdf_files = [f for f in pdf_files if f.name not in already_processed]
            print(f"📋 Skipping {len(already_processed)} already processed files")
            print(f"📖 {len(pdf_files)} files to process")
        
        if not pdf_files:
            print("✅ All files already processed!")
            return
        
        # Connect to database
        conn = await asyncpg.connect(self.database_url)
        
        try:
            # Setup database schema
            await self.setup_database(conn)
            
            # Process each PDF
            for pdf_file in pdf_files:
                # Process PDF
                book_data = await self.process_single_pdf(pdf_file)
                
                if book_data['success']:
                    # Store to database
                    stored = await self.store_to_database(book_data, conn)
                    
                    if stored:
                        self.processed_books['processed'].append(pdf_file.name)
                    else:
                        self.processed_books['failed'].append({
                            'filename': pdf_file.name,
                            'error': 'Database storage failed'
                        })
                else:
                    self.processed_books['failed'].append({
                        'filename': pdf_file.name,
                        'error': book_data.get('error', 'Unknown error')
                    })
                
                # Save progress after each book
                self.save_processed_log()
                
        finally:
            await conn.close()
        
        # Final report
        print("\n" + "="*50)
        print("📊 Processing Complete!")
        print(f"✅ Successfully processed: {len(self.processed_books['processed'])} books")
        print(f"❌ Failed: {len(self.processed_books['failed'])} books")
        
        if self.processed_books['failed']:
            print("\nFailed books:")
            for failure in self.processed_books['failed']:
                print(f"  - {failure['filename']}: {failure['error']}")

if __name__ == "__main__":
    preprocessor = LocalPreprocessor()
    asyncio.run(preprocessor.run())