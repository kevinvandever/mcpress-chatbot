from typing import List, Dict, Any, Optional
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class BookMetadata:
    filename: str
    title: str
    category: str
    subcategory: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    tags: List[str] = None
    description: Optional[str] = None
    total_pages: int = 0
    total_chunks: int = 0
    has_images: bool = False
    has_code: bool = False
    upload_date: str = None
    mc_press_url: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.upload_date is None:
            self.upload_date = datetime.now().isoformat()

class BookManager:
    def __init__(self, metadata_file: str = "books_metadata.json"):
        self.metadata_file = metadata_file
        self.books: Dict[str, BookMetadata] = {}
        self.load_metadata()
        
        # Predefined categories for technical books
        self.categories = {
            "programming": {
                "name": "Programming Languages",
                "subcategories": ["python", "javascript", "java", "c++", "rpg", "cobol", "sql"]
            },
            "systems": {
                "name": "Systems & Architecture", 
                "subcategories": ["ibm-i", "as400", "mainframe", "unix", "linux", "windows"]
            },
            "databases": {
                "name": "Database Systems",
                "subcategories": ["db2", "sql-server", "oracle", "mysql", "postgresql"]
            },
            "web": {
                "name": "Web Development",
                "subcategories": ["frontend", "backend", "frameworks", "apis"]
            },
            "devops": {
                "name": "DevOps & Infrastructure",
                "subcategories": ["deployment", "monitoring", "ci-cd", "containers"]
            },
            "business": {
                "name": "Business Applications",
                "subcategories": ["erp", "crm", "accounting", "hr"]
            }
        }
    
    def validate_url(self, url: str) -> bool:
        """Validate if the provided string is a valid URL"""
        if not url:
            return True  # Empty URLs are allowed (field is optional)
        
        # Basic URL validation pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
    
    def add_book(self, filename: str, title: str = None, category: str = "general", 
                 subcategory: str = None, **kwargs) -> BookMetadata:
        """Add a new book with metadata"""
        if not title:
            title = filename.replace('.pdf', '').replace('_', ' ').title()
        
        # Validate URL if provided
        mc_press_url = kwargs.get('mc_press_url')
        if mc_press_url and not self.validate_url(mc_press_url):
            raise ValueError(f"Invalid URL format: {mc_press_url}")
        
        book = BookMetadata(
            filename=filename,
            title=title,
            category=category,
            subcategory=subcategory,
            **kwargs
        )
        
        self.books[filename] = book
        self.save_metadata()
        return book
    
    def update_book_stats(self, filename: str, total_pages: int, total_chunks: int, 
                         has_images: bool, has_code: bool):
        """Update book statistics after processing"""
        if filename in self.books:
            self.books[filename].total_pages = total_pages
            self.books[filename].total_chunks = total_chunks
            self.books[filename].has_images = has_images
            self.books[filename].has_code = has_code
            self.save_metadata()
    
    def get_books_by_category(self, category: str, subcategory: str = None) -> List[BookMetadata]:
        """Get all books in a specific category/subcategory"""
        books = [book for book in self.books.values() if book.category == category]
        if subcategory:
            books = [book for book in books if book.subcategory == subcategory]
        return books
    
    def search_books(self, query: str) -> List[BookMetadata]:
        """Search books by title, tags, or description"""
        query = query.lower()
        results = []
        
        for book in self.books.values():
            if (query in book.title.lower() or
                query in (book.description or "").lower() or
                any(query in tag.lower() for tag in book.tags)):
                results.append(book)
        
        return results
    
    def get_book_filters(self) -> List[str]:
        """Get list of book filenames for filtering searches"""
        return list(self.books.keys())
    
    def get_categories_summary(self) -> Dict[str, Any]:
        """Get summary of books by category"""
        summary = {}
        for category_id, category_info in self.categories.items():
            books = self.get_books_by_category(category_id)
            summary[category_id] = {
                "name": category_info["name"],
                "count": len(books),
                "subcategories": {}
            }
            
            for subcat in category_info["subcategories"]:
                subcat_books = [b for b in books if b.subcategory == subcat]
                if subcat_books:
                    summary[category_id]["subcategories"][subcat] = len(subcat_books)
        
        return summary
    
    def load_metadata(self):
        """Load book metadata from file"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.books = {
                        filename: BookMetadata(**book_data) 
                        for filename, book_data in data.items()
                    }
            except Exception as e:
                print(f"Error loading metadata: {e}")
                self.books = {}
        else:
            self.books = {}
    
    def save_metadata(self):
        """Save book metadata to file"""
        try:
            data = {filename: asdict(book) for filename, book in self.books.items()}
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def suggest_category(self, filename: str, content_sample: str = "") -> Dict[str, str]:
        """Suggest category based on filename and content"""
        filename_lower = filename.lower()
        content_lower = content_sample.lower()
        
        # Simple heuristics for categorization
        if any(lang in filename_lower or lang in content_lower 
               for lang in ["python", "java", "javascript", "c++", "rpg", "cobol"]):
            return {"category": "programming", "subcategory": "detect_from_content"}
        
        if any(sys in filename_lower or sys in content_lower 
               for sys in ["ibm", "as400", "mainframe", "unix", "linux"]):
            return {"category": "systems", "subcategory": "detect_from_content"}
        
        if any(db in filename_lower or db in content_lower 
               for db in ["database", "sql", "db2", "oracle", "mysql"]):
            return {"category": "databases", "subcategory": "detect_from_content"}
        
        return {"category": "general", "subcategory": None}