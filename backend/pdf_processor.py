import fitz  # PyMuPDF
import base64
import io
import re
from typing import List, Dict, Any
from PIL import Image
import pytesseract
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio

class PDFProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
    async def process_pdf(self, file_path: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_pdf_sync, file_path)
    
    def _process_pdf_sync(self, file_path: str) -> Dict[str, Any]:
        doc = fitz.open(file_path)
        
        all_text = ""
        images = []
        code_blocks = []
        chunks = []
        
        try:
            # First pass: extract text and code blocks
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                all_text += f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"
                code_blocks.extend(self._extract_code_blocks(page_text, page_num + 1))
            
            # Second pass: extract images with better error handling
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    image_list = page.get_images()
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            
                            # Check if document is still open
                            if doc.is_closed:
                                print(f"Document closed while processing image {img_index} on page {page_num + 1}")
                                break
                            
                            pix = fitz.Pixmap(doc, xref)
                            
                            # Skip if pixmap is invalid
                            if not pix or pix.width == 0 or pix.height == 0:
                                if pix:
                                    pix = None
                                continue
                            
                            # Convert CMYK to RGB if needed
                            if pix.n - pix.alpha == 4:  # CMYK
                                try:
                                    rgb_pix = fitz.Pixmap(fitz.csRGB, pix)
                                    pix = rgb_pix
                                except:
                                    pix = None
                                    continue
                            
                            # Only process GRAY or RGB images with reasonable size
                            if pix and pix.n - pix.alpha < 4 and pix.width > 10 and pix.height > 10:
                                try:
                                    img_data = pix.tobytes("png")
                                    img_base64 = base64.b64encode(img_data).decode()
                                    
                                    # Only run OCR on smaller images to avoid memory issues
                                    ocr_text = ""
                                    if pix.width * pix.height < 1000000:  # 1 megapixel limit
                                        ocr_text = self._extract_text_from_image(pix)
                                    
                                    images.append({
                                        "page": page_num + 1,
                                        "index": img_index,
                                        "base64": img_base64,
                                        "ocr_text": ocr_text
                                    })
                                except Exception as e:
                                    print(f"Error converting image to PNG on page {page_num + 1}: {e}")
                            
                            if pix:
                                pix = None
                                
                        except Exception as e:
                            print(f"Error processing image {img_index} on page {page_num + 1}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {e}")
                    continue
        
        finally:
            doc.close()
        
        text_chunks = self.text_splitter.split_text(all_text)
        
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "id": f"chunk_{i}",
                "content": chunk,
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "has_code": any(code['content'] in chunk for code in code_blocks),
                    "type": "text"
                }
            })
        
        for i, code in enumerate(code_blocks):
            chunks.append({
                "id": f"code_{i}",
                "content": f"Code block from page {code['page']}:\n```{code['language']}\n{code['content']}\n```",
                "metadata": {
                    "page": code['page'],
                    "language": code['language'],
                    "type": "code"
                }
            })
        
        for i, img in enumerate(images):
            if img['ocr_text']:
                chunks.append({
                    "id": f"image_{i}",
                    "content": f"Image from page {img['page']}: {img['ocr_text']}",
                    "metadata": {
                        "page": img['page'],
                        "type": "image",
                        "has_ocr": True
                    }
                })
        
        # Get total pages before closing
        total_pages = len(doc) if not doc.is_closed else 0
        
        return {
            "chunks": chunks,
            "total_pages": total_pages,
            "images": images,
            "code_blocks": code_blocks
        }
    
    def _extract_code_blocks(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        code_blocks = []
        processed_ranges = []  # Track what text ranges have already been processed
        
        # Define patterns in order of specificity (most specific first)
        patterns = [
            # Markdown code blocks (highest priority)
            (r'```(\w+)?\n(.*?)```', 'detected', self._validate_markdown),
            
            # DDS (Display File Source) patterns - very specific
            (r'(?:^A\s+.*(?:\n|$)){3,}', 'dds', self._validate_dds),  # 3+ A-spec lines
            
            # Free-format RPG patterns (before fixed-format)
            # Look for lines with RPG keywords or semicolons (free-format typically ends with ;)
            (r'(?:(?:DCL-[A-Z]+|END-[A-Z]+|BEGSR|ENDSR|EXSR|EVAL-?[A-Z]*|IF|ELSE|ELSEIF|ENDIF|DOW|DOU|ENDDO|FOR|ENDFOR|ITER|LEAVE|SELECT|WHEN|OTHER|ENDSL|MONITOR|ON-[A-Z]+|ENDMON|READ[A-Z]*|WRITE|UPDATE|DELETE|CHAIN|SETLL|SETGT|EXFMT|CALLP|RETURN|CLEAR|RESET|SORTA|XML-[A-Z]+|DATA-[A-Z]+|%[A-Z]+)[\s\(].*(?:\n|$))+', 'rpg', self._validate_free_format_rpg),
            # Also catch code with multiple semicolons (typical of free-format RPG)
            (r'(?:.*;\s*(?:\n|$)){3,}', 'rpg', self._validate_free_format_rpg),
            
            # RPG IV patterns - check for RPG-specific structures (fixed format)
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
                # Lower threshold for RPG/DDS since they can have short but valid code blocks
                min_length = 20 if language in ['rpg', 'dds', 'cl'] else 30
                if len(content) > min_length and validator(content, match.groups()):
                    code_blocks.append({
                        "page": page_num,
                        "language": language,
                        "content": content
                    })
                    processed_ranges.append((start, end))
        
        return code_blocks
    
    def _looks_like_code(self, content: str, language: str) -> bool:
        """Additional validation to ensure content looks like code"""
        lines = content.split('\n')
        
        # DDS validation - more comprehensive
        if language == 'dds':
            # Check for DDS keywords (case insensitive)
            dds_keywords = ['CF', 'SFLSIZ', 'SFLPAG', 'OVERLAY', 'ROLLUP', 'SFLDSP', 'SFLCTL', 'SFLCLR', 'DSPATR', 'SFLEND']
            content_upper = content.upper()
            has_keywords = any(keyword in content_upper for keyword in dds_keywords)
            
            # Check for A-spec lines (lines starting with 'A' followed by space or field position)
            a_spec_lines = len([line for line in lines if re.match(r'^A\s+', line.strip()) or re.match(r'^A\s*\w', line.strip())])
            
            return has_keywords or a_spec_lines >= 2
        
        # RPG validation - more comprehensive
        if language == 'rpg':
            rpg_keywords = ['DCL-', 'MONITOR', 'EVAL', 'CALLP', 'BEGSR', 'ENDSR', 'DSPATR', 'ENDMON']
            content_upper = content.upper()
            has_keywords = any(keyword in content_upper for keyword in rpg_keywords)
            
            # Check for RPG spec lines (H, D, F, P, C specs)
            spec_lines = len([line for line in lines if re.match(r'^[HDFRPC]\s+', line.strip())])
            
            return has_keywords or spec_lines >= 2
        
        # General code validation - check for code-like characteristics
        code_indicators = [
            len([line for line in lines if line.strip().startswith(('A ', 'H ', 'D ', 'F '))]) > 1,  # Spec lines
            content.count(';') > 2,  # Multiple statements
            content.count('(') > 2 and content.count(')') > 2,  # Function calls
            len([line for line in lines if re.match(r'^\s{2,}\w+', line)]) > 2,  # Consistent indentation
        ]
        
        return any(code_indicators)
    
    def _validate_markdown(self, content: str, match_groups) -> bool:
        """Validate markdown code blocks"""
        return len(content.strip()) > 10
    
    def _validate_dds(self, content: str, match_groups) -> bool:
        """Validate DDS code blocks"""
        dds_keywords = ['CF', 'SFLSIZ', 'SFLPAG', 'OVERLAY', 'ROLLUP', 'SFLDSP', 'SFLCTL', 'SFLCLR', 'DSPATR', 'SFLEND']
        content_upper = content.upper()
        has_keywords = any(keyword in content_upper for keyword in dds_keywords)
        
        # Check for A-spec lines
        lines = content.split('\n')
        a_spec_lines = len([line for line in lines if re.match(r'^A\s+', line.strip()) or re.match(r'^A\s*\w', line.strip())])
        
        return has_keywords or a_spec_lines >= 2
    
    def _validate_rpg(self, content: str, match_groups) -> bool:
        """Validate RPG code blocks (fixed format)"""
        rpg_keywords = ['DCL-', 'MONITOR', 'EVAL', 'CALLP', 'BEGSR', 'ENDSR', 'DSPATR', 'ENDMON']
        content_upper = content.upper()
        has_keywords = any(keyword in content_upper for keyword in rpg_keywords)
        
        # Check for RPG spec lines
        lines = content.split('\n')
        spec_lines = len([line for line in lines if re.match(r'^[HDFRPC]\s+', line.strip())])
        
        return has_keywords or spec_lines >= 1
    
    def _validate_free_format_rpg(self, content: str, match_groups) -> bool:
        """Validate free-format RPG code blocks"""
        # Free-format RPG keywords
        free_format_keywords = [
            'DCL-S', 'DCL-DS', 'DCL-PI', 'DCL-PR', 'DCL-C', 'DCL-PROC', 'END-DS', 'END-PI', 'END-PR', 'END-PROC',
            'BEGSR', 'ENDSR', 'EXSR',
            'IF', 'ELSE', 'ELSEIF', 'ENDIF',
            'DOW', 'DOU', 'ENDDO', 'FOR', 'ENDFOR', 'ITER', 'LEAVE',
            'SELECT', 'WHEN', 'OTHER', 'ENDSL',
            'MONITOR', 'ON-ERROR', 'ON-EXIT', 'ENDMON',
            'EVAL', 'EVAL-CORR', 'EVALR',
            'READ', 'READE', 'READPE', 'READP', 'READC', 'CHAIN', 'SETLL', 'SETGT',
            'WRITE', 'UPDATE', 'DELETE', 'EXFMT',
            'CALLP', 'RETURN',
            'CLEAR', 'RESET', 'SORTA',
            'XML-INTO', 'XML-SAX', 'DATA-INTO', 'DATA-GEN'
        ]
        
        # Also check for built-in functions (BIFs) starting with %
        bif_pattern = r'%[A-Z]+\('
        
        content_upper = content.upper()
        
        # Count keyword occurrences
        keyword_count = sum(1 for keyword in free_format_keywords if keyword in content_upper)
        
        # Check for BIFs
        has_bifs = re.search(bif_pattern, content_upper) is not None
        
        # Free-format RPG typically has semicolons at end of statements
        has_semicolons = content.count(';') >= 2
        
        # Must have at least 2 keywords or 1 keyword + BIFs or semicolons
        return keyword_count >= 2 or (keyword_count >= 1 and (has_bifs or has_semicolons))
    
    def _validate_sql(self, content: str, match_groups) -> bool:
        """Validate SQL code blocks"""
        return len(content.strip()) > 15 and any(keyword in content.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'])
    
    def _validate_cl(self, content: str, match_groups) -> bool:
        """Validate CL (Control Language) code blocks"""
        cl_commands = ['CRTPF', 'ADDPFM', 'CHGPF', 'DLTPF', 'DSPFD', 'WRKACTJOB', 'STRPDM']
        return any(cmd in content.upper() for cmd in cl_commands)
    
    def _validate_general_code(self, content: str, match_groups) -> bool:
        """Validate general programming code blocks"""
        return len(content.strip()) > 20
    
    def _validate_indented_code(self, content: str, match_groups) -> bool:
        """Validate indented code blocks"""
        lines = content.split('\n')
        return len(lines) >= 3 and all(line.startswith('    ') or line.strip() == '' for line in lines)
    
    def _extract_text_from_image(self, pixmap) -> str:
        try:
            img_data = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""