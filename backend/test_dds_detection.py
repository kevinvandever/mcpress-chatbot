#!/usr/bin/env python3
"""
Test script for DDS code detection in PDF processor
"""

from pdf_processor import PDFProcessor
import re

def test_dds_detection():
    """Test the DDS code detection patterns with sample DDS code"""
    
    processor = PDFProcessor()
    
    # Sample DDS code provided by user
    sample_dds = """A                CF06
A                SFLSIZ(0013)  
A                SFLPAG(0012)
A                ROLLUP
A                OVERLAY
A N32            SFLDSP
A N31            SFLDSPSCTL
A 31             SFLCLR
A 90             SFLEND(*MORE)
A        RRN1    4S 0H    SFLRCDNBR
A                9 7'Last Name'
A                DSPATR(HI)
A                9 31'First Name'
A                DSPATR(HI)
A                9 55'MI'
A                DSPATR(HI)
A                9 60'Nick Name'
A                DSPATR(HI)
A                1 2'SFL004RG'"""

    print("Testing DDS code detection...")
    print("=" * 60)
    print("Sample DDS code:")
    print(sample_dds)
    print("=" * 60)
    
    # Test the _extract_code_blocks method
    code_blocks = processor._extract_code_blocks(sample_dds, 1)
    
    print(f"Number of code blocks detected: {len(code_blocks)}")
    
    for i, block in enumerate(code_blocks):
        print(f"\nCode Block {i + 1}:")
        print(f"Language: {block['language']}")
        print(f"Page: {block['page']}")
        print(f"Content length: {len(block['content'])} characters")
        print("Content preview:")
        print(block['content'][:200] + "..." if len(block['content']) > 200 else block['content'])
        print("-" * 40)

    # Test individual patterns
    print("\nTesting individual regex patterns:")
    print("=" * 60)
    
    patterns = [
        (r'(?:^A\s+.*\n)+', 'dds', "Multiple A-spec lines"),
        (r'.*(?:CF\d+|SFLSIZ|SFLPAG|OVERLAY|ROLLUP|SFLDSP|SFLCTL|SFLCLR).*(?:\n.*(?:CF\d+|SFLSIZ|SFLPAG|OVERLAY|ROLLUP|SFLDSP|SFLCTL|SFLCLR).*)*', 'dds', "DDS keywords pattern"),
    ]
    
    for pattern, lang, description in patterns:
        print(f"\nTesting: {description}")
        print(f"Pattern: {pattern}")
        
        matches = list(re.finditer(pattern, sample_dds, re.MULTILINE | re.DOTALL))
        print(f"Matches found: {len(matches)}")
        
        for j, match in enumerate(matches):
            content = match.group(0).strip()
            print(f"Match {j + 1} length: {len(content)} characters")
            print(f"Match {j + 1} preview: {content[:100]}...")
            
            # Test the _looks_like_code validation
            looks_like_code = processor._looks_like_code(content, lang)
            print(f"Passes _looks_like_code validation: {looks_like_code}")
        print("-" * 40)

    # Test edge cases
    print("\nTesting edge cases:")
    print("=" * 60)
    
    # Test single A-spec line
    single_a_line = "A                CF06"
    print("Single A-spec line test:")
    single_blocks = processor._extract_code_blocks(single_a_line, 1)
    print(f"Blocks detected: {len(single_blocks)}")
    
    # Test mixed content
    mixed_content = f"""This is some regular text about DDS.

{sample_dds}

And here is more regular text after the DDS code."""
    
    print("\nMixed content test:")
    mixed_blocks = processor._extract_code_blocks(mixed_content, 1)
    print(f"Blocks detected: {len(mixed_blocks)}")
    for block in mixed_blocks:
        print(f"Language: {block['language']}, Length: {len(block['content'])}")

if __name__ == "__main__":
    test_dds_detection()