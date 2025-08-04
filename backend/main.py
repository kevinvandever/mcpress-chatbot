import os
import warnings
# Set tokenizer environment variable to suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Suppress specific warnings that clutter logs
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*tokenizers.*")

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import time

from backend.pdf_processor_full import PDFProcessorFull
from backend.vector_store import VectorStore
from backend.chat_handler import ChatHandler
from backend.category_mapper import get_category_mapper

load_dotenv()

app = FastAPI(title="MC Press Chatbot API")

# Temporary storage for PDFs awaiting metadata
temp_storage = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "https://frontend-qwnql4s2j0s-kevin-vandevers-projects.vercel.app",
        "https://frontend-cwanq0nz1-kevin-vandevers-projects.vercel.app",
        os.getenv("CORS_ORIGIN", "*")  # Allow environment override
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_processor = PDFProcessorFull()
vector_store = VectorStore()

# Initialize the database on startup
@app.on_event("startup")
async def startup_event():
    await vector_store.init_database()
chat_handler = ChatHandler(vector_store)
category_mapper = get_category_mapper()

# Global upload progress tracking
upload_progress = {}

# Thread pool for concurrent processing
executor = ThreadPoolExecutor(max_workers=3)

class ChatMessage(BaseModel):
    message: str
    conversation_id: str = "default"

class ProcessingStatus(BaseModel):
    status: str
    message: str
    progress: int = 0

class BatchUploadProgress(BaseModel):
    batch_id: str
    total_files: int
    processed_files: int
    current_file: Optional[str] = None
    files_status: Dict[str, Dict[str, Any]] = {}
    overall_progress: int = 0
    status: str = "processing"

