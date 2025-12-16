#!/usr/bin/env python3

import pandas as pd
import sys

def debug_excel_file(file_path):
    """Debug Excel file to see actual column names and data"""
    try:
        # Read the Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        
        print(f"File: {file_path}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print("\nFirst few rows:")
        print(df.head())
        
        print("\nColumn data types:")
        print(df.dtypes)
        
        print("\nFirst row data:")
        for col in df.columns:
            val = df.iloc[0][col] if len(df) > 0 else None
            print(f"  {col}: {repr(val)} (type: {type(val)})")
            
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    file_path = ".kiro/specs/multi-author-metadata-enhancement/data/book-metadata.xlsm"
    debug_excel_file(file_path)