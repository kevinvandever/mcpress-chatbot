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
        
        return {
            "chunks": chunks,
            "total_pages": len(doc),
            "images": images,
            "code_blocks": code_blocks
        }
    
    def _extract_code_blocks(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        code_blocks = []
        
        patterns = [
            (r'```(\w+)?\n(.*?)```', 'detected'),
            (r'    .*(?:\n    .*)*', 'python'),  # Indented code
            (r'^\s*(?:def|class|import|from|if|for|while)\s+.*$', 'python'),
        ]
        
        for pattern, default_lang in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                if len(match.groups()) > 1:
                    language = match.group(1) or default_lang
                    content = match.group(2)
                else:
                    language = default_lang
                    content = match.group(0)
                
                if len(content.strip()) > 20:  # Minimum code length
                    code_blocks.append({
                        "page": page_num,
                        "language": language,
                        "content": content.strip()
                    })
        
        return code_blocks
    
    def _extract_text_from_image(self, pixmap) -> str:
        try:
            img_data = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""