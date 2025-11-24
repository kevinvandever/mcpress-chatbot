-- Rollback Migration 003: Multi-Author Metadata Enhancement
-- Feature: multi-author-metadata-enhancement
-- Created: 2025-11-24

-- =====================================================
-- WARNING: This rollback will lose multi-author data
-- =====================================================

-- Drop triggers
DROP TRIGGER IF EXISTS update_authors_updated_at_trigger ON authors;
DROP FUNCTION IF EXISTS update_authors_updated_at();

-- Drop indexes
DROP INDEX IF EXISTS idx_document_authors_order;
DROP INDEX IF EXISTS idx_document_authors_author;
DROP INDEX IF EXISTS idx_document_authors_book;
DROP INDEX IF EXISTS idx_authors_name;

-- Drop tables (cascade will remove foreign key constraints)
DROP TABLE IF EXISTS document_authors CASCADE;
DROP TABLE IF EXISTS authors CASCADE;

-- Remove columns from books table
ALTER TABLE books
DROP COLUMN IF EXISTS document_type;

ALTER TABLE books
DROP COLUMN IF EXISTS article_url;

-- Note: mc_press_url is preserved as it existed before this migration
-- Note: The original author column should be restored from backup if needed
