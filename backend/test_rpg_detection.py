#!/usr/bin/env python3
"""Test RPG detection on Subfiles in Free-Format RPG PDF"""

import asyncio
from pdf_processor import PDFProcessor

async def test():
    processor = PDFProcessor()
    
    # Process the Subfiles PDF
    pdf_path = "./uploads/Subfiles in Free-Format RPG.pdf"
    print(f"Processing: {pdf_path}")
    
    result = await processor.process_pdf(pdf_path)
    
    # Count code blocks by language
    languages = {}
    for chunk in result['chunks']:
        if chunk['metadata'].get('type') == 'code':
            lang = chunk['metadata'].get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
    
    print(f"\nCode blocks found by language:")
    for lang, count in sorted(languages.items()):
        print(f"  {lang}: {count}")
    
    # Show a few RPG examples
    print("\nSample RPG code blocks:")
    rpg_count = 0
    for chunk in result['chunks']:
        if chunk['metadata'].get('type') == 'code' and chunk['metadata'].get('language') == 'rpg':
            rpg_count += 1
            if rpg_count <= 3:
                print(f"\n--- RPG Block {rpg_count} (page {chunk['metadata'].get('page', 'unknown')}) ---")
                print(chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content'])
            
if __name__ == "__main__":
    asyncio.run(test())