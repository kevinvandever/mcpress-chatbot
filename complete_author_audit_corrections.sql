
-- =====================================================
-- COMPLETE AUTHOR AUDIT AND CORRECTIONS
-- Generated from book-metadata.csv
-- =====================================================

-- This script fixes ALL author discrepancies, not just the 3 mentioned books


-- =====================================================
-- STEP 1: CREATE MISSING AUTHORS
-- =====================================================


-- Create Arvind Sathi
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Arvind Sathi', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Arvind Sathi');


-- Create Chuck Stupca
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Chuck Stupca', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Chuck Stupca');


-- Create Don Denoncourt
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Don Denoncourt', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Don Denoncourt');


-- Create Gary Craig
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Gary Craig', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Gary Craig');


-- Create Gili Mendel
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Gili Mendel', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Gili Mendel');


-- Create Jean-Francois Puget
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Jean-Francois Puget', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Jean-Francois Puget');


-- Create MC Press Bookstore
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'MC Press Bookstore', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'MC Press Bookstore');


-- Create Mithkal Smadi
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Mithkal Smadi', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Mithkal Smadi');


-- Create Peter Jakab
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Peter Jakab', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Peter Jakab');


-- Create Shannon O'Donnell
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT 'Shannon O''Donnell', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = 'Shannon O''Donnell');


-- =====================================================
-- STEP 2: FIX ALL BOOK-AUTHOR ASSOCIATIONS
-- =====================================================


-- Fix: 21st Century RPG: /Free, ILE, and MVC
-- CSV Authors: David Shirey

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%21st Century RPG: /Free, ILE, and MVC%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%21st Century RPG: /Free, ILE, and MVC%');


