import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio

class PDFProcessorSimple:
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
        code_blocks = []
        chunks = []
        
        try:
            # Extract text and code blocks only (skip images for now)
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                all_text += f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"
                code_blocks.extend(self._extract_code_blocks(page_text, page_num + 1))
        
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
        
        return {
            "chunks": chunks,
            "total_pages": len(doc),
            "images": [],  # No images for now
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