#!/usr/bin/env python3
"""
Test single problematic PDF with detailed debug
"""
import os
from pathlib import Path
from author_extractor import get_author_extractor
import fitz

def test_single_pdf():
    """Test the problematic PDF with detailed analysis"""
    pdf_path = "./uploads/Building Applications with IBM Rational Application Developer and JavaBeans.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return
    
    print(f"🔍 Detailed analysis of: {os.path.basename(pdf_path)}")
    print("="*80)
    
    # First, let's examine the PDF metadata and first page manually
    try:
        doc = fitz.open(pdf_path)
        print(f"📄 Total pages: {len(doc)}")
        
        # Check metadata
        metadata = doc.metadata
        print(f"\n📋 PDF Metadata:")
        for key, value in metadata.items():
            print(f"   {key}: {value}")
        
        # Check first page text
        if len(doc) > 0:
            page = doc[0]
            text = page.get_text()
            print(f"\n📖 First page text (first 500 chars):")
            print("-" * 40)
            print(text[:500])
            print("-" * 40)
            
            # Look for obvious author patterns manually
            lines = text.split('\n')
            print(f"\n📝 Analyzing lines for author patterns:")
            for i, line in enumerate(lines[:20]):  # First 20 lines
                line = line.strip()
                if line and len(line) > 3:
                    print(f"   Line {i+1:2d}: {line}")
        
        doc.close()
        
    except Exception as e:
        print(f"💥 Error analyzing PDF: {e}")
        return
    
    # Now test with our extractor
    print(f"\n🔍 Running Author Extractor:")
    print("="*50)
    
    extractor = get_author_extractor()
    author = extractor.extract_author(pdf_path)
    
    if author:
        print(f"\n🎉 SUCCESS: Found author = '{author}'")
    else:
        print(f"\n⚠️  FAILED: No author found")

if __name__ == "__main__":
    test_single_pdf()