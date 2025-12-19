-- Complete Author Corrections Based on book-metadata.csv
-- This script fixes all the author association issues identified

-- =====================================================
-- Step 1: Create missing author (Dan Riehl)
-- =====================================================

-- Check if Dan Riehl exists
SELECT id, name FROM authors WHERE name = 'Dan Riehl';

-- Create Dan Riehl if he doesn't exist
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Dan Riehl', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Dan Riehl');

-- Get Dan Riehl's ID for later use
-- (After running above, check: SELECT id FROM authors WHERE name = 'Dan Riehl';)

-- =====================================================
-- Step 2: Fix Complete CL: Sixth Edition (Ted Holt)
-- =====================================================

-- Find the book
SELECT id, title FROM books WHERE title ILIKE '%Complete CL%Sixth%';

-- Remove wrong author (annegrubb)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Complete CL%Sixth%')
  AND author_id = 7724; -- annegrubb

-- Add correct author (Ted Holt)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, 8390, 0  -- Ted Holt
FROM books b
WHERE b.title ILIKE '%Complete CL%Sixth%'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = 8390
  );

-- =====================================================
-- Step 3: Fix Subfiles in Free-Format RPG (Kevin Vandever)
-- =====================================================

-- Find the book
SELECT id, title FROM books WHERE title ILIKE '%Subfiles%Free%';

-- Remove wrong author (admin)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Subfiles%Free%')
  AND author_id = 7756; -- admin

-- Add correct author (Kevin Vandever)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, 8529, 0  -- Kevin Vandever
FROM books b
WHERE b.title ILIKE '%Subfiles%Free%'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = 8529
  );

-- =====================================================
-- Step 4: Fix Control Language Programming for IBM i (Multiple Authors)
-- =====================================================

-- Find the book
SELECT id, title FROM books WHERE title ILIKE '%Control Language Programming%';

-- Remove any wrong authors first
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Control Language Programming%')
  AND author_id IN (7724, 7756); -- Remove annegrubb, admin if present

-- Add Jim Buck (primary author, order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, 7736, 0  -- Jim Buck
FROM books b
WHERE b.title ILIKE '%Control Language Programming%'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = 7736
  );

-- Add Bryan Meyers (co-author, order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, 8392, 1  -- Bryan Meyers
FROM books b
WHERE b.title ILIKE '%Control Language Programming%'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = 8392
  );

-- Add Dan Riehl (co-author, order 2) - NEED TO GET HIS ID FIRST
-- Replace XXXX with Dan Riehl's actual ID after creating him
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, (SELECT id FROM authors WHERE name = 'Dan Riehl'), 2  -- Dan Riehl
FROM books b
WHERE b.title ILIKE '%Control Language Programming%'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = (SELECT id FROM authors WHERE name = 'Dan Riehl')
  );

-- =====================================================
-- Step 5: Optional - Add Kevin Vandever's website
-- =====================================================

-- If Kevin wants to add his website URL:
-- UPDATE authors SET site_url = 'https://your-website.com' WHERE id = 8529;

-- =====================================================
-- Step 6: Verification Queries
-- =====================================================

-- Verify Complete CL: Sixth Edition
SELECT b.title, a.name, da.author_order
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE b.title ILIKE '%Complete CL%Sixth%'
ORDER BY da.author_order;

-- Verify Subfiles in Free-Format RPG
SELECT b.title, a.name, da.author_order
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE b.title ILIKE '%Subfiles%Free%'
ORDER BY da.author_order;

-- Verify Control Language Programming for IBM i
SELECT b.title, a.name, da.author_order
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE b.title ILIKE '%Control Language Programming%'
ORDER BY da.author_order;

-- =====================================================
-- Step 7: Clean up other books with wrong authors
-- =====================================================

-- Find all books currently associated with annegrubb or admin
SELECT b.title, a.name as current_author
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE a.id IN (7724, 7756)  -- annegrubb, admin
ORDER BY b.title;

-- These will need manual review and correction based on the CSV data