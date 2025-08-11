#!/usr/bin/env python3
"""
Test the _looks_like_code validation function
"""

from pdf_processor import PDFProcessor

def test_validation():
    """Test the _looks_like_code validation function"""
    
    processor = PDFProcessor()
    
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
    
    print("Testing _looks_like_code validation...")
    print("=" * 60)
    print(f"Sample content length: {len(sample_dds)} characters")
    print()
    
    # Test with different languages
    languages = ['dds', 'rpg', 'code', 'sql', 'cl']
    
    for lang in languages:
        result = processor._looks_like_code(sample_dds, lang)
        print(f"Language '{lang}': {result}")
        
        # Show detailed analysis for each language
        if lang == 'dds':
            print("  DDS validation details:")
            dds_keywords = ['CF', 'SFLSIZ', 'SFLPAG', 'OVERLAY', 'ROLLUP', 'SFLDSP', 'SFLCTL', 'SFLCLR', 'DSPATR']
            for keyword in dds_keywords:
                if keyword in sample_dds.upper():
                    print(f"    ✓ Contains '{keyword}'")
            if sample_dds.strip().startswith('A '):
                print("    ✓ Starts with 'A '")
                
        elif lang == 'rpg':
            print("  RPG validation details:")
            rpg_keywords = ['DCL-', 'MONITOR', 'EVAL', 'CALLP', 'BEGSR', 'ENDSR', 'DSPATR']
            found_keywords = []
            for keyword in rpg_keywords:
                if keyword in sample_dds.upper():
                    found_keywords.append(keyword)
                    print(f"    ✓ Contains '{keyword}'")
            if not found_keywords:
                print("    ✗ No RPG keywords found")
        print()

    # Test the general code validation logic
    print("General code validation details:")
    lines = sample_dds.split('\n')
    
    spec_lines = len([line for line in lines if line.strip().startswith(('A ', 'H ', 'D ', 'F '))])
    print(f"  Spec lines (A, H, D, F): {spec_lines}")
    
    semicolons = sample_dds.count(';')
    print(f"  Semicolons: {semicolons}")
    
    parens = sample_dds.count('(')
    close_parens = sample_dds.count(')')
    print(f"  Parentheses: {parens} open, {close_parens} close")
    
    indented_lines = len([line for line in lines if line.startswith('  ') and line.strip() and line[2:3].isalpha()])
    print(f"  Consistently indented lines: {indented_lines}")
    
    print("\nCode indicators evaluation:")
    code_indicators = [
        (spec_lines > 1, f"Multiple spec lines: {spec_lines} > 1"),
        (semicolons > 2, f"Multiple semicolons: {semicolons} > 2"),
        (parens > 2 and close_parens > 2, f"Multiple parentheses: {parens} open and {close_parens} close > 2 each"),
        (indented_lines > 2, f"Consistent indentation: {indented_lines} > 2"),
    ]
    
    for indicator, description in code_indicators:
        status = "✓" if indicator else "✗"
        print(f"  {status} {description}")

if __name__ == "__main__":
    test_validation()