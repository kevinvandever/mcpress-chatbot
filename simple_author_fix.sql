-- Simple fix for the 3 specific author issues
-- Run this on Railway database

-- Fix 1: Complete CL: Sixth Edition should show Ted Holt
UPDATE books 
SET author = 'Ted Holt' 
WHERE title ILIKE '%Complete CL%Sixth%';

-- Fix 2: Subfiles in Free-Format RPG should show Kevin Vandever  
UPDATE books 
SET author = 'Kevin Vandever' 
WHERE title ILIKE '%Subfiles%Free%';

-- Fix 3: Control Language Programming should show multiple authors
UPDATE books 
SET author = 'Jim Buck, Bryan Meyers, Dan Riehl' 
WHERE title ILIKE '%Control Language Programming%';

-- Verify the fixes
SELECT title, author FROM books 
WHERE title ILIKE '%Complete CL%Sixth%' 
   OR title ILIKE '%Subfiles%Free%' 
   OR title ILIKE '%Control Language Programming%';