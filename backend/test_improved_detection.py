#!/usr/bin/env python3
"""
Test improved DDS detection with better validation logic
"""

import re
from typing import List, Dict, Any

class ImprovedPDFProcessor:
    """Improved PDF processor with better DDS detection"""
    
    def _extract_code_blocks(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Extract code blocks with improved pattern matching and validation"""
        code_blocks = []
        processed_ranges = []  # Track what text ranges have already been processed
        
        # Define patterns in order of specificity (most specific first)
        patterns = [
            # Markdown code blocks (highest priority)
            (r'```(\w+)?\n(.*?)```', 'detected', self._validate_markdown),
            
            # DDS (Display File Source) patterns - very specific
            (r'(?:^A\s+.*(?:\n|$)){3,}', 'dds', self._validate_dds),  # 3+ A-spec lines
            
            # RPG IV patterns - check for RPG-specific structures
            (r'(?:^[HDFRPC]\s+.*(?:\n|$)){2,}', 'rpg', self._validate_rpg),  # 2+ spec lines
            
            # SQL patterns 
            (r'(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.*(?:\n\s*.*)*?(?:;|$)', 'sql', self._validate_sql),
            
            # CL (Control Language) patterns
            (r'(?:CRTPF|ADDPFM|CHGPF|DLTPF|DSPFD|WRKACTJOB|STRPDM)(?:\s+|\n).*(?:\n.*)*', 'cl', self._validate_cl),
            
            # General programming patterns (lower priority)
            (r'^\s*(?:def|class|import|from|if|for|while|function|var|const|let)\s+.*(?:\n.*)*', 'code', self._validate_general_code),
            
            # Indented code blocks (lowest priority)
            (r'(?:^    .*(?:\n|$)){3,}', 'code', self._validate_indented_code),
        ]
        
        for pattern, default_lang, validator in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                start, end = match.span()
                
                # Skip if this range overlaps with already processed content
                if any(start < p_end and end > p_start for p_start, p_end in processed_ranges):
                    continue
                
                if len(match.groups()) > 1:
                    language = match.group(1) or default_lang
                    content = match.group(2)
                else:
                    language = default_lang
                    content = match.group(0)
                
                content = content.strip()
                
                # Apply minimum length and validation
                if len(content) > 30 and validator(content, language):
                    code_blocks.append({
                        "page": page_num,
                        "language": language,
                        "content": content
                    })
                    processed_ranges.append((start, end))
        
        return code_blocks
    
    def _validate_markdown(self, content: str, language: str) -> bool:
        """Validate markdown code blocks"""
        return len(content.strip()) > 10
    
    def _validate_dds(self, content: str, language: str) -> bool:
        """Validate DDS code with more specific criteria"""
        lines = content.split('\n')
        
        # Count lines that start with 'A' followed by whitespace
        a_spec_lines = [line for line in lines if re.match(r'^A\s+', line)]
        
        # Must have multiple A-spec lines
        if len(a_spec_lines) < 3:
            return False
        
        # Check for DDS-specific keywords
        dds_keywords = [
            'CF\d+', 'SFLSIZ', 'SFLPAG', 'OVERLAY', 'ROLLUP', 
            'SFLDSP', 'SFLCTL', 'SFLCLR', 'SFLEND', 'SFLRCDNBR'
        ]
        
        # Look for at least one strong DDS indicator
        content_upper = content.upper()
        has_dds_keywords = any(re.search(keyword, content_upper) for keyword in dds_keywords)
        
        # Check for typical DDS formatting patterns
        has_field_definitions = bool(re.search(r'A\s+\w+\s+\d+[SA]\s*\d*[HABNP]*', content))
        has_display_attributes = 'DSPATR' in content_upper
        has_literals = bool(re.search(r"A\s+\d+\s+\d+\s*'.*'", content))
        
        return has_dds_keywords or has_field_definitions or (has_display_attributes and len(a_spec_lines) >= 5) or has_literals
    
    def _validate_rpg(self, content: str, language: str) -> bool:
        """Validate RPG code with better specificity"""
        lines = content.split('\n')
        
        # Don't classify as RPG if it's clearly DDS (starts with many A lines)
        a_lines = [line for line in lines if re.match(r'^A\s+', line)]
        if len(a_lines) > len(lines) * 0.8:  # If >80% are A-spec lines, it's probably DDS
            return False
        
        # Look for RPG-specific patterns
        rpg_keywords = ['DCL-', 'MONITOR', 'ENDMON', 'BEGSR', 'ENDSR', 'EVAL', 'CALLP']
        free_form_rpg = any(keyword in content.upper() for keyword in rpg_keywords)
        
        # Check for traditional RPG spec indicators
        spec_lines = [line for line in lines if re.match(r'^[HDFRPC]\s+', line)]
        has_rpg_specs = len(spec_lines) >= 2
        
        # Don't match on DSPATR alone - it's common in DDS
        dspatr_only = 'DSPATR' in content.upper() and not any(kw in content.upper() for kw in rpg_keywords)
        
        return (free_form_rpg or has_rpg_specs) and not dspatr_only
    
    def _validate_sql(self, content: str, language: str) -> bool:
        """Validate SQL code"""
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']
        return any(keyword in content.upper() for keyword in sql_keywords)
    
    def _validate_cl(self, content: str, language: str) -> bool:
        """Validate CL code"""
        cl_commands = ['CRTPF', 'ADDPFM', 'CHGPF', 'DLTPF', 'DSPFD', 'WRKACTJOB', 'STRPDM']
        return any(cmd in content.upper() for cmd in cl_commands)
    
    def _validate_general_code(self, content: str, language: str) -> bool:
        """Validate general programming code"""
        code_keywords = ['def ', 'class ', 'import ', 'from ', 'function', 'var ', 'const ', 'let ']
        return any(keyword in content.lower() for keyword in code_keywords)
    
    def _validate_indented_code(self, content: str, language: str) -> bool:
        """Validate indented code blocks"""
        lines = content.split('\n')
        indented_lines = [line for line in lines if line.startswith('    ') and line.strip()]
        return len(indented_lines) >= 3

def test_improved_detection():
    """Test the improved DDS detection"""
    processor = ImprovedPDFProcessor()
    
    # Sample DDS code
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

    # Sample RPG code for comparison
    sample_rpg = """H DATEDIT(*YMD) COPYNEST DFTACTGRP(*NO) ACTGRP(*NEW) BNDDIR('QC2LE')

D num1            s              5i 0 inz(10)
D num2            s              5i 0 inz(20)
D result          s              5i 0

/free
  monitor;
    result = num1 + num2;
    dsply ('Result: ' + %char(result));
  on-error;
    dsply 'An error occurred';
  endmon;
/end-free"""

    print("Testing improved DDS detection...")
    print("=" * 60)
    
    # Test DDS sample
    print("DDS Sample:")
    dds_blocks = processor._extract_code_blocks(sample_dds, 1)
    print(f"Code blocks detected: {len(dds_blocks)}")
    for block in dds_blocks:
        print(f"  Language: {block['language']}, Length: {len(block['content'])}")
    
    # Test RPG sample
    print("\nRPG Sample:")
    rpg_blocks = processor._extract_code_blocks(sample_rpg, 1)
    print(f"Code blocks detected: {len(rpg_blocks)}")
    for block in rpg_blocks:
        print(f"  Language: {block['language']}, Length: {len(block['content'])}")
    
    # Test mixed content
    mixed_content = f"""This is a discussion about DDS programming.

{sample_dds}

Here's some RPG code for comparison:

{sample_rpg}

And that concludes our examples."""
    
    print("\nMixed Content:")
    mixed_blocks = processor._extract_code_blocks(mixed_content, 1)
    print(f"Code blocks detected: {len(mixed_blocks)}")
    for i, block in enumerate(mixed_blocks):
        print(f"  Block {i+1}: {block['language']}, Length: {len(block['content'])}")
        print(f"    Preview: {block['content'][:50]}...")
    
    return dds_blocks, rpg_blocks, mixed_blocks

if __name__ == "__main__":
    test_improved_detection()