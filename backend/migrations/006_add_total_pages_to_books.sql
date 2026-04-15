-- Migration 006: Add total_pages column to books table
-- Required by the ingestion service to store page count from PDF processing

ALTER TABLE books ADD COLUMN IF NOT EXISTS total_pages INTEGER;
