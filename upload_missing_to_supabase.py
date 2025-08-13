#!/usr/bin/env python3
"""
Upload missing PDFs directly to Supabase bypassing Railway migration
"""
import os
import glob
from pathlib import Path

# List all PDFs we have locally
pdf_dir = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"
pdf_files = glob.glob(f"{pdf_dir}/*.pdf")

print(f"📚 Found {len(pdf_files)} PDF files locally:")

# We know from the live app that we only have "Advanced, Integrated RPG.pdf"
# So we need to upload the other 114 files

current_doc = "Advanced, Integrated RPG.pdf"
missing_pdfs = []

for pdf_path in sorted(pdf_files):
    pdf_name = Path(pdf_path).name
    if pdf_name != current_doc:
        missing_pdfs.append(pdf_path)

print(f"✅ Current in Supabase: 1 document ({current_doc})")
print(f"📋 Missing from Supabase: {len(missing_pdfs)} documents")

# Show first 10 missing files
print(f"\nFirst 10 missing PDFs:")
for i, pdf_path in enumerate(missing_pdfs[:10]):
    pdf_name = Path(pdf_path).name
    print(f"  {i+1}. {pdf_name}")

if len(missing_pdfs) > 10:
    print(f"  ... and {len(missing_pdfs) - 10} more")

print(f"\n🎯 Plan: Upload {len(missing_pdfs)} missing PDFs directly to Supabase")
print("This will be much faster than migrating from Railway!")