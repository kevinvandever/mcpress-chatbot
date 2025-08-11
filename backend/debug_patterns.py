#!/usr/bin/env python3
"""
Debug script to analyze regex pattern behavior for DDS detection
"""

import re

def debug_patterns():
    """Debug the regex patterns used for DDS detection"""
    
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

    print("Analyzing DDS patterns...")
    print("=" * 60)
    
    # Test the current patterns one by one
    patterns = [
        (r'```(\w+)?\n(.*?)```', 'detected', "Triple backticks"),
        (r'(?:^A\s+.*\n)+', 'dds', "Multiple A-spec lines"),
        (r'.*(?:CF\d+|SFLSIZ|SFLPAG|OVERLAY|ROLLUP|SFLDSP|SFLCTL|SFLCLR).*(?:\n.*(?:CF\d+|SFLSIZ|SFLPAG|OVERLAY|ROLLUP|SFLDSP|SFLCTL|SFLCLR).*)*', 'dds', "DDS keywords pattern"),
        (r'(?:^[HDFRPC]\s+.*\n)+', 'rpg', "RPG spec lines"),
        (r'.*(?:DCL-|MONITOR|ENDMON|BEGSR|ENDSR|EVAL|CALLP|DSPATR).*(?:\n.*(?:DCL-|MONITOR|ENDMON|BEGSR|ENDSR|EVAL|CALLP|DSPATR).*)*', 'rpg', "RPG keywords"),
        (r'(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.*(?:\n\s*.*)*?(?:;|$)', 'sql', "SQL patterns"),
        (r'(?:CRTPF|ADDPFM|CHGPF|DLTPF|DSPFD|WRKACTJOB|STRPDM)(?:\s+|\n).*(?:\n.*)*', 'cl', "CL patterns"),
        (r'    .*(?:\n    .*)*', 'code', "Indented code"),
        (r'^\s*(?:def|class|import|from|if|for|while|function|var|const|let)\s+.*$', 'code', "Programming keywords"),
        (r'(?:^\s{2,}[A-Z][A-Z0-9_]*\s+.*\n){3,}', 'code', "Structured text"),
    ]
    
    for i, (pattern, lang, desc) in enumerate(patterns):
        print(f"\nPattern {i+1}: {desc}")
        print(f"Language: {lang}")
        print(f"Regex: {pattern}")
        
        try:
            matches = list(re.finditer(pattern, sample_dds, re.MULTILINE | re.DOTALL))
            print(f"Matches: {len(matches)}")
            
            for j, match in enumerate(matches):
                if len(match.groups()) > 1:
                    language = match.group(1) or lang
                    content = match.group(2)
                    print(f"  Match {j+1}: Groups found - Lang: '{language}', Content length: {len(content)}")
                else:
                    content = match.group(0)
                    print(f"  Match {j+1}: Single group - Content length: {len(content)}")
                
                content = content.strip()
                print(f"  Content preview (first 100 chars): {repr(content[:100])}")
                
                # Check minimum length requirement
                if len(content) > 30:
                    print(f"  ✓ Passes length requirement (>{30} chars)")
                else:
                    print(f"  ✗ Fails length requirement (<={30} chars)")
                    
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print("-" * 60)
    
    # Test the problem with overlapping matches
    print("\nAnalyzing overlap issues:")
    print("=" * 60)
    
    # Check what happens when we apply patterns in sequence
    print("Simulating pattern matching in order...")
    found_matches = []
    
    for i, (pattern, lang, desc) in enumerate(patterns):
        matches = list(re.finditer(pattern, sample_dds, re.MULTILINE | re.DOTALL))
        for match in matches:
            content = match.group(0).strip() if len(match.groups()) <= 1 else match.group(2).strip()
            if len(content) > 30:
                found_matches.append({
                    'pattern_index': i,
                    'description': desc,
                    'language': lang,
                    'content_length': len(content),
                    'start': match.start(),
                    'end': match.end()
                })
    
    print(f"Total qualifying matches: {len(found_matches)}")
    for match in found_matches:
        print(f"  Pattern {match['pattern_index']+1} ({match['description']}): {match['language']} - {match['content_length']} chars at pos {match['start']}-{match['end']}")

if __name__ == "__main__":
    debug_patterns()