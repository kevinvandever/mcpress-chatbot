"""
Asynchronous upload handler to prevent timeouts
"""
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List
import time

# Store upload jobs
upload_jobs: Dict[str, Dict[str, Any]] = {}

async def process_pdf_async(job_id: str, file_path: str, pdf_processor, vector_store, category_mapper):
    """Process PDF in background"""
    try:
        upload_jobs[job_id]['status'] = 'processing'
        upload_jobs[job_id]['message'] = 'Extracting content from PDF...'
        
        # Process PDF
        extracted_content = await pdf_processor.process_pdf(file_path)
        
        upload_jobs[job_id]['message'] = 'Adding to vector store...'
        
        # Get metadata
        filename = os.path.basename(file_path)
        title = filename.replace('.pdf', '')
        category = category_mapper.get_category(filename)
        author = extracted_content.get("author", "Unknown")
        
        # Add to vector store
        await vector_store.add_documents(
            extracted_content["chunks"],
            metadata={
                "filename": filename,
                "title": title,
                "author": author,
                "category": category,
                "page_count": extracted_content["total_pages"],
                "has_images": len(extracted_content.get("images", [])) > 0,
                "has_code": len(extracted_content.get("code_blocks", [])) > 0
            }
        )
        
        upload_jobs[job_id]['status'] = 'completed'
        upload_jobs[job_id]['message'] = f'Successfully uploaded {filename}'
        upload_jobs[job_id]['result'] = {
            "filename": filename,
            "chunks_created": len(extracted_content["chunks"]),
            "total_pages": extracted_content["total_pages"]
        }
        
    except Exception as e:
        upload_jobs[job_id]['status'] = 'failed'
        upload_jobs[job_id]['message'] = f'Error: {str(e)}'
        upload_jobs[job_id]['error'] = str(e)

def create_upload_job(filename: str) -> str:
    """Create a new upload job"""
    job_id = f"job_{int(time.time())}_{filename[:20]}"
    upload_jobs[job_id] = {
        "job_id": job_id,
        "filename": filename,
        "status": "queued",
        "message": "Upload queued",
        "created_at": time.time()
    }
    return job_id

def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of an upload job"""
    return upload_jobs.get(job_id, {"status": "not_found", "message": "Job not found"})

def cleanup_old_jobs():
    """Remove jobs older than 1 hour"""
    current_time = time.time()
    to_remove = []
    for job_id, job in upload_jobs.items():
        if current_time - job.get('created_at', 0) > 3600:  # 1 hour
            to_remove.append(job_id)
    for job_id in to_remove:
        del upload_jobs[job_id]