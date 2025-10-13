## Story-005 Integration Guide

### Overview
This document explains how to integrate the new Document Processing Pipeline into main.py without disrupting existing functionality.

---

## Phase 1: Add New Service (No Breaking Changes)

### 1. Add imports to main.py

After existing imports (around line 125), add:

```python
# Story-005: Document Processing Pipeline
try:
    from processing_integration import (
        init_processing_service,
        processing_router,
        get_processing_service
    )
    PROCESSING_PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Story-005 processing pipeline not available: {e}")
    PROCESSING_PIPELINE_AVAILABLE = False
    processing_router = None
```

### 2. Initialize service on startup

In the `startup_event()` function (around line 332), add:

```python
@app.on_event("startup")
async def startup_event():
    # ... existing code ...

    # Story-005: Initialize processing service
    if PROCESSING_PIPELINE_AVAILABLE:
        try:
            processing_service = init_processing_service(vector_store, pdf_processor)
            print("✅ Document Processing Service ready")
        except Exception as e:
            print(f"⚠️  Could not initialize processing service: {e}")
```

### 3. Include new API routes

After other router includes (around line 295), add:

```python
# Include Story-005 processing routes
if PROCESSING_PIPELINE_AVAILABLE and processing_router:
    app.include_router(processing_router)
    print("✅ Processing pipeline endpoints enabled at /api/process/*")
```

---

## Phase 2: Feature Flag for New Upload Endpoint

### 4. Add environment variable for feature flag

Add to your .env or Railway environment:

```bash
# Enable new processing pipeline for uploads
USE_NEW_PROCESSING_PIPELINE=false  # Set to true to enable
```

### 5. Create new upload endpoint using new service

Add this new endpoint to main.py (around line 928, near `/upload-async`):

```python
@app.post("/upload-v2")
async def upload_pdf_v2(file: UploadFile = File(...)):
    """
    Upload PDF using new processing pipeline (Story-005)
    Feature flag: USE_NEW_PROCESSING_PIPELINE
    """
    use_new_pipeline = os.getenv("USE_NEW_PROCESSING_PIPELINE", "false").lower() == "true"

    if not use_new_pipeline or not PROCESSING_PIPELINE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="New processing pipeline not enabled. Use /upload-async instead."
        )

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Save file
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Get processing service
        processing_service = get_processing_service()
        if not processing_service:
            raise HTTPException(status_code=500, detail="Processing service not initialized")

        # Get metadata
        category = category_mapper.get_category(file.filename)
        metadata = {
            "filename": file.filename,
            "category": category,
            "title": file.filename.replace('.pdf', '')
        }

        # Start processing
        job = await processing_service.process_document(
            file_path=file_path,
            filename=file.filename,
            metadata=metadata
        )

        return {
            "status": "success",
            "job_id": job.job_id,
            "message": f"Processing started for {file.filename}",
            "check_status_url": f"/api/process/job/{job.job_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Phase 3: Testing

### 6. Test new endpoints

```bash
# Check health
curl http://localhost:8000/api/process/health

# Upload a file using new pipeline
curl -X POST -F "file=@test.pdf" http://localhost:8000/upload-v2

# Check job status
curl http://localhost:8000/api/process/job/{job_id}

# List all jobs
curl http://localhost:8000/api/process/jobs

# Get storage metrics
curl http://localhost:8000/api/process/metrics
```

---

## Rollback Plan

If issues occur:

### Option 1: Disable via Feature Flag
Set environment variable:
```bash
USE_NEW_PROCESSING_PIPELINE=false
```

### Option 2: Remove Router
Comment out in main.py:
```python
# app.include_router(processing_router)
```

### Option 3: Database Rollback
```bash
cd backend
python run_migration.py rollback
```

This removes the new tables but preserves existing documents table.

---

## New API Endpoints

All endpoints are prefixed with `/api/process`:

- `POST /api/process/document` - Start processing a document
- `GET /api/process/job/{job_id}` - Get job status and events
- `POST /api/process/retry/{job_id}` - Retry a failed job
- `DELETE /api/process/job/{job_id}` - Cancel a job
- `GET /api/process/jobs` - List all jobs (with pagination)
- `POST /api/process/cleanup` - Clean up old jobs
- `GET /api/process/metrics` - Get storage metrics
- `GET /api/process/health` - Health check

---

## Migration Strategy

### Week 1: Add Infrastructure
- ✅ Add new tables (run migration)
- ✅ Add DocumentProcessingService
- ✅ Keep async_upload.py functional (backward compatibility)

### Week 2: Gradual Migration
- Route new uploads through `/upload-v2`
- Monitor both systems in parallel
- Validate job tracking works

### Week 3: Full Cutover
- Switch feature flag: `USE_NEW_PROCESSING_PIPELINE=true`
- Update `/upload-async` to use new service
- Deprecate old async_upload.py

---

## Success Criteria

- [ ] All new endpoints return 200 status
- [ ] Jobs are persisted to database (survive restarts)
- [ ] Error recovery works (check retry_count in jobs)
- [ ] Webhooks deliver (if configured)
- [ ] Storage metrics show accurate data
- [ ] Old `/upload-async` endpoint still works
- [ ] No errors in Railway logs