-- Add David Shirey (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%21st Century RPG: /Free, ILE, and MVC%'
  AND a.name = 'David Shirey'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: 5 Keys to Business Analytics Program Success
-- CSV Authors: John Boyer, Bill Frank, Brian Green, Tracy Harris, Kay Van De Vanter

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%5 Keys to Business Analytics Program Success%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%5 Keys to Business Analytics Program Success%');


-- Add John Boyer (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%5 Keys to Business Analytics Program Success%'
  AND a.name = 'John Boyer'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Bill Frank (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%5 Keys to Business Analytics Program Success%'
  AND a.name = 'Bill Frank'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Brian Green (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%5 Keys to Business Analytics Program Success%'
  AND a.name = 'Brian Green'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Tracy Harris (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%5 Keys to Business Analytics Program Success%'
  AND a.name = 'Tracy Harris'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Kay Van De Vanter (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%5 Keys to Business Analytics Program Success%'
  AND a.name = 'Kay Van De Vanter'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Active Server Pages Primer
-- CSV Authors: Mike Faust

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Active Server Pages Primer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Active Server Pages Primer%');


-- Add Mike Faust (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Active Server Pages Primer%'
  AND a.name = 'Mike Faust'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Administering Informix Dynamic Server
-- CSV Authors: Carlton Doe

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Administering Informix Dynamic Server%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Administering Informix Dynamic Server%');


-- Add Carlton Doe (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Administering Informix Dynamic Server%'
  AND a.name = 'Carlton Doe'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Advanced Guide to PHP on IBM i
-- CSV Authors: Kevin Schroeder

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Advanced Guide to PHP on IBM i%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Advanced Guide to PHP on IBM i%');


-- Add Kevin Schroeder (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Advanced Guide to PHP on IBM i%'
  AND a.name = 'Kevin Schroeder'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Advanced, Integrated RPG
-- CSV Authors: Thomas Snyder

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Advanced, Integrated RPG%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Advanced, Integrated RPG%');


-- Add Thomas Snyder (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Advanced, Integrated RPG%'
  AND a.name = 'Thomas Snyder'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Advanced Java EE Development for Rational Application Developer 7.5
-- CSV Authors: Kameron Cole, Robert McChesney, Richard Raszka

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Advanced Java EE Development for Rational Application Developer 7.5%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Advanced Java EE Development for Rational Application Developer 7.5%');


-- Add Kameron Cole (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Advanced Java EE Development for Rational Application Developer 7.5%'
  AND a.name = 'Kameron Cole'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Robert McChesney (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Advanced Java EE Development for Rational Application Developer 7.5%'
  AND a.name = 'Robert McChesney'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Richard Raszka (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Advanced Java EE Development for Rational Application Developer 7.5%'
  AND a.name = 'Richard Raszka'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: An Introduction to IBM Rational Application Developer
-- CSV Authors: Jane Fung, Colin Yu, Christian Lau, Ellen McKay, Gary Flood, James Hunter, Tim deBoer, Valentina Birsan, Yen Lu, Peter Walker, Joe Winchester, Gili Mendel

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%An Introduction to IBM Rational Application Developer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%An Introduction to IBM Rational Application Developer%');


-- Add Jane Fung (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Jane Fung'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Colin Yu (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Colin Yu'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Christian Lau (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Christian Lau'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Ellen McKay (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Ellen McKay'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Gary Flood (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Gary Flood'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add James Hunter (order 5)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 5
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'James Hunter'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Tim deBoer (order 6)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 6
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Tim deBoer'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Valentina Birsan (order 7)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 7
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Valentina Birsan'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Yen Lu (order 8)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 8
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Yen Lu'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Peter Walker (order 9)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 9
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Peter Walker'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Joe Winchester (order 10)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 10
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Joe Winchester'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Gili Mendel (order 11)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 11
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to IBM Rational Application Developer%'
  AND a.name = 'Gili Mendel'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: An Introduction to Web Application Development with IBM WebSphere Studio (Exam 285)
-- CSV Authors: Gary Craig, Peter Jakab

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%An Introduction to Web Application Development with IBM WebSphere Studio (Exam 285)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%An Introduction to Web Application Development with IBM WebSphere Studio (Exam 285)%');


-- Add Gary Craig (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to Web Application Development with IBM WebSphere Studio (Exam 285)%'
  AND a.name = 'Gary Craig'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Peter Jakab (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%An Introduction to Web Application Development with IBM WebSphere Studio (Exam 285)%'
  AND a.name = 'Peter Jakab'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Artificial Intelligence: Evolution and Revolution
-- CSV Authors: Steven Astorino, Mark Simmonds, Jean-Francois Puget, Roger Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Artificial Intelligence: Evolution and Revolution%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Artificial Intelligence: Evolution and Revolution%');


-- Add Steven Astorino (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Artificial Intelligence: Evolution and Revolution%'
  AND a.name = 'Steven Astorino'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Mark Simmonds (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Artificial Intelligence: Evolution and Revolution%'
  AND a.name = 'Mark Simmonds'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jean-Francois Puget (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Artificial Intelligence: Evolution and Revolution%'
  AND a.name = 'Jean-Francois Puget'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Roger Sanders (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%Artificial Intelligence: Evolution and Revolution%'
  AND a.name = 'Roger Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: AS/400 TCP/IP Handbook
-- CSV Authors: Chris Peters

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%AS/400 TCP/IP Handbook%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%AS/400 TCP/IP Handbook%');


-- Add Chris Peters (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%AS/400 TCP/IP Handbook%'
  AND a.name = 'Chris Peters'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Big Data Analytics
-- CSV Authors: Arvind Sathi

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Big Data Analytics%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Big Data Analytics%');


-- Add Arvind Sathi (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Big Data Analytics%'
  AND a.name = 'Arvind Sathi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Big Data Governance
-- CSV Authors: Sunil Soares

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Big Data Governance%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Big Data Governance%');


-- Add Sunil Soares (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Big Data Governance%'
  AND a.name = 'Sunil Soares'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Building Applications with IBM Rational Application Developer and JavaBeans
-- CSV Authors: Colette Burrus, Stephanie Parkin

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Building Applications with IBM Rational Application Developer and JavaBeans%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Building Applications with IBM Rational Application Developer and JavaBeans%');


-- Add Colette Burrus (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Building Applications with IBM Rational Application Developer and JavaBeans%'
  AND a.name = 'Colette Burrus'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Stephanie Parkin (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Building Applications with IBM Rational Application Developer and JavaBeans%'
  AND a.name = 'Stephanie Parkin'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Business Intelligence Strategy
-- CSV Authors: John Boyer, Bill Frank, Brian Green, Tracy Harris, Kay Van De Vanter

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Business Intelligence Strategy%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Business Intelligence Strategy%');


-- Add John Boyer (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Business Intelligence Strategy%'
  AND a.name = 'John Boyer'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Bill Frank (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Business Intelligence Strategy%'
  AND a.name = 'Bill Frank'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Brian Green (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Business Intelligence Strategy%'
  AND a.name = 'Brian Green'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Tracy Harris (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%Business Intelligence Strategy%'
  AND a.name = 'Tracy Harris'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Kay Van De Vanter (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%Business Intelligence Strategy%'
  AND a.name = 'Kay Van De Vanter'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: BYTE-ing Satire
-- CSV Authors: Joel Klebanoff

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%BYTE-ing Satire%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%BYTE-ing Satire%');


-- Add Joel Klebanoff (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%BYTE-ing Satire%'
  AND a.name = 'Joel Klebanoff'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Complete CL
-- CSV Authors: Ted Holt

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Complete CL%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Complete CL%');


-- Add Ted Holt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Complete CL%'
  AND a.name = 'Ted Holt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Complete CL: Sixth Edition
-- CSV Authors: Ted Holt

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Complete CL: Sixth Edition%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Complete CL: Sixth Edition%');


-- Add Ted Holt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Complete CL: Sixth Edition%'
  AND a.name = 'Ted Holt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Control Language Programming for IBM i
-- CSV Authors: Jim Buck, Bryan Meyers, Dan Riehl

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Control Language Programming for IBM i%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Control Language Programming for IBM i%');


-- Add Jim Buck (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Control Language Programming for IBM i%'
  AND a.name = 'Jim Buck'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Bryan Meyers (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Control Language Programming for IBM i%'
  AND a.name = 'Bryan Meyers'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Dan Riehl (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Control Language Programming for IBM i%'
  AND a.name = 'Dan Riehl'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Customer Experience Analytics
-- CSV Authors: Arvind Sathi

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Customer Experience Analytics%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Customer Experience Analytics%');


-- Add Arvind Sathi (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Customer Experience Analytics%'
  AND a.name = 'Arvind Sathi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Database Design and SQL for DB2
-- CSV Authors: James Cooper

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Database Design and SQL for DB2%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Database Design and SQL for DB2%');


-- Add James Cooper (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Database Design and SQL for DB2%'
  AND a.name = 'James Cooper'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Data Fabric: An Intelligent Data Architecture for AI
-- CSV Authors: Steven Astorino, Mark Simmonds, Roger Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Data Fabric: An Intelligent Data Architecture for AI%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Data Fabric: An Intelligent Data Architecture for AI%');


-- Add Steven Astorino (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Data Fabric: An Intelligent Data Architecture for AI%'
  AND a.name = 'Steven Astorino'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Mark Simmonds (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Data Fabric: An Intelligent Data Architecture for AI%'
  AND a.name = 'Mark Simmonds'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Roger Sanders (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Data Fabric: An Intelligent Data Architecture for AI%'
  AND a.name = 'Roger Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Data Governance Tools
-- CSV Authors: Sunil Soares

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Data Governance Tools%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Data Governance Tools%');


-- Add Sunil Soares (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Data Governance Tools%'
  AND a.name = 'Sunil Soares'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10.1/10.5 for Linux, UNIX, and Windows Database Administration (Exams 611 and 311)
-- CSV Authors: Mohankumar Saraswatipura, Robert (Kent) Collins

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10.1/10.5 for Linux, UNIX, and Windows Database Administration (Exams 611 and 311)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10.1/10.5 for Linux, UNIX, and Windows Database Administration (Exams 611 and 311)%');


-- Add Mohankumar Saraswatipura (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10.1/10.5 for Linux, UNIX, and Windows Database Administration (Exams 611 and 311)%'
  AND a.name = 'Mohankumar Saraswatipura'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Robert (Kent) Collins (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10.1/10.5 for Linux, UNIX, and Windows Database Administration (Exams 611 and 311)%'
  AND a.name = 'Robert (Kent) Collins'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10.1 Fundamentals (Exam 610)
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10.1 Fundamentals (Exam 610)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10.1 Fundamentals (Exam 610)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10.1 Fundamentals (Exam 610)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10.5 DBA for LUW Upgrade from DB2 10.1: Certification Study Notes
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10.5 DBA for LUW Upgrade from DB2 10.1: Certification Study Notes%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10.5 DBA for LUW Upgrade from DB2 10.1: Certification Study Notes%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10.5 DBA for LUW Upgrade from DB2 10.1: Certification Study Notes%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10.5 Fundamentals for LUW (Exam 615)
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10.5 Fundamentals for LUW (Exam 615)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10.5 Fundamentals for LUW (Exam 615)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10.5 Fundamentals for LUW (Exam 615)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10 for z/OS: Cost Savings...Right Out of the Box
-- CSV Authors: Dave Beulke, Roger Miller, Surekha Parekh, Julian Stuhler

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10 for z/OS: Cost Savings...Right Out of the Box%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10 for z/OS: Cost Savings...Right Out of the Box%');


-- Add Dave Beulke (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: Cost Savings...Right Out of the Box%'
  AND a.name = 'Dave Beulke'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Roger Miller (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: Cost Savings...Right Out of the Box%'
  AND a.name = 'Roger Miller'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Surekha Parekh (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: Cost Savings...Right Out of the Box%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Julian Stuhler (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: Cost Savings...Right Out of the Box%'
  AND a.name = 'Julian Stuhler'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10 for z/OS Database Administration (Exam 612)
-- CSV Authors: Susan Lawson, Daniel Luksetich

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10 for z/OS Database Administration (Exam 612)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10 for z/OS Database Administration (Exam 612)%');


-- Add Susan Lawson (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS Database Administration (Exam 612)%'
  AND a.name = 'Susan Lawson'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Daniel Luksetich (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS Database Administration (Exam 612)%'
  AND a.name = 'Daniel Luksetich'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 10 for z/OS: The Smarter, Faster Way to Upgrade
-- CSV Authors: John Campbell, Cristian Molaro, Surekha Parekh

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 10 for z/OS: The Smarter, Faster Way to Upgrade%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 10 for z/OS: The Smarter, Faster Way to Upgrade%');


-- Add John Campbell (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: The Smarter, Faster Way to Upgrade%'
  AND a.name = 'John Campbell'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Cristian Molaro (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: The Smarter, Faster Way to Upgrade%'
  AND a.name = 'Cristian Molaro'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Surekha Parekh (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%DB2 10 for z/OS: The Smarter, Faster Way to Upgrade%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 11 for z/OS Database Administration: Certification Study Guide (Exam 312)
-- CSV Authors: Susan Lawson

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 11 for z/OS Database Administration: Certification Study Guide (Exam 312)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 11 for z/OS Database Administration: Certification Study Guide (Exam 312)%');


-- Add Susan Lawson (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11 for z/OS Database Administration: Certification Study Guide (Exam 312)%'
  AND a.name = 'Susan Lawson'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 11 System Administrator for z/OS: Certification Study Guide (Exam 317)
-- CSV Authors: Judy H. Nall

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 11 System Administrator for z/OS: Certification Study Guide (Exam 317)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 11 System Administrator for z/OS: Certification Study Guide (Exam 317)%');


-- Add Judy H. Nall (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11 System Administrator for z/OS: Certification Study Guide (Exam 317)%'
  AND a.name = 'Judy H. Nall'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 11: The Database for Big Data and Analytics
-- CSV Authors: Cristian Molaro, Surekha Parekh, Terry Purcell, Julian Stuhler

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 11: The Database for Big Data and Analytics%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 11: The Database for Big Data and Analytics%');


-- Add Cristian Molaro (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Database for Big Data and Analytics%'
  AND a.name = 'Cristian Molaro'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Surekha Parekh (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Database for Big Data and Analytics%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Terry Purcell (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Database for Big Data and Analytics%'
  AND a.name = 'Terry Purcell'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Julian Stuhler (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Database for Big Data and Analytics%'
  AND a.name = 'Julian Stuhler'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile
-- CSV Authors: John Campbell, Chris Crone, Gareth Jones, Surekha Parekh, Jay Yothers

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%');


-- Add John Campbell (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%'
  AND a.name = 'John Campbell'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Chris Crone (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%'
  AND a.name = 'Chris Crone'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Gareth Jones (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%'
  AND a.name = 'Gareth Jones'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Surekha Parekh (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jay Yothers (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%DB2 11: The Ultimate Database for Cloud, Analytics, and Mobile%'
  AND a.name = 'Jay Yothers'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 12 for z/OS - The #1 Enterprise Database
-- CSV Authors: Surekha Parekh

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 12 for z/OS - The #1 Enterprise Database%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 12 for z/OS - The #1 Enterprise Database%');


-- Add Surekha Parekh (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 12 for z/OS - The #1 Enterprise Database%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9.7 for Linux, UNIX, and Windows Database Administration (Exam 541)
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9.7 for Linux, UNIX, and Windows Database Administration (Exam 541)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9.7 for Linux, UNIX, and Windows Database Administration (Exam 541)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9.7 for Linux, UNIX, and Windows Database Administration (Exam 541)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 for Developers
-- CSV Authors: Philip K. Gunning

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 for Developers%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 for Developers%');


-- Add Philip K. Gunning (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for Developers%'
  AND a.name = 'Philip K. Gunning'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 for Linux, UNIX, and Windows Advanced Database Administration (Exam 734)
-- CSV Authors: Roger E. Sanders, Dwaine R. Snow

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 for Linux, UNIX, and Windows Advanced Database Administration (Exam 734)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 for Linux, UNIX, and Windows Advanced Database Administration (Exam 734)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for Linux, UNIX, and Windows Advanced Database Administration (Exam 734)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Dwaine R. Snow (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for Linux, UNIX, and Windows Advanced Database Administration (Exam 734)%'
  AND a.name = 'Dwaine R. Snow'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 for Linux, UNIX, and Windows Database Administration (Exam 731)
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 for Linux, UNIX, and Windows Database Administration (Exam 731)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 for Linux, UNIX, and Windows Database Administration (Exam 731)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for Linux, UNIX, and Windows Database Administration (Exam 731)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 for Linux, UNIX, and Windows Database Administration Upgrade (Exam 736)
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 for Linux, UNIX, and Windows Database Administration Upgrade (Exam 736)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 for Linux, UNIX, and Windows Database Administration Upgrade (Exam 736)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for Linux, UNIX, and Windows Database Administration Upgrade (Exam 736)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 for z/OS Database Administration (Exam 732)
-- CSV Authors: Susan Lawson, Daniel Luksetich

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 for z/OS Database Administration (Exam 732)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 for z/OS Database Administration (Exam 732)%');


-- Add Susan Lawson (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for z/OS Database Administration (Exam 732)%'
  AND a.name = 'Susan Lawson'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Daniel Luksetich (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 for z/OS Database Administration (Exam 732)%'
  AND a.name = 'Daniel Luksetich'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 Fundamentals (Exam 730)
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 Fundamentals (Exam 730)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 Fundamentals (Exam 730)%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 Fundamentals (Exam 730)%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: DB2 9 System Administration for z/OS (Exam 737)
-- CSV Authors: Judy H. Nall

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%DB2 9 System Administration for z/OS (Exam 737)%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%DB2 9 System Administration for z/OS (Exam 737)%');


-- Add Judy H. Nall (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%DB2 9 System Administration for z/OS (Exam 737)%'
  AND a.name = 'Judy H. Nall'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Developing Business Applications for the Web: With HTML, CSS, JSP, PHP, ASP.NET, and JavaScript
-- CSV Authors: Laura Ubelhor, Christian Hur

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Developing Business Applications for the Web: With HTML, CSS, JSP, PHP, ASP.NET, and JavaScript%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Developing Business Applications for the Web: With HTML, CSS, JSP, PHP, ASP.NET, and JavaScript%');


-- Add Laura Ubelhor (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Developing Business Applications for the Web: With HTML, CSS, JSP, PHP, ASP.NET, and JavaScript%'
  AND a.name = 'Laura Ubelhor'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Christian Hur (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Developing Business Applications for the Web: With HTML, CSS, JSP, PHP, ASP.NET, and JavaScript%'
  AND a.name = 'Christian Hur'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Developing Web 2.0 Applications with EGL for IBM i
-- CSV Authors: Joe Pluta

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Developing Web 2.0 Applications with EGL for IBM i%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Developing Web 2.0 Applications with EGL for IBM i%');


-- Add Joe Pluta (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Developing Web 2.0 Applications with EGL for IBM i%'
  AND a.name = 'Joe Pluta'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Developing Web Services for Web Applications
-- CSV Authors: Colette Burrus, Stephanie Parkin

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Developing Web Services for Web Applications%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Developing Web Services for Web Applications%');


-- Add Colette Burrus (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Developing Web Services for Web Applications%'
  AND a.name = 'Colette Burrus'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Stephanie Parkin (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Developing Web Services for Web Applications%'
  AND a.name = 'Stephanie Parkin'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Digital Marketplaces for Knowledge Intensive Assets
-- CSV Authors: Ranjan Sinha, Cheranellore Vasudevan

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Digital Marketplaces for Knowledge Intensive Assets%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Digital Marketplaces for Knowledge Intensive Assets%');


-- Add Ranjan Sinha (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Digital Marketplaces for Knowledge Intensive Assets%'
  AND a.name = 'Ranjan Sinha'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Cheranellore Vasudevan (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Digital Marketplaces for Knowledge Intensive Assets%'
  AND a.name = 'Cheranellore Vasudevan'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Driving the Power of AIX
-- CSV Authors: Ken Milberg

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Driving the Power of AIX%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Driving the Power of AIX%');


-- Add Ken Milberg (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Driving the Power of AIX%'
  AND a.name = 'Ken Milberg'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Eclipse: Step by Step
-- CSV Authors: Joe Pluta

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Eclipse: Step by Step%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Eclipse: Step by Step%');


-- Add Joe Pluta (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Eclipse: Step by Step%'
  AND a.name = 'Joe Pluta'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Enterprise Web 2.0 with EGL
-- CSV Authors: Ben Margolis

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Enterprise Web 2.0 with EGL%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Enterprise Web 2.0 with EGL%');


-- Add Ben Margolis (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Enterprise Web 2.0 with EGL%'
  AND a.name = 'Ben Margolis'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Evolve Your RPG Coding: Move from OPM to ILE ... and Beyond
-- CSV Authors: Rafael Victoria-Pereira

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Evolve Your RPG Coding: Move from OPM to ILE ... and Beyond%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Evolve Your RPG Coding: Move from OPM to ILE ... and Beyond%');


-- Add Rafael Victoria-Pereira (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Evolve Your RPG Coding: Move from OPM to ILE ... and Beyond%'
  AND a.name = 'Rafael Victoria-Pereira'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Extract, Transform, and Load with SQL Server Integration Services
-- CSV Authors: Thomas Snyder, Vedish Shah

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Extract, Transform, and Load with SQL Server Integration Services%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Extract, Transform, and Load with SQL Server Integration Services%');


-- Add Thomas Snyder (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Extract, Transform, and Load with SQL Server Integration Services%'
  AND a.name = 'Thomas Snyder'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Vedish Shah (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Extract, Transform, and Load with SQL Server Integration Services%'
  AND a.name = 'Vedish Shah'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Flexible Input, Dazzling Output with IBM i
-- CSV Authors: Rafael Victoria-Pereira

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Flexible Input, Dazzling Output with IBM i%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Flexible Input, Dazzling Output with IBM i%');


-- Add Rafael Victoria-Pereira (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Flexible Input, Dazzling Output with IBM i%'
  AND a.name = 'Rafael Victoria-Pereira'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Free-Format RPG IV: Third Edition
-- CSV Authors: Jim Martin

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Free-Format RPG IV: Third Edition%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Free-Format RPG IV: Third Edition%');


-- Add Jim Martin (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Free-Format RPG IV: Third Edition%'
  AND a.name = 'Jim Martin'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Free-Format RPG IV: Second Edition
-- CSV Authors: Jim Martin

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Free-Format RPG IV: Second Edition%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Free-Format RPG IV: Second Edition%');


-- Add Jim Martin (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Free-Format RPG IV: Second Edition%'
  AND a.name = 'Jim Martin'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: From Idea to Print
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%From Idea to Print%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%From Idea to Print%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%From Idea to Print%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Functions in Free-Format RPG IV
-- CSV Authors: Jim Martin

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Functions in Free-Format RPG IV%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Functions in Free-Format RPG IV%');


-- Add Jim Martin (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Functions in Free-Format RPG IV%'
  AND a.name = 'Jim Martin'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Fundamentals of Technology Project Management
-- CSV Authors: Colleen Garton, Erika McCulloch

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Fundamentals of Technology Project Management%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Fundamentals of Technology Project Management%');


-- Add Colleen Garton (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Fundamentals of Technology Project Management%'
  AND a.name = 'Colleen Garton'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Erika McCulloch (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Fundamentals of Technology Project Management%'
  AND a.name = 'Erika McCulloch'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Gift Card
-- CSV Authors: MC Press Bookstore

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Gift Card%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Gift Card%');


-- Add MC Press Bookstore (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Gift Card%'
  AND a.name = 'MC Press Bookstore'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: How to Become a Highly Paid Corporate Programmer
-- CSV Authors: Paul H. Harkins

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%How to Become a Highly Paid Corporate Programmer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%How to Become a Highly Paid Corporate Programmer%');


-- Add Paul H. Harkins (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%How to Become a Highly Paid Corporate Programmer%'
  AND a.name = 'Paul H. Harkins'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: HTML for the Business Developer
-- CSV Authors: Kevin Forsythe, Laura Ubelhor

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%HTML for the Business Developer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%HTML for the Business Developer%');


-- Add Kevin Forsythe (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%HTML for the Business Developer%'
  AND a.name = 'Kevin Forsythe'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Laura Ubelhor (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%HTML for the Business Developer%'
  AND a.name = 'Laura Ubelhor'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: i5/OS and Microsoft Office Integration Handbook
-- CSV Authors: Chris Peters, Brian Singleton

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%i5/OS and Microsoft Office Integration Handbook%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%i5/OS and Microsoft Office Integration Handbook%');


-- Add Chris Peters (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%i5/OS and Microsoft Office Integration Handbook%'
  AND a.name = 'Chris Peters'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Brian Singleton (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%i5/OS and Microsoft Office Integration Handbook%'
  AND a.name = 'Brian Singleton'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM Business Analytics and Cloud Computing
-- CSV Authors: Anant Jhingran, Stephan Jou, William Lee, Thanh Pham, Biraj Saha

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM Business Analytics and Cloud Computing%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM Business Analytics and Cloud Computing%');


-- Add Anant Jhingran (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM Business Analytics and Cloud Computing%'
  AND a.name = 'Anant Jhingran'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Stephan Jou (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%IBM Business Analytics and Cloud Computing%'
  AND a.name = 'Stephan Jou'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add William Lee (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%IBM Business Analytics and Cloud Computing%'
  AND a.name = 'William Lee'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Thanh Pham (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%IBM Business Analytics and Cloud Computing%'
  AND a.name = 'Thanh Pham'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Biraj Saha (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%IBM Business Analytics and Cloud Computing%'
  AND a.name = 'Biraj Saha'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM Cloud Platform Primer
-- CSV Authors: Ashok K. Iyengar

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM Cloud Platform Primer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM Cloud Platform Primer%');


-- Add Ashok K. Iyengar (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM Cloud Platform Primer%'
  AND a.name = 'Ashok K. Iyengar'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!
-- CSV Authors: Shantan Kethireddy, Jane Man, Surekha Parekh, Pallavi Priyadarshini, Maryela Weihrauch

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%');


-- Add Shantan Kethireddy (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%'
  AND a.name = 'Shantan Kethireddy'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jane Man (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%'
  AND a.name = 'Jane Man'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Surekha Parekh (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Pallavi Priyadarshini (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%'
  AND a.name = 'Pallavi Priyadarshini'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Maryela Weihrauch (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%IBM DB2 for z/OS: The Database for Gaining a Competitive Advantage!%'
  AND a.name = 'Maryela Weihrauch'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM i5/iSeries Primer
-- CSV Authors: Ted Holt, Kevin Forsythe, Doug Pence, Ron Hawkins

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM i5/iSeries Primer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM i5/iSeries Primer%');


-- Add Ted Holt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM i5/iSeries Primer%'
  AND a.name = 'Ted Holt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Kevin Forsythe (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%IBM i5/iSeries Primer%'
  AND a.name = 'Kevin Forsythe'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Doug Pence (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%IBM i5/iSeries Primer%'
  AND a.name = 'Doug Pence'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Ron Hawkins (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%IBM i5/iSeries Primer%'
  AND a.name = 'Ron Hawkins'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM InfoSphere: A Platform for Big Data Governance and Process Data Governance
-- CSV Authors: Sunil Soares

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM InfoSphere: A Platform for Big Data Governance and Process Data Governance%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM InfoSphere: A Platform for Big Data Governance and Process Data Governance%');


-- Add Sunil Soares (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM InfoSphere: A Platform for Big Data Governance and Process Data Governance%'
  AND a.name = 'Sunil Soares'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM i Security Administration and Compliance
-- CSV Authors: Carol Woodbury

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM i Security Administration and Compliance%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM i Security Administration and Compliance%');


-- Add Carol Woodbury (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM i Security Administration and Compliance%'
  AND a.name = 'Carol Woodbury'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM i Security Administration and Compliance: Second Edition
-- CSV Authors: Carol Woodbury

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM i Security Administration and Compliance: Second Edition%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM i Security Administration and Compliance: Second Edition%');


-- Add Carol Woodbury (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM i Security Administration and Compliance: Second Edition%'
  AND a.name = 'Carol Woodbury'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM i Security Administration and Compliance: Third Edition
-- CSV Authors: Carol Woodbury

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM i Security Administration and Compliance: Third Edition%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM i Security Administration and Compliance: Third Edition%');


-- Add Carol Woodbury (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM i Security Administration and Compliance: Third Edition%'
  AND a.name = 'Carol Woodbury'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM Mainframe Security
-- CSV Authors: Dinesh D. Dattani

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM Mainframe Security%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM Mainframe Security%');


-- Add Dinesh D. Dattani (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM Mainframe Security%'
  AND a.name = 'Dinesh D. Dattani'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM Rational Business Developer with EGL
-- CSV Authors: Ben Margolis

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM Rational Business Developer with EGL%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM Rational Business Developer with EGL%');


-- Add Ben Margolis (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM Rational Business Developer with EGL%'
  AND a.name = 'Ben Margolis'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM System i APIs at Work
-- CSV Authors: Bruce Vining, Doug Pence, Ron Hawkins

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM System i APIs at Work%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM System i APIs at Work%');


-- Add Bruce Vining (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM System i APIs at Work%'
  AND a.name = 'Bruce Vining'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Doug Pence (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%IBM System i APIs at Work%'
  AND a.name = 'Doug Pence'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Ron Hawkins (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%IBM System i APIs at Work%'
  AND a.name = 'Ron Hawkins'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IBM WebSphere Portal Primer
-- CSV Authors: Ashok K. Iyengar, Venkata Gadepalli, Bruce Olson

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IBM WebSphere Portal Primer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IBM WebSphere Portal Primer%');


-- Add Ashok K. Iyengar (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IBM WebSphere Portal Primer%'
  AND a.name = 'Ashok K. Iyengar'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Venkata Gadepalli (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%IBM WebSphere Portal Primer%'
  AND a.name = 'Venkata Gadepalli'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Bruce Olson (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%IBM WebSphere Portal Primer%'
  AND a.name = 'Bruce Olson'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Identity Management
-- CSV Authors: Graham Williamson, David Yip, Ilan Sharoni, Kent Spaulding

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Identity Management%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Identity Management%');


-- Add Graham Williamson (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Identity Management%'
  AND a.name = 'Graham Williamson'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add David Yip (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Identity Management%'
  AND a.name = 'David Yip'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Ilan Sharoni (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Identity Management%'
  AND a.name = 'Ilan Sharoni'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Kent Spaulding (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%Identity Management%'
  AND a.name = 'Kent Spaulding'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Identity Management: A Business Perspective
-- CSV Authors: Graham Williamson

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Identity Management: A Business Perspective%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Identity Management: A Business Perspective%');


-- Add Graham Williamson (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Identity Management: A Business Perspective%'
  AND a.name = 'Graham Williamson'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: iSeries and AS/400 Work Management
-- CSV Authors: Chuck Stupca

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%iSeries and AS/400 Work Management%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%iSeries and AS/400 Work Management%');


-- Add Chuck Stupca (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%iSeries and AS/400 Work Management%'
  AND a.name = 'Chuck Stupca'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: IT Virtualization Best Practices
-- CSV Authors: Mickey Iqbal, Mithkal Smadi, Chris Molloy, Jim Rymarczyk

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%IT Virtualization Best Practices%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%IT Virtualization Best Practices%');


-- Add Mickey Iqbal (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%IT Virtualization Best Practices%'
  AND a.name = 'Mickey Iqbal'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Mithkal Smadi (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%IT Virtualization Best Practices%'
  AND a.name = 'Mithkal Smadi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Chris Molloy (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%IT Virtualization Best Practices%'
  AND a.name = 'Chris Molloy'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jim Rymarczyk (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%IT Virtualization Best Practices%'
  AND a.name = 'Jim Rymarczyk'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Java Application Strategies for iSeries and AS/400
-- CSV Authors: Don Denoncourt

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Java Application Strategies for iSeries and AS/400%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Java Application Strategies for iSeries and AS/400%');


-- Add Don Denoncourt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Java Application Strategies for iSeries and AS/400%'
  AND a.name = 'Don Denoncourt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Java for RPG Programmers
-- CSV Authors: Phil Coulthard, George Farr

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Java for RPG Programmers%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Java for RPG Programmers%');


-- Add Phil Coulthard (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Java for RPG Programmers%'
  AND a.name = 'Phil Coulthard'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add George Farr (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Java for RPG Programmers%'
  AND a.name = 'George Farr'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: JavaScript for the Business Developer
-- CSV Authors: Mike Faust

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%JavaScript for the Business Developer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%JavaScript for the Business Developer%');


-- Add Mike Faust (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%JavaScript for the Business Developer%'
  AND a.name = 'Mike Faust'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Leadership in My Rearview Mirror
-- CSV Authors: Jack Beach

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Leadership in My Rearview Mirror%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Leadership in My Rearview Mirror%');


-- Add Jack Beach (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Leadership in My Rearview Mirror%'
  AND a.name = 'Jack Beach'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Managing Without Walls
-- CSV Authors: Colleen Garton, Kevin Wegryn

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Managing Without Walls%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Managing Without Walls%');


-- Add Colleen Garton (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Managing Without Walls%'
  AND a.name = 'Colleen Garton'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Kevin Wegryn (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Managing Without Walls%'
  AND a.name = 'Kevin Wegryn'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Mastering IBM i
-- CSV Authors: Jim Buck, Jerry Fottral

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Mastering IBM i%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Mastering IBM i%');


-- Add Jim Buck (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Mastering IBM i%'
  AND a.name = 'Jim Buck'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jerry Fottral (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Mastering IBM i%'
  AND a.name = 'Jerry Fottral'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Mastering IBM i Security
-- CSV Authors: Carol Woodbury

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Mastering IBM i Security%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Mastering IBM i Security%');


-- Add Carol Woodbury (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Mastering IBM i Security%'
  AND a.name = 'Carol Woodbury'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Mastering the AS/400
-- CSV Authors: Jerry Fottral

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Mastering the AS/400%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Mastering the AS/400%');


-- Add Jerry Fottral (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Mastering the AS/400%'
  AND a.name = 'Jerry Fottral'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: MDM for Customer Data
-- CSV Authors: Kelvin K. A. Looi

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%MDM for Customer Data%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%MDM for Customer Data%');


-- Add Kelvin K. A. Looi (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%MDM for Customer Data%'
  AND a.name = 'Kelvin K. A. Looi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Open Query File Magic
-- CSV Authors: Ted Holt

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Open Query File Magic%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Open Query File Magic%');


-- Add Ted Holt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Open Query File Magic%'
  AND a.name = 'Ted Holt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Open Source Starter Guide for IBM i Developers
-- CSV Authors: Pete Helgren

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Open Source Starter Guide for IBM i Developers%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Open Source Starter Guide for IBM i Developers%');


-- Add Pete Helgren (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Open Source Starter Guide for IBM i Developers%'
  AND a.name = 'Pete Helgren'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Programming in ILE RPG, Fifth Edition
-- CSV Authors: Bryan Meyers, Jim Buck

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Programming in ILE RPG, Fifth Edition%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Programming in ILE RPG, Fifth Edition%');


-- Add Bryan Meyers (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Programming in ILE RPG, Fifth Edition%'
  AND a.name = 'Bryan Meyers'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jim Buck (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Programming in ILE RPG, Fifth Edition%'
  AND a.name = 'Jim Buck'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Programming in RPG IV
-- CSV Authors: Bryan Meyers, Jim Buck

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Programming in RPG IV%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Programming in RPG IV%');


-- Add Bryan Meyers (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Programming in RPG IV%'
  AND a.name = 'Bryan Meyers'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Jim Buck (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Programming in RPG IV%'
  AND a.name = 'Jim Buck'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Programming Portlets
-- CSV Authors: Ron Lynn, Joey Bernal, Peter Blinstrubas, Usman Memon, Cayce Marston, Tim Hanis, Varadarajan (Varad) Ramamoorthy, Stefan Hepper

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Programming Portlets%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Programming Portlets%');


-- Add Ron Lynn (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Ron Lynn'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Joey Bernal (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Joey Bernal'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Peter Blinstrubas (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Peter Blinstrubas'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Usman Memon (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Usman Memon'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Cayce Marston (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Cayce Marston'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Tim Hanis (order 5)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 5
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Tim Hanis'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Varadarajan (Varad) Ramamoorthy (order 6)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 6
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Varadarajan (Varad) Ramamoorthy'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Stefan Hepper (order 7)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 7
FROM books b, authors a
WHERE b.title ILIKE '%Programming Portlets%'
  AND a.name = 'Stefan Hepper'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Qshell for iSeries
-- CSV Authors: Ted Holt, Fred A. Kulack

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Qshell for iSeries%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Qshell for iSeries%');


-- Add Ted Holt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Qshell for iSeries%'
  AND a.name = 'Ted Holt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Fred A. Kulack (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%Qshell for iSeries%'
  AND a.name = 'Fred A. Kulack'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: QuickStart Guide to Db2 Development with Python
-- CSV Authors: Roger E. Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%QuickStart Guide to Db2 Development with Python%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%QuickStart Guide to Db2 Development with Python%');


-- Add Roger E. Sanders (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%QuickStart Guide to Db2 Development with Python%'
  AND a.name = 'Roger E. Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: RPG TnT
-- CSV Authors: Bob Cozzi

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%RPG TnT%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%RPG TnT%');


-- Add Bob Cozzi (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%RPG TnT%'
  AND a.name = 'Bob Cozzi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Selling Information Governance to the Business
-- CSV Authors: Sunil Soares

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Selling Information Governance to the Business%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Selling Information Governance to the Business%');


-- Add Sunil Soares (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Selling Information Governance to the Business%'
  AND a.name = 'Sunil Soares'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: SOA for the Business Developer
-- CSV Authors: Ben Margolis

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%SOA for the Business Developer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%SOA for the Business Developer%');


-- Add Ben Margolis (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%SOA for the Business Developer%'
  AND a.name = 'Ben Margolis'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: SQL Built-In Functions and Stored Procedures
-- CSV Authors: Mike Faust

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%SQL Built-In Functions and Stored Procedures%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%SQL Built-In Functions and Stored Procedures%');


-- Add Mike Faust (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%SQL Built-In Functions and Stored Procedures%'
  AND a.name = 'Mike Faust'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: SQL for eServer i5 and iSeries
-- CSV Authors: Kevin Forsythe

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%SQL for eServer i5 and iSeries%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%SQL for eServer i5 and iSeries%');


-- Add Kevin Forsythe (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%SQL for eServer i5 and iSeries%'
  AND a.name = 'Kevin Forsythe'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: SQL for IBM i: A Database Modernization Guide
-- CSV Authors: Rafael Victoria-Pereira

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%SQL for IBM i: A Database Modernization Guide%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%SQL for IBM i: A Database Modernization Guide%');


-- Add Rafael Victoria-Pereira (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%SQL for IBM i: A Database Modernization Guide%'
  AND a.name = 'Rafael Victoria-Pereira'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Subfiles in Free-Format RPG
-- CSV Authors: Kevin Vandever

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Subfiles in Free-Format RPG%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Subfiles in Free-Format RPG%');


-- Add Kevin Vandever (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Subfiles in Free-Format RPG%'
  AND a.name = 'Kevin Vandever'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: System i Disaster Recovery Planning
-- CSV Authors: Richard Dolewski

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%System i Disaster Recovery Planning%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%System i Disaster Recovery Planning%');


-- Add Richard Dolewski (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%System i Disaster Recovery Planning%'
  AND a.name = 'Richard Dolewski'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: Template
-- CSV Authors: MC Press Bookstore

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%Template%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Template%');


-- Add MC Press Bookstore (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%Template%'
  AND a.name = 'MC Press Bookstore'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The Business Value of DB2 for z/OS
-- CSV Authors: John Campbell, Namik Hrle, Ruiping Li, Surekha Parekh, Terry Purcell

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The Business Value of DB2 for z/OS%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The Business Value of DB2 for z/OS%');


-- Add John Campbell (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The Business Value of DB2 for z/OS%'
  AND a.name = 'John Campbell'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Namik Hrle (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%The Business Value of DB2 for z/OS%'
  AND a.name = 'Namik Hrle'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Ruiping Li (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%The Business Value of DB2 for z/OS%'
  AND a.name = 'Ruiping Li'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Surekha Parekh (order 3)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 3
FROM books b, authors a
WHERE b.title ILIKE '%The Business Value of DB2 for z/OS%'
  AND a.name = 'Surekha Parekh'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Terry Purcell (order 4)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 4
FROM books b, authors a
WHERE b.title ILIKE '%The Business Value of DB2 for z/OS%'
  AND a.name = 'Terry Purcell'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The Chief Data Officer Handbook for Data Governance
-- CSV Authors: Sunil Soares

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The Chief Data Officer Handbook for Data Governance%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The Chief Data Officer Handbook for Data Governance%');


-- Add Sunil Soares (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The Chief Data Officer Handbook for Data Governance%'
  AND a.name = 'Sunil Soares'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The IBM Data Governance Unified Process
-- CSV Authors: Sunil Soares

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The IBM Data Governance Unified Process%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The IBM Data Governance Unified Process%');


-- Add Sunil Soares (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The IBM Data Governance Unified Process%'
  AND a.name = 'Sunil Soares'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The IBM i Programmer's Guide to PHP
-- CSV Authors: Jeff Olen, Kevin Schroeder

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The IBM i Programmer''s Guide to PHP%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The IBM i Programmer''s Guide to PHP%');


-- Add Jeff Olen (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The IBM i Programmer''s Guide to PHP%'
  AND a.name = 'Jeff Olen'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Kevin Schroeder (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%The IBM i Programmer''s Guide to PHP%'
  AND a.name = 'Kevin Schroeder'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The Lakehouse Effect - A New Era for Data Insights and AI
-- CSV Authors: Steven Astorino, Mark Simmonds, Roger Sanders

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The Lakehouse Effect - A New Era for Data Insights and AI%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The Lakehouse Effect - A New Era for Data Insights and AI%');


-- Add Steven Astorino (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The Lakehouse Effect - A New Era for Data Insights and AI%'
  AND a.name = 'Steven Astorino'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Mark Simmonds (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%The Lakehouse Effect - A New Era for Data Insights and AI%'
  AND a.name = 'Mark Simmonds'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Roger Sanders (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%The Lakehouse Effect - A New Era for Data Insights and AI%'
  AND a.name = 'Roger Sanders'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The MC Press Desktop Encyclopedia of Tips, Techniques, and Programming Practices for iSeries and AS/400
-- CSV Authors: Ted Holt, Shannon O'Donnell

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The MC Press Desktop Encyclopedia of Tips, Techniques, and Programming Practices for iSeries and AS/400%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The MC Press Desktop Encyclopedia of Tips, Techniques, and Programming Practices for iSeries and AS/400%');


-- Add Ted Holt (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The MC Press Desktop Encyclopedia of Tips, Techniques, and Programming Practices for iSeries and AS/400%'
  AND a.name = 'Ted Holt'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Shannon O'Donnell (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%The MC Press Desktop Encyclopedia of Tips, Techniques, and Programming Practices for iSeries and AS/400%'
  AND a.name = 'Shannon O''Donnell'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The Modern RPG IV Language
-- CSV Authors: Bob Cozzi

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The Modern RPG IV Language%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The Modern RPG IV Language%');


-- Add Bob Cozzi (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The Modern RPG IV Language%'
  AND a.name = 'Bob Cozzi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The Programmer's Guide to iSeries Navigator
-- CSV Authors: Paul Tuohy

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The Programmer''s Guide to iSeries Navigator%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The Programmer''s Guide to iSeries Navigator%');


-- Add Paul Tuohy (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The Programmer''s Guide to iSeries Navigator%'
  AND a.name = 'Paul Tuohy'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: The Remote System Explorer
-- CSV Authors: Don Yantzi, Nazmin Haji

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%The Remote System Explorer%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%The Remote System Explorer%');


-- Add Don Yantzi (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%The Remote System Explorer%'
  AND a.name = 'Don Yantzi'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Nazmin Haji (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%The Remote System Explorer%'
  AND a.name = 'Nazmin Haji'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: WDSC: Step by Step
-- CSV Authors: Joe Pluta

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%WDSC: Step by Step%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%WDSC: Step by Step%');


-- Add Joe Pluta (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%WDSC: Step by Step%'
  AND a.name = 'Joe Pluta'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: WebSphere Application Server: Step by Step
-- CSV Authors: Rama Turaga, Owen Cline, Peter Van Sickel

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%WebSphere Application Server: Step by Step%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%WebSphere Application Server: Step by Step%');


-- Add Rama Turaga (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%WebSphere Application Server: Step by Step%'
  AND a.name = 'Rama Turaga'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Owen Cline (order 1)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 1
FROM books b, authors a
WHERE b.title ILIKE '%WebSphere Application Server: Step by Step%'
  AND a.name = 'Owen Cline'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Add Peter Van Sickel (order 2)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 2
FROM books b, authors a
WHERE b.title ILIKE '%WebSphere Application Server: Step by Step%'
  AND a.name = 'Peter Van Sickel'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- Fix: You Want to Do What with PHP?
-- CSV Authors: Kevin Schroeder

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%You Want to Do What with PHP?%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%You Want to Do What with PHP?%');


-- Add Kevin Schroeder (order 0)
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b, authors a
WHERE b.title ILIKE '%You Want to Do What with PHP?%'
  AND a.name = 'Kevin Schroeder'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );


-- =====================================================
-- STEP 3: VERIFICATION QUERIES
-- =====================================================

-- Check for books with no authors (should be empty)
SELECT b.title 
FROM books b 
LEFT JOIN document_authors da ON b.id = da.book_id 
WHERE da.book_id IS NULL;

-- Check for suspicious authors still in use
SELECT b.title, a.name as suspicious_author
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE a.name IN ('admin', 'Admin', 'annegrubb', 'Annegrubb', 'USA Sales', 'Unknown')
ORDER BY b.title;

-- Count multi-author books
SELECT COUNT(*) as multi_author_books
FROM (
  SELECT book_id 
  FROM document_authors 
  GROUP BY book_id 
  HAVING COUNT(*) > 1
) multi;