@app.get("/")
def read_root():
    return {"message": "MC Press Chatbot API is running"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
    if file.size > max_size:
        raise HTTPException(status_code=400, detail=f"File size exceeds {max_size}MB limit")
    
    try:
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        extracted_content = await pdf_processor.process_pdf(file_path)
        
        # Get category from CSV mapping
        category = category_mapper.get_category(file.filename)
        
        # Check if author metadata is missing
        author = extracted_content.get("author")
        needs_author = author is None or author == ""
        
        print(f"📝 Upload status for {file.filename}: Author = '{author}', Needs author = {needs_author}")
        
        if needs_author:
            # Store the document temporarily without adding to vector store
            temp_storage[file.filename] = {
                "extracted_content": extracted_content,
                "category": category,
                "file_path": file_path
            }
            
            print(f"💾 Stored {file.filename} in temporary storage awaiting author metadata")
            print(f"📊 File stats: {len(extracted_content['chunks'])} chunks, {extracted_content['total_pages']} pages")
            
            return {
                "status": "needs_metadata",
                "message": f"Author information could not be automatically extracted from {file.filename}. Please provide the author name to complete the upload.",
                "filename": file.filename,
                "needs_author": True,
                "chunks_created": len(extracted_content["chunks"]),
                "images_processed": len(extracted_content["images"]),
                "code_blocks_found": len(extracted_content["code_blocks"]),
                "total_pages": extracted_content["total_pages"],
                "extraction_details": "Author extraction attempted using PDF metadata and text analysis patterns"
            }
        else:
            # Author exists, proceed normally
            await vector_store.add_documents(
                documents=extracted_content["chunks"],
                metadata={
                    "filename": file.filename,
                    "total_pages": extracted_content["total_pages"],
                    "has_images": len(extracted_content["images"]) > 0,
                    "has_code": len(extracted_content["code_blocks"]) > 0,
                    "category": category,
                    "title": file.filename.replace('.pdf', ''),
                    "author": author
                }
            )
            
            return {
                "status": "success",
                "message": f"Successfully processed {file.filename}",
                "chunks_created": len(extracted_content["chunks"]),
                "images_processed": len(extracted_content["images"]),
                "code_blocks_found": len(extracted_content["code_blocks"]),
                "total_pages": extracted_content["total_pages"]
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_single_pdf(file_content: bytes, filename: str, batch_id: str, file_index: int, total_files: int):
    """Process a single PDF file as part of a batch"""
    try:
        # Update progress: uploading
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "uploading",
            "progress": 0,
            "message": "Uploading..."
        }
        
        # Save file
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Update progress: processing
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "processing",
            "progress": 30,
            "message": "Processing PDF..."
        }
        upload_progress[batch_id]["current_file"] = filename
        
        # Process PDF
        extracted_content = await pdf_processor.process_pdf(file_path)
        
        # Get metadata and category from CSV mapping
        title = filename.replace('.pdf', '')
        category = category_mapper.get_category(filename)
        
        # Add to vector store with enhanced metadata (with batch splitting for large documents)
        chunks_count = len(extracted_content["chunks"])
        print(f"Adding {chunks_count} chunks to vector store for {filename}")
        
        # Check if author metadata is missing
        author = extracted_content.get("author")
        needs_author = author is None or author == ""
        
        print(f"📝 Batch upload status for {filename}: Author = '{author}', Needs author = {needs_author}")
        
        if needs_author:
            # Store temporarily and mark as needing metadata
            temp_storage[filename] = {
                "extracted_content": extracted_content,
                "category": category,
                "file_path": file_path,
                "batch_id": batch_id
            }
            
            # Update progress with special status
            upload_progress[batch_id]["files_status"][filename] = {
                "status": "needs_metadata",
                "progress": 90,
                "message": "Author extraction failed - manual input required",
                "stats": {
                    "chunks_created": len(extracted_content["chunks"]),
                    "images_processed": len(extracted_content["images"]),
                    "code_blocks_found": len(extracted_content["code_blocks"]),
                    "total_pages": extracted_content["total_pages"],
                    "category": category
                },
                "extraction_details": "Author extraction attempted using PDF metadata and text patterns"
            }
            print(f"📋 File {filename} needs author metadata - stored in temp_storage")
            return "needs_metadata"
        
        try:
            await vector_store.add_documents(
                documents=extracted_content["chunks"],
                metadata={
                    "filename": filename,
                    "title": title,
                    "category": category,
                    "author": author,
                    "total_pages": extracted_content["total_pages"],
                    "has_images": len(extracted_content["images"]) > 0,
                    "has_code": len(extracted_content["code_blocks"]) > 0,
                    "upload_batch": batch_id,
                    "upload_timestamp": time.time()
                }
            )
            print(f"Successfully added all {chunks_count} chunks for {filename}")
        except Exception as e:
            print(f"Error adding chunks to vector store for {filename}: {str(e)}")
            raise
        
        # Update progress: completed
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "completed",
            "progress": 100,
            "message": "Processing complete",
            "stats": {
                "chunks_created": len(extracted_content["chunks"]),
                "images_processed": len(extracted_content["images"]),
                "code_blocks_found": len(extracted_content["code_blocks"]),
                "total_pages": extracted_content["total_pages"],
                "category": category
            }
        }
        
        upload_progress[batch_id]["processed_files"] += 1
        upload_progress[batch_id]["overall_progress"] = int(
            (upload_progress[batch_id]["processed_files"] / total_files) * 100
        )
        
        return True
        
    except Exception as e:
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "error",
            "progress": 0,
            "message": str(e)
        }
        return False

@app.post("/batch-upload")
async def batch_upload_pdfs(files: List[UploadFile] = File(...)):
    """Upload and process multiple PDF files concurrently"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate all files are PDFs
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF file")
    
    # Create batch ID
    batch_id = f"batch_{int(time.time())}"
    
    # Initialize progress tracking
    upload_progress[batch_id] = {
        "batch_id": batch_id,
        "total_files": len(files),
        "processed_files": 0,
        "current_file": None,
        "files_status": {},
        "overall_progress": 0,
        "status": "processing"
    }
    
    # Read all files first to avoid file handle issues
    print(f"Reading {len(files)} files into memory...")
    file_data = []
    total_size = 0
    max_batch_size = int(os.getenv("MAX_BATCH_SIZE_MB", 500)) * 1024 * 1024  # 500MB default
    
    for file in files:
        content = await file.read()
        file_size = len(content)
        total_size += file_size
        
        # Check individual file size
        max_file_size = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
        if file_size > max_file_size:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} exceeds {max_file_size/(1024*1024):.0f}MB limit"
            )
        
        # Check total batch size
        if total_size > max_batch_size:
            raise HTTPException(
                status_code=400, 
                detail=f"Total batch size exceeds {max_batch_size/(1024*1024):.0f}MB limit"
            )
        
        file_data.append((content, file.filename))
    
    print(f"All files read successfully. Total size: {total_size/(1024*1024):.2f}MB")

    # Process files concurrently with rate limiting
    async def process_batch():
        tasks = []
        for i, (content, filename) in enumerate(file_data):
            # Add delay between files to avoid overwhelming the system
            if i > 0 and i % 3 == 0:
                await asyncio.sleep(1)
            
            task = process_single_pdf(content, filename, batch_id, i, len(file_data))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update final status
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        upload_progress[batch_id]["status"] = "completed"
        upload_progress[batch_id]["summary"] = {
            "successful": successful,
            "failed": failed,
            "total": len(files)
        }
    
    # Start processing in background
    asyncio.create_task(process_batch())
    
    return {
        "batch_id": batch_id,
        "message": f"Started processing {len(files)} files",
        "status_url": f"/batch-upload/status/{batch_id}"
    }

@app.get("/batch-upload/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get the status of a batch upload"""
    if batch_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return upload_progress[batch_id]

