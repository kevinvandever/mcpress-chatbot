import re
import fitz  # PyMuPDF
from typing import List, Optional, Set
import os

class AuthorExtractor:
    def __init__(self):
        # Common patterns for author identification
        self.author_patterns = [
            # "By Author Name" or "by Author Name"
            r'(?:^|\n)\s*[Bb]y\s+([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$|[,\.]?\s*(?:with|and|&))',
            
            # "Author Name" at start of line after title
            r'(?:^|\n)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*(?:\s+[A-Z][a-z]+)+)\s*(?:\n|$)',
            
            # "Written by Author Name"
            r'[Ww]ritten\s+by\s+([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$|[,\.]?\s*(?:with|and|&))',
            
            # "Author: Author Name"
            r'[Aa]uthor\s*:\s*([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$)',
            
            # Common name patterns on title pages
            r'(?:^|\n)\s*([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)\s*(?:\n|$)',  # First M. Last
            r'(?:^|\n)\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\n|$)',  # First Last or First Middle Last
        ]
        
        # Words that indicate this is NOT an author name
        self.exclude_words = {
            'press', 'publishing', 'publisher', 'publications', 'books', 'company', 'corp',
            'corporation', 'inc', 'incorporated', 'ltd', 'limited', 'llc', 'systems',
            'international', 'group', 'division', 'department', 'university', 'college',
            'guide', 'manual', 'handbook', 'reference', 'tutorial', 'primer', 'introduction',
            'edition', 'version', 'volume', 'chapter', 'section', 'page', 'contents',
            'table', 'index', 'appendix', 'bibliography', 'glossary', 'preface',
            'foreword', 'acknowledgments', 'copyright', 'rights', 'reserved', 'trademark',
            'registered', 'printing', 'printed', 'bound', 'published', 'isbn', 'library',
            'congress', 'cataloging', 'data', 'information', 'technology', 'computer',
            'software', 'hardware', 'application', 'system', 'database', 'programming',
            'development', 'management', 'administration', 'security', 'analysis',
            'design', 'implementation', 'solutions', 'strategies', 'techniques', 'methods',
            'best', 'practices', 'fundamentals', 'advanced', 'complete', 'comprehensive',
            'step', 'ultimate', 'essential', 'professional', 'expert', 'mastering',
            'learning', 'understanding', 'exploring', 'building', 'creating', 'developing'
        }
    
    def extract_author(self, file_path: str) -> Optional[str]:
        """Extract author from PDF using multiple methods"""
        try:
            doc = fitz.open(file_path)
            authors = set()
            
            # Method 1: Try PDF metadata
            metadata_author = self._extract_from_metadata(doc)
            if metadata_author:
                authors.add(metadata_author)
            
            # Method 2: Extract from first few pages (title page, copyright page)
            text_authors = self._extract_from_text(doc, max_pages=3)
            authors.update(text_authors)
            
            doc.close()
            
            # Return the most likely author
            if authors:
                return self._select_best_author(authors)
            
            return None
            
        except Exception as e:
            print(f"Error extracting author from {file_path}: {e}")
            return None
    
    def _extract_from_metadata(self, doc) -> Optional[str]:
        """Extract author from PDF metadata"""
        try:
            metadata = doc.metadata
            author = metadata.get('author', '').strip()
            if author and self._is_valid_author(author):
                return self._clean_author_name(author)
        except:
            pass
        return None
    
    def _extract_from_text(self, doc, max_pages: int = 3) -> Set[str]:
        """Extract author from PDF text content"""
        authors = set()
        
        for page_num in range(min(max_pages, len(doc))):
            try:
                page = doc[page_num]
                text = page.get_text()
                
                # Try each pattern
                for pattern in self.author_patterns:
                    matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        potential_author = match.group(1).strip()
                        if self._is_valid_author(potential_author):
                            cleaned = self._clean_author_name(potential_author)
                            if cleaned:
                                authors.add(cleaned)
                
            except Exception as e:
                continue
        
        return authors
    
    def _is_valid_author(self, name: str) -> bool:
        """Check if a potential author name is valid"""
        if not name or len(name.strip()) < 3:
            return False
        
        name_lower = name.lower().strip()
        
        # Check for excluded words
        for word in self.exclude_words:
            if word in name_lower:
                return False
        
        # Must contain at least one space (first and last name)
        if ' ' not in name.strip():
            return False
        
        # Should not be too long (likely a sentence)
        if len(name) > 50:
            return False
        
        # Should not contain too many special characters
        special_chars = sum(1 for c in name if not c.isalnum() and c not in ' .,-\'')
        if special_chars > 2:
            return False
        
        # Should start with a capital letter
        if not name[0].isupper():
            return False
        
        # Should have at least 2 words
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word should start with capital (with some exceptions)
        for word in words:
            if len(word) > 1 and not word[0].isupper() and word.lower() not in ['de', 'von', 'van', 'del', 'la', 'le']:
                return False
        
        return True
    
    def _clean_author_name(self, name: str) -> str:
        """Clean and standardize author name"""
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove trailing punctuation
        name = re.sub(r'[,\.\s]+$', '', name)
        
        # Remove common prefixes/suffixes
        name = re.sub(r'^(Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(Jr\.?|Sr\.?|III?|IV)$', '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _select_best_author(self, authors: Set[str]) -> str:
        """Select the most likely author from candidates"""
        if not authors:
            return None
        
        if len(authors) == 1:
            return list(authors)[0]
        
        # Prefer shorter, simpler names (likely to be actual authors vs. titles/descriptions)
        sorted_authors = sorted(authors, key=lambda x: (len(x.split()), len(x)))
        
        # Return the simplest candidate
        return sorted_authors[0]

# Singleton instance
_author_extractor = None

def get_author_extractor() -> AuthorExtractor:
    """Get singleton instance of AuthorExtractor"""
    global _author_extractor
    if _author_extractor is None:
        _author_extractor = AuthorExtractor()
    return _author_extractor