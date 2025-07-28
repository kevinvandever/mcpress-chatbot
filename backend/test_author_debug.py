#!/usr/bin/env python3
"""
Test author extraction with debug output
"""
import os
from pathlib import Path
from author_extractor import get_author_extractor

def test_author_extraction():
    """Test author extraction on sample PDFs"""
    print("🔍 Testing Author Extraction with Debug Output\n")
    
    # Get PDF files from uploads directory
    upload_dir = Path("./uploads")
    pdf_files = list(upload_dir.glob("*.pdf"))[:3]  # Test with first 3 PDFs
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory")
        return
    
    extractor = get_author_extractor()
    
    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Testing: {pdf_file.name}")
        print(f"{'='*60}")
        
        try:
            author = extractor.extract_author(str(pdf_file))
            
            if author:
                print(f"\n🎉 SUCCESS: Author found = '{author}'")
            else:
                print(f"\n⚠️  FAILED: No author found for {pdf_file.name}")
                
        except Exception as e:
            print(f"\n💥 ERROR: {e}")
    
    print(f"\n{'='*60}")
    print("Test completed!")

if __name__ == "__main__":
    test_author_extraction()