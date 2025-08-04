#!/bin/bash
# Install heavy dependencies at runtime if not present
if ! python -c "import sentence_transformers" 2>/dev/null; then
    echo "Installing ML dependencies at runtime..."
    pip install sentence-transformers numpy pandas pdfplumber
    echo "ML dependencies installed!"
fi

# Start the application
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT