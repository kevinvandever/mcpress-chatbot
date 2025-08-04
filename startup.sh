#!/bin/bash
# Install heavy dependencies at runtime if not present
if ! python -c "import sentence_transformers" 2>/dev/null; then
    echo "Installing ML dependencies at runtime..."
    pip install sentence-transformers numpy pandas pdfplumber pytesseract
    echo "ML dependencies installed!"
fi

# Install system dependency for tesseract if needed
if ! command -v tesseract &> /dev/null; then
    echo "Installing tesseract-ocr..."
    apt-get update && apt-get install -y tesseract-ocr
fi

# Start the application
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT