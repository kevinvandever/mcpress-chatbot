import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio

class PDFProcessorTextOnly:
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
        try:
            doc = fitz.open(file_path)
            
            all_text = ""
            code_blocks = []
            chunks = []
            total_pages = len(doc)
            
            # Extract text from each page
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text.strip():  # Only add pages with content
                        all_text += f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"
                        
                        # Extract code blocks from this page
                        page_code_blocks = self._extract_code_blocks(page_text, page_num + 1)
                        code_blocks.extend(page_code_blocks)
                        
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {e}")
                    continue
            
            # Close document immediately after text extraction
            doc.close()
            
            if not all_text.strip():
                return {
                    "chunks": [{
                        "id": "error_chunk",
                        "content": f"Could not extract text from PDF: {file_path}",
                        "metadata": {"type": "error", "chunk_index": 0, "total_chunks": 1}
                    }],
                    "total_pages": total_pages,
                    "images": [],
                    "code_blocks": []
                }
            
            # Split text into chunks
            text_chunks = self.text_splitter.split_text(all_text)
            
            # Create text chunks
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
            
            # Add code blocks as separate chunks
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
            
            print(f"Successfully processed PDF: {total_pages} pages, {len(chunks)} chunks created")
            
            return {
                "chunks": chunks,
                "total_pages": total_pages,
                "images": [],  # No image processing for now
                "code_blocks": code_blocks
            }
            
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")
            return {
                "chunks": [{
                    "id": "error_chunk",
                    "content": f"Error processing PDF: {str(e)}",
                    "metadata": {"type": "error", "chunk_index": 0, "total_chunks": 1}
                }],
                "total_pages": 0,
                "images": [],
                "code_blocks": []
            }
    
    def _extract_code_blocks(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        code_blocks = []
        
        # Patterns for detecting code blocks
        patterns = [
            # Markdown code blocks
            (r'```(\w+)?\n(.*?)```', 'detected'),
            # Indented code (4+ spaces)
            (r'^    .+(?:\n    .+)*', 'generic'),
            # Python-specific patterns
            (r'^\s*(?:def|class|import|from|if __name__|for|while|try|except)\s+.*(?:\n.*)*?(?=\n\s*$|\n[^\s]|\Z)', 'python'),
            # Function calls and assignments
            (r'^\s*\w+\s*=\s*\w+\(.*\).*', 'python'),
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
                    
                    # Clean up the content
                    content = content.strip()
                    
                    # Only include substantial code blocks
                    if len(content) > 30 and '\n' in content:
                        code_blocks.append({
                            "page": page_num,
                            "language": language,
                            "content": content
                        })
                except Exception as e:
                    print(f"Error extracting code block: {e}")
                    continue
        
        return code_blocks