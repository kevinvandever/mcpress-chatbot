#!/usr/bin/env python3
"""
Debug script to analyze book metadata Excel file structure
Run this on Railway to see what's actually in the Excel file
"""

import os
import sys
import asyncio
import pandas as pd
from pathlib import Path

# Add backend to path for imports
sys.path.append('/app/backend')

async def debug_book_excel():
    """Debug the book metadata Excel file"""
    
    # File path on Railway (you'll need to upload it there)
    file_path = "/tmp/book-metadata.xlsm"
    
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        print("Please upload the file to Railway first")
        return
    
    try:
        # Read the Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        
        print(f"=== BOOK METADATA EXCEL DEBUG ===")
        print(f"File: {file_path}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        print(f"\n=== COLUMN DATA TYPES ===")
        for col in df.columns:
            print(f"  {col}: {df[col].dtype}")
        
        print(f"\n=== FIRST 5 ROWS ===")
        for idx, row in df.head().iterrows():
            print(f"\nRow {idx + 1}:")
            for col in df.columns:
                val = row[col]
                print(f"  {col}: {repr(val)} (type: {type(val)})")
        
        print(f"\n=== URL COLUMN ANALYSIS ===")
        if 'URL' in df.columns:
            url_col = df['URL']
            print(f"URL column dtype: {url_col.dtype}")
            print(f"Non-null values: {url_col.notna().sum()}")
            print(f"Null values: {url_col.isna().sum()}")
            print(f"Unique values (first 10): {url_col.unique()[:10]}")
            
            # Check for URLs that might be stored as text
            for idx, val in enumerate(url_col.head(10)):
                print(f"  Row {idx+1} URL: {repr(val)} -> {repr(str(val))}")
        else:
            print("No 'URL' column found!")
            print("Available columns:", list(df.columns))
            
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_book_excel())