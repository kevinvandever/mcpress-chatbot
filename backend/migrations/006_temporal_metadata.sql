-- Migration 006: Temporal Metadata for RPG Era Awareness
-- Feature: temporal-rag-anti-hallucination
-- Purpose: Adds publication_year and rpg_era columns to the books table
--          to support temporal re-ranking in the RAG pipeline.
--          This eliminates "era hallucinations" where the chatbot returns
--          RPG code from the wrong era (e.g., fixed-format when user asks
--          about modern free-form RPG).
-- Idempotent: Safe to run multiple times (uses IF NOT EXISTS).

-- Add publication year column (nullable — unknown for many older books)
ALTER TABLE books ADD COLUMN IF NOT EXISTS publication_year INTEGER;

-- Add RPG era classification column (defaults to 'general' for non-RPG content)
ALTER TABLE books ADD COLUMN IF NOT EXISTS rpg_era VARCHAR(20) DEFAULT 'general';

-- Index on rpg_era for efficient filtering during temporal re-ranking
CREATE INDEX IF NOT EXISTS idx_books_rpg_era ON books (rpg_era);
