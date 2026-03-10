import re
import fitz  # PyMuPDF
from typing import List, Optional, Set
import os
import logging

# Set up logging for author extraction
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthorExtractor:
    def __init__(self):
        # Enhanced patterns for author identification
        self.author_patterns = [
            # "By Author Name" or "by Author Name" - more flexible
            r'(?:^|\n)\s*[Bb]y\s+([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$|[,\.]?\s*(?:with|and|&|\s*$))',
            
            # "Written by Author Name" 
            r'[Ww]ritten\s+by\s+([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$|[,\.]?\s*(?:with|and|&))',
            
            # "Author: Author Name" or "Authors: Author Name"
            r'[Aa]uthors?\s*:\s*([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$)',
            
            # "Authored by Author Name"
            r'[Aa]uthored\s+by\s+([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$)',
            
            # Common name patterns on title pages - First M. Last
            r'(?:^|\n)\s*([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)\s*(?:\n|$)',  
            
            # First Last or First Middle Last - standalone on line
            r'(?:^|\n)\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\n|$)', 
            
            # Publisher-specific patterns for technical books
            r'(?:^|\n)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*(?:\s+[A-Z][a-z]+)+)\s*\n(?:\s*\n)*\s*(?:MC\s+Press|Pearson|O\'Reilly|Wiley|Manning)',
            
            # Copyright line patterns
            r'©\s*\d{4}\s+(?:by\s+)?([A-Za-z][A-Za-z\s\.,\'-]+?)(?:\n|$|[,\.])',
            
            # More flexible "Author Name" at start after title
            r'(?:^|\n)\s*([A-Z][a-z]{2,}\s+(?:[A-Z]\.\s+)?[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\s*(?:\n\s*\n|\n\s*[A-Z])',
            
            # Multi-line author pattern - captures "First Last and First Last" across lines
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+and\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            
            # Pattern for book title pages - authors between edition and publisher
            r'(?:Edition|Version)\s*\n\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)?)\s*\n',
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
        filename = os.path.basename(file_path)
        logger.info(f"🔍 Starting author extraction for: {filename}")
        
        try:
            doc = fitz.open(file_path)
            authors = set()
            
            # Method 1: Try PDF metadata
            logger.info(f"📋 Checking PDF metadata for {filename}")
            metadata_author = self._extract_from_metadata(doc)
            if metadata_author:
                logger.info(f"✅ Found author in metadata: '{metadata_author}'")
                authors.add(metadata_author)
            else:
                logger.info(f"❌ No author found in metadata for {filename}")
            
            # Method 2: Extract from first few pages (title page, copyright page)
            logger.info(f"📄 Analyzing first 3 pages of text for {filename}")
            text_authors = self._extract_from_text(doc, max_pages=3)
            if text_authors:
                logger.info(f"✅ Found {len(text_authors)} potential authors in text: {list(text_authors)}")
                authors.update(text_authors)
            else:
                logger.info(f"❌ No authors found in text analysis for {filename}")
            
            doc.close()
            
            # Return the most likely author
            if authors:
                selected_author = self._select_best_author(authors)
                logger.info(f"🎯 Selected best author for {filename}: '{selected_author}'")
                return selected_author
            else:
                logger.warning(f"⚠️  No author could be extracted from {filename}")
                return None
            
        except Exception as e:
            logger.error(f"💥 Error extracting author from {filename}: {e}")
            return None
    
    def _extract_from_metadata(self, doc) -> Optional[str]:
        """Extract author from PDF metadata"""
        try:
            metadata = doc.metadata
            author = metadata.get('author', '').strip()
            logger.debug(f"📋 Raw metadata author: '{author}'")
            
            if author:
                # Handle single name in metadata (like 'senthil')
                if len(author.split()) == 1 and len(author) > 2:
                    # Single name - capitalize properly
                    cleaned = author.title()
                    logger.debug(f"✅ Single name author from metadata: '{cleaned}'")
                    return cleaned
                elif self._is_valid_author(author):
                    cleaned = self._clean_author_name(author)
                    logger.debug(f"✅ Valid author from metadata: '{cleaned}'")
                    return cleaned
                else:
                    logger.debug(f"❌ Invalid author in metadata: '{author}'")
        except Exception as e:
            logger.debug(f"Error reading metadata: {e}")
        return None
    
    def _extract_from_text(self, doc, max_pages: int = 3) -> Set[str]:
        """Extract author from PDF text content"""
        authors = set()
        
        for page_num in range(min(max_pages, len(doc))):
            try:
                page = doc[page_num]
                text = page.get_text()
                logger.debug(f"📖 Page {page_num + 1} text preview: {text[:200].replace(chr(10), ' ')[:100]}...")
                
                # Try each pattern
                for i, pattern in enumerate(self.author_patterns):
                    matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        # Handle patterns with multiple capture groups (like "and" patterns)
                        if len(match.groups()) > 1:
                            # Multi-author pattern
                            for group_num in range(1, len(match.groups()) + 1):
                                if match.group(group_num):
                                    potential_author = match.group(group_num).strip()
                                    logger.debug(f"🔍 Pattern {i+1} group {group_num} found potential author: '{potential_author}'")
                                    
                                    if self._is_valid_author(potential_author):
                                        cleaned = self._clean_author_name(potential_author)
                                        if cleaned:
                                            authors.add(cleaned)
                                            logger.debug(f"✅ Added valid author: '{cleaned}'")
                                    else:
                                        logger.debug(f"❌ Rejected invalid author: '{potential_author}'")
                        else:
                            # Single author pattern
                            potential_author = match.group(1).strip()
                            logger.debug(f"🔍 Pattern {i+1} found potential author: '{potential_author}'")
                            
                            if self._is_valid_author(potential_author):
                                cleaned = self._clean_author_name(potential_author)
                                if cleaned:
                                    authors.add(cleaned)
                                    logger.debug(f"✅ Added valid author: '{cleaned}'")
                            else:
                                logger.debug(f"❌ Rejected invalid author: '{potential_author}'")
                
            except Exception as e:
                logger.debug(f"Error processing page {page_num + 1}: {e}")
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