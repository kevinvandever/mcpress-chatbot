import csv
import os
from typing import Dict, Optional

class CategoryMapper:
    def __init__(self, csv_path: str = None):
        self.category_map: Dict[str, str] = {}
        
        # Default CSV path - try local first, then desktop
        if csv_path is None:
            local_path = os.path.join(os.path.dirname(__file__), "mc_press_categories.csv")
            desktop_path = "/Users/kevinvandever/Desktop/MC Press LIst of Books & File Size.csv"
            
            if os.path.exists(local_path):
                csv_path = local_path
            elif os.path.exists(desktop_path):
                csv_path = desktop_path
            else:
                csv_path = local_path  # Use local as default
        
        if os.path.exists(csv_path):
            self._load_categories(csv_path)
        else:
            print(f"Warning: Category CSV not found at {csv_path}")
    
    def _load_categories(self, csv_path: str):
        """Load categories from MC Press CSV file"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Get the title and category from the CSV
                    title = row.get('Title', '').strip()
                    category = row.get('Original Category', '').strip()
                    
                    # Skip empty entries
                    if not title or not category:
                        continue
                    
                    # Store mapping by title
                    self.category_map[title.lower()] = category
                    
            print(f"Loaded {len(self.category_map)} category mappings from CSV")
                    
        except Exception as e:
            print(f"Error loading categories from CSV: {e}")
    
    def get_category(self, filename: str) -> str:
        """Get category for a given filename"""
        # Clean filename to get potential title
        title = filename.replace('.pdf', '').strip()
        
        # Try exact match first (case-insensitive)
        category = self.category_map.get(title.lower())
        if category:
            return category
        
        # Try partial matching for common variations
        title_lower = title.lower()
        for csv_title, csv_category in self.category_map.items():
            # Check if the CSV title is contained in the filename
            if csv_title in title_lower or title_lower in csv_title:
                return csv_category
        
        # Fallback to pattern-based categorization
        return self._fallback_categorization(filename)
    
    def _fallback_categorization(self, filename: str) -> str:
        """Fallback categorization based on filename patterns"""
        filename_lower = filename.lower()
        
        # RPG Programming
        if any(keyword in filename_lower for keyword in ['rpg', 'ile', 'cl', 'subfiles', 'free-format']):
            return "RPG"
        
        # Database
        elif any(keyword in filename_lower for keyword in ['db2', 'sql', 'database', 'data governance', 'big data', 'analytics', 'informix', 'lakehouse']):
            return "Database"
        
        # Application Development
        elif any(keyword in filename_lower for keyword in ['websphere', 'rational', 'portal', 'portlets', 'javabeans', 'cloud platform', 'wdsc', 'eclipse']):
            return "Application Development"
        
        # System Administration
        elif any(keyword in filename_lower for keyword in ['security', 'administration', 'compliance', 'identity management', 'disaster recovery', 'virtualization']):
            return "System Administration"
        
        # Management and Career
        elif any(keyword in filename_lower for keyword in ['management', 'leadership', 'career', 'project management', 'without walls', 'corporate programmer']):
            return "Management and Career"
        
        # Operating Systems
        elif any(keyword in filename_lower for keyword in ['ibm i', 'iseries', 'as/400', 'as-400', 'aix', 'system operations', 'mastering', 'qshell']):
            return "Operating Systems"
        
        # Default category
        return "Programming"

# Singleton instance
_category_mapper = None

def get_category_mapper() -> CategoryMapper:
    """Get singleton instance of CategoryMapper"""
    global _category_mapper
    if _category_mapper is None:
        _category_mapper = CategoryMapper()
    return _category_mapper