#!/bin/bash

# Set only required environment variables for local ChromaDB setup
export OPENAI_API_KEY="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"

# Start backend
cd /Users/kevinvandever/kev-dev/pdf-chatbot
python -m backend.main