class CompleteUploadRequest(BaseModel):
    filename: str
    author: str
    mc_press_url: Optional[str] = None

class UpdateMetadataRequest(BaseModel):
    filename: str
    title: str
    author: str
    category: Optional[str] = None
    mc_press_url: Optional[str] = None

@app.post("/complete-upload")
async def complete_upload_with_metadata(request: CompleteUploadRequest):
    """Complete the upload of a PDF that was missing author metadata"""
    print(f"Complete upload request for: '{request.filename}'")
    print(f"Current temp_storage keys: {list(temp_storage.keys())}")
    
    if request.filename not in temp_storage:
        raise HTTPException(status_code=404, detail=f"File '{request.filename}' not found in temporary storage. Available files: {list(temp_storage.keys())}")
    
    try:
        # Retrieve stored data
        stored_data = temp_storage[request.filename]
        extracted_content = stored_data["extracted_content"]
        category = stored_data["category"]
        
        # Add to vector store with provided author and URL
        await vector_store.add_documents(
            documents=extracted_content["chunks"],
            metadata={
                "filename": request.filename,
                "total_pages": extracted_content["total_pages"],
                "has_images": len(extracted_content["images"]) > 0,
                "has_code": len(extracted_content["code_blocks"]) > 0,
                "category": category,
                "title": request.filename.replace('.pdf', ''),
                "author": request.author,
                "mc_press_url": request.mc_press_url
            }
        )
        
        # Clean up temp storage
        del temp_storage[request.filename]
        
        return {
            "status": "success",
            "message": f"Successfully processed {request.filename} with author: {request.author}",
            "chunks_created": len(extracted_content["chunks"]),
            "total_pages": extracted_content["total_pages"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/documents/{filename}/metadata")
async def update_document_metadata(filename: str, request: UpdateMetadataRequest):
    """Update the title, author, category, and MC Press URL metadata for a document"""
    try:
        await vector_store.update_document_metadata(filename, request.title, request.author, request.category, request.mc_press_url)
        return {
            "status": "success",
            "message": f"Successfully updated metadata for {filename}",
            "title": request.title,
            "author": request.author,
            "category": request.category
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(message: ChatMessage):
    async def generate():
        async for chunk in chat_handler.stream_response(
            message.message, 
            message.conversation_id
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/search")
async def search_documents(q: str, n_results: int = 5, filename: str = None, content_types: str = None):
    try:
        book_filter = [filename] if filename else None
        type_filter = content_types.split(',') if content_types else None
        results = await vector_store.search(q, n_results=n_results, book_filter=book_filter, type_filter=type_filter)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    return await vector_store.list_documents()

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    try:
        await vector_store.delete_document(filename)
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_database():
    """Reset the entire database - use with caution!"""
    try:
        import shutil
        import os
        
        # Reset the vector store
        vector_store.reset_database()
        
        # Clean up uploads directory
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            shutil.rmtree(uploads_dir)
        os.makedirs(uploads_dir, exist_ok=True)
        
        return {"status": "success", "message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "vector_store": vector_store.is_connected(),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }