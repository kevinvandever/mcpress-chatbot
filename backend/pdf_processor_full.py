import fitz  # PyMuPDF
import base64
import io
import re
from typing import List, Dict, Any
from PIL import Image
import pytesseract
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio
import os
from author_extractor import get_author_extractor

class PDFProcessorFull:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.author_extractor = get_author_extractor()
        
    async def process_pdf(self, file_path: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_pdf_sync, file_path)
    
    def _process_pdf_sync(self, file_path: str) -> Dict[str, Any]:
        filename = os.path.basename(file_path)
        
        try:
            # Open document once and extract all metadata first
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # Extract author information with debug logging
            print(f"🔍 Extracting author information for: {os.path.basename(file_path)}")
            author = self.author_extractor.extract_author(file_path)
            if author:
                print(f"✅ Author extracted: '{author}'")
            else:
                print(f"⚠️  No author found for: {os.path.basename(file_path)}")
            
            # First pass: Extract all text content
            all_text = ""
            page_texts = []
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    page_texts.append(page_text)
                    
                    if page_text.strip():
                        all_text += f"\n\n{page_text}"
                except Exception as e:
                    print(f"Error extracting text from page {page_num + 1}: {e}")
                    page_texts.append("")
            
            # Second pass: Extract images with better error handling
            images = []
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            # Create a new document reference for each image to avoid closure issues
                            img_doc = fitz.open(file_path)
                            
                            xref = img[0]
                            pix = fitz.Pixmap(img_doc, xref)
                            
                            # Skip invalid pixmaps
                            if not pix or pix.width <= 10 or pix.height <= 10:
                                if pix:
                                    pix = None
                                img_doc.close()
                                continue
                            
                            # Convert CMYK to RGB if needed
                            if pix.n - pix.alpha == 4:  # CMYK
                                try:
                                    rgb_pix = fitz.Pixmap(fitz.csRGB, pix)
                                    pix.drop()  # Clean up original pixmap
                                    pix = rgb_pix
                                except Exception as e:
                                    # Silently skip CMYK conversion issues - these are common and non-critical
                                    if pix:
                                        pix.drop()
                                    img_doc.close()
                                    continue
                            
                            # Handle other color spaces that can't be converted to PNG
                            if pix and pix.n - pix.alpha > 3:  # Not RGB or grayscale
                                try:
                                    # Try to convert to RGB
                                    rgb_pix = fitz.Pixmap(fitz.csRGB, pix)
                                    pix.drop()
                                    pix = rgb_pix
                                except Exception as e:
                                    # Silently skip colorspace conversion issues - these are common and non-critical
                                    if pix:
                                        pix.drop()
                                    img_doc.close()
                                    continue
                            
                            # Ensure we have a valid pixmap for PNG conversion
                            if pix and (pix.n - pix.alpha <= 3):  # RGB or grayscale
                                try:
                                    # Convert to PNG
                                    img_data = pix.tobytes("png")
                                    img_base64 = base64.b64encode(img_data).decode()
                                    
                                    # OCR for text extraction (limit size to avoid memory issues)
                                    ocr_text = ""
                                    if pix.width * pix.height < 2000000:  # 2MP limit
                                        ocr_text = self._extract_text_from_image(pix)
                                    
                                    images.append({
                                        "page": page_num + 1,
                                        "index": img_index,
                                        "base64": img_base64,
                                        "ocr_text": ocr_text,
                                        "width": pix.width,
                                        "height": pix.height,
                                        "book": filename  # Track which book this image came from
                                    })
                                    
                                except Exception as e:
                                    # Only log critical errors, not format conversion issues
                                    if "unsupported" not in str(e).lower() and "cannot" not in str(e).lower():
                                        print(f"Critical image processing error on page {page_num + 1}: {e}")
                            
                            # Clean up pixmap memory
                            if pix:
                                pix.drop()
                                pix = None
                            img_doc.close()
                            
                        except Exception as e:
                            # Only log non-trivial image processing errors
                            if "unsupported" not in str(e).lower() and "invalid" not in str(e).lower():
                                print(f"Image processing error {img_index} on page {page_num + 1}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Error processing images on page {page_num + 1}: {e}")
                    continue
            
            # Close the main document
            doc.close()
            
            # Extract code blocks from all text
            code_blocks = []
            for page_num, page_text in enumerate(page_texts):
                if page_text.strip():
                    page_code_blocks = self._extract_code_blocks(page_text, page_num + 1, filename)
                    code_blocks.extend(page_code_blocks)
            
            # Create chunks
            chunks = []
            
            if all_text.strip():
                # Text chunks with quality validation
                text_chunks = self.text_splitter.split_text(all_text)
                quality_chunks = []
                
                for i, chunk in enumerate(text_chunks):
                    chunk_content = chunk.strip()
                    
                    # Skip chunks that are too short
                    if len(chunk_content) < 50:
                        continue
                    
                    # Skip chunks that are primarily page separators or whitespace
                    lines = chunk_content.split('\n')
                    meaningful_lines = [line for line in lines 
                                     if line.strip() and not re.match(r'^---\s*Page\s+\d+\s*---\s*$', line.strip())]
                    meaningful_content = '\n'.join(meaningful_lines).strip()
                    
                    # Require substantial meaningful content
                    if len(meaningful_content) < 30:
                        continue
                    
                    # Calculate page information from chunk position
                    chunk_page = self._estimate_page_from_chunk(i, len(text_chunks), total_pages)
                    
                    quality_chunks.append({
                        "id": f"{filename}_chunk_{i}",
                        "content": chunk_content,
                        "metadata": {
                            "filename": filename,
                            "chunk_index": i,
                            "total_chunks": len(text_chunks),
                            "page": chunk_page,
                            "has_code": any(code['content'] in chunk_content for code in code_blocks),
                            "type": "text",
                            "book": filename,
                            "author": author,
                            "meaningful_length": len(meaningful_content),
                            "total_length": len(chunk_content)
                        }
                    })
                
                chunks.extend(quality_chunks)
                
                # Code block chunks
                for i, code in enumerate(code_blocks):
                    chunks.append({
                        "id": f"{filename}_code_{i}",
                        "content": f"Code block from {filename}, page {code['page']}:\n```{code['language']}\n{code['content']}\n```",
                        "metadata": {
                            "filename": filename,
                            "page": code['page'],
                            "language": code['language'],
                            "type": "code",
                            "book": filename,
                            "author": author
                        }
                    })
                
                # Image chunks (OCR text)
                for i, img in enumerate(images):
                    if img['ocr_text'].strip():
                        chunks.append({
                            "id": f"{filename}_image_{i}",
                            "content": f"Image from {filename}, page {img['page']}: {img['ocr_text']}",
                            "metadata": {
                                "filename": filename,
                                "page": img['page'],
                                "type": "image",
                                "has_ocr": True,
                                "book": filename,
                                "author": author,
                                "image_index": i
                            }
                        })
            
            print(f"Successfully processed {filename}: {total_pages} pages, {len(chunks)} chunks, {len(images)} images, {len(code_blocks)} code blocks")
            
            return {
                "chunks": chunks,
                "total_pages": total_pages,
                "images": images,
                "code_blocks": code_blocks,
                "author": author
            }
            
        except Exception as e:
            print(f"Error processing PDF {filename}: {e}")
            return {
                "chunks": [{
                    "id": f"{filename}_error",
                    "content": f"Error processing {filename}: {str(e)}",
                    "metadata": {"type": "error", "filename": filename, "book": filename}
                }],
                "total_pages": 0,
                "images": [],
                "code_blocks": []
            }
    
    def _extract_text_from_image(self, pixmap) -> str:
        try:
            img_data = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Use OCR to extract text
            text = pytesseract.image_to_string(img, config='--psm 6')
            return text.strip()
        except Exception as e:
            # OCR failures are common and non-critical - don't spam logs
            return ""
    
    def _extract_code_blocks(self, text: str, page_num: int, filename: str) -> List[Dict[str, Any]]:
        code_blocks = []
        
        patterns = [
            # Markdown code blocks
            (r'```(\w+)?\n(.*?)```', 'detected'),
            # Indented code (4+ spaces)
            (r'^    .+(?:\n    .+)*', 'generic'),
            # RPG/COBOL patterns
            (r'^\s*(?:H|F|D|P|C|O)\s+.*', 'rpg'),
            # SQL patterns
            (r'^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.*(?:\n.*)*?(?=;|\n\s*$)', 'sql'),
            # General programming patterns
            (r'^\s*(?:def|class|import|from|if __name__|for|while|try|except|function|var|let|const)\s+.*(?:\n.*)*?(?=\n\s*$|\n[^\s]|\Z)', 'programming'),
        ]
        
        for pattern, default_lang in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    if len(match.groups()) > 1:
                        language = match.group(1) or default_lang
                        content = match.group(2)
                    else:
                        language = default_lang
                        content = match.group(0)
                    
                    content = content.strip()
                    
                    # Only include substantial code blocks
                    if len(content) > 30:
                        code_blocks.append({
                            "page": page_num,
                            "language": language,
                            "content": content,
                            "book": filename
                        })
                except Exception as e:
                    print(f"Error extracting code block: {e}")
                    continue
        
        return code_blocks
    
    def _estimate_page_from_chunk(self, chunk_index: int, total_chunks: int, total_pages: int) -> int:
        """Estimate which page a chunk belongs to based on its position"""
        if total_chunks == 0 or total_pages == 0:
            return 1
        
        # Simple estimation: distribute chunks evenly across pages
        estimated_page = int((chunk_index / total_chunks) * total_pages) + 1
        return min(estimated_page, total_pages)