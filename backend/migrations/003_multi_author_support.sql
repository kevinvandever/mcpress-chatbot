-- Migration 003: Multi-Author Metadata Enhancement
-- Feature: multi-author-metadata-enhancement
-- Created: 2025-11-24

-- =====================================================
-- Authors Table
-- Stores unique author information
-- =====================================================
CREATE TABLE IF NOT EXISTS authors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    site_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for author name lookups
CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name);

COMMENT ON TABLE authors IS 'Stores unique author information with optional website URLs';
COMMENT ON COLUMN authors.name IS 'Author name - must be unique';
COMMENT ON COLUMN authors.site_url IS 'Optional URL to author website or profile';

-- =====================================================
-- Document Authors Junction Table
-- Many-to-many relationship between documents and authors
-- =====================================================
CREATE TABLE IF NOT EXISTS document_authors (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, author_id)
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_document_authors_book ON document_authors(book_id);
CREATE INDEX IF NOT EXISTS idx_document_authors_author ON document_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_document_authors_order ON document_authors(book_id, author_order);

COMMENT ON TABLE document_authors IS 'Junction table linking documents to authors with ordering';
COMMENT ON COLUMN document_authors.author_order IS 'Order of author in document (0 = first author)';
COMMENT ON CONSTRAINT document_authors_book_id_author_id_key ON document_authors IS 'Prevents duplicate author associations';

-- =====================================================
-- Books Table Modifications
-- Add document type and article URL fields
-- =====================================================

-- Add document_type column (book or article)
ALTER TABLE books
ADD COLUMN IF NOT EXISTS document_type TEXT NOT NULL DEFAULT 'book' CHECK (document_type IN ('book', 'article'));

-- Add article_url column for article documents
ALTER TABLE books
ADD COLUMN IF NOT EXISTS article_url TEXT;

-- Note: mc_press_url already exists in the books table

COMMENT ON COLUMN books.document_type IS 'Type of document: book or article';
COMMENT ON COLUMN books.article_url IS 'URL to online article (for article document type)';

-- =====================================================
-- Trigger function to update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_authors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for authors table
DROP TRIGGER IF EXISTS update_authors_updated_at_trigger ON authors;
CREATE TRIGGER update_authors_updated_at_trigger
    BEFORE UPDATE ON authors
    FOR EACH ROW
    EXECUTE FUNCTION update_authors_updated_at();

-- =====================================================
-- Migration Complete
-- =====================================================
-- Next step: Run data migration to populate authors table
-- from existing books.author column
