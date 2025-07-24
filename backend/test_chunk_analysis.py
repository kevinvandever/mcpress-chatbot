import asyncio
from pdf_processor_full import PDFProcessorFull
import json

async def analyze_chunks():
    processor = PDFProcessorFull()
    
    # Process the Subfiles book
    file_path = "./uploads/Subfiles in Free-Format RPG.pdf"
    print(f"Processing: {file_path}")
    
    result = await processor.process_pdf(file_path)
    
    # Analyze chunks
    chunks = result.get('chunks', [])
    print(f"\nTotal chunks: {len(chunks)}")
    
    # Count by type
    type_counts = {}
    text_chunks = []
    
    for chunk in chunks:
        chunk_type = chunk.get('metadata', {}).get('type', 'unknown')
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        if chunk_type == 'text':
            text_chunks.append(chunk)
    
    print(f"Chunks by type: {type_counts}")
    
    # Analyze text chunks
    if text_chunks:
        print(f"\nText chunks analysis:")
        print(f"Number of text chunks: {len(text_chunks)}")
        
        # Look at lengths
        lengths = []
        for chunk in text_chunks:
            metadata = chunk.get('metadata', {})
            meaningful = metadata.get('meaningful_length', 0)
            total = metadata.get('total_length', 0)
            lengths.append((meaningful, total))
        
        if lengths:
            avg_meaningful = sum(l[0] for l in lengths) / len(lengths)
            avg_total = sum(l[1] for l in lengths) / len(lengths)
            print(f"Average meaningful length: {avg_meaningful:.1f}")
            print(f"Average total length: {avg_total:.1f}")
        
        # Show first few text chunks
        print("\nFirst 3 text chunks:")
        for i, chunk in enumerate(text_chunks[:3]):
            print(f"\nChunk {i}:")
            print(f"  Content preview: {chunk['content'][:150]}...")
            print(f"  Metadata: {chunk['metadata']}")
    else:
        print("\nNo text chunks found!")
        
        # Let's see what's happening with the raw text
        print("\nDebugging: Checking raw text extraction...")
        # We'll need to look at the intermediate steps

if __name__ == "__main__":
    asyncio.run(analyze_chunks())