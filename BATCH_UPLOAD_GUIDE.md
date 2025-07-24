# Batch Upload Feature Guide

## Overview
The PDF Chatbot now supports batch uploading of multiple PDFs with concurrent processing, progress tracking, and automatic categorization.

## Features Implemented

### 1. Backend API Endpoints
- **POST `/batch-upload`**: Upload multiple PDF files
  - Processes up to 3 files concurrently to avoid overwhelming the system
  - Automatically categorizes PDFs based on filename patterns
  - Returns a batch ID for tracking progress
  
- **GET `/batch-upload/status/{batch_id}`**: Check batch upload progress
  - Real-time progress updates for each file
  - Overall batch progress percentage
  - Detailed statistics for each processed file

### 2. Frontend Components
- **BatchUpload Component** (`/frontend/components/BatchUpload.tsx`)
  - Drag-and-drop interface for multiple files
  - Real-time progress monitoring
  - Individual file status tracking
  - Summary statistics upon completion
  - Error handling and retry capabilities

### 3. Categorization System
PDFs are automatically categorized based on filename patterns:
- **Documentation**: Files containing "manual", "guide", "documentation"
- **Tutorial**: Files containing "tutorial", "learning", "course"
- **Reference**: Files containing "reference", "api", "specification"
- **Technical**: Default category for all other files

### 4. Enhanced Metadata
Each uploaded PDF now includes:
- Title (extracted from filename)
- Category
- Upload batch ID
- Upload timestamp
- Page count
- Image count
- Code block count

## How to Use

### Starting the Servers
```bash
cd /Users/kevinvandever/kev-dev/pdf-chatbot
./start_servers.sh
```

### Using the Batch Upload UI
1. Open http://localhost:3000 in your browser
2. Click on the "Batch" tab in the sidebar
3. Drag and drop up to 113 PDFs onto the upload area
4. Click "Upload X Files" to start processing
5. Monitor real-time progress for each file
6. View summary statistics when complete

### Testing Batch Upload
```bash
cd /Users/kevinvandever/kev-dev/pdf-chatbot/backend
python test_batch_upload.py
```

## Technical Details

### Concurrency Control
- Processes up to 3 PDFs simultaneously
- Adds 1-second delay after every 3 files to prevent system overload
- Each PDF is processed in its own async task

### Progress Tracking
- Real-time updates stored in memory
- File-level progress: uploading → processing → completed/error
- Overall batch progress calculated as percentage of completed files

### Error Handling
- Individual file failures don't stop the batch
- Failed files are tracked separately
- Detailed error messages for debugging

## API Examples

### Batch Upload Request
```bash
curl -X POST http://localhost:8000/batch-upload \
  -F "files=@book1.pdf" \
  -F "files=@book2.pdf" \
  -F "files=@book3.pdf"
```

### Check Progress
```bash
curl http://localhost:8000/batch-upload/status/batch_1234567890
```

## Next Steps
- Add support for more file formats (EPUB, DOCX)
- Implement batch operations (delete, export)
- Add advanced categorization using AI
- Create upload presets for common document types
- Add batch processing history and analytics