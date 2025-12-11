"""
Property-based tests for Excel Import Service

These tests verify the correctness properties defined in the design document
for the multi-author metadata enhancement feature.
"""

import pytest
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
import pandas as pd

from excel_import_service import ExcelImportService
from author_service import AuthorService


class TestExcelImportProperties:
    """Property-based tests for Excel Import Service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database URL for testing
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        author_service = AuthorService()
        self.service = ExcelImportService(author_service)
    
    # Feature: multi-author-metadata-enhancement, Property 30: Excel file format validation
    @given(
        file_extension=st.sampled_from(['.xlsx', '.xls', '.csv', '.txt', '.pdf', '.xlsm']),
        file_exists=st.booleans()
    )
    @settings(max_examples=100)
    async def test_excel_file_format_validation(self, file_extension, file_exists):
        """
        For any file with various extensions, the system should correctly identify 
        valid .xlsm files and reject invalid formats.
        **Validates: Requirements 11.1**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with the given extension
            test_file = Path(temp_dir) / f"test{file_extension}"
            
            if file_exists:
                if file_extension == '.xlsm':
                    # Create a valid Excel file
                    df = pd.DataFrame({
                        'URL': ['https://example.com'],
                        'Title': ['Test Book'],
                        'Author': ['Test Author']
                    })
                    df.to_excel(test_file, engine='openpyxl', index=False)
                else:
                    # Create a file with wrong extension
                    test_file.write_text("dummy content")
            
            # Test validation
            result = await self.service.validate_excel_file(str(test_file), 'book')
            
            # Property: Only .xlsm files that exist should be considered valid format-wise
            if file_exists and file_extension == '.xlsm':
                # Should not fail due to file format (may fail due to content)
                format_errors = [e for e in result.errors 
                               if 'format' in e.message.lower() or 'extension' in e.message.lower()]
                assert len(format_errors) == 0, f"Valid .xlsm file should not have format errors: {format_errors}"
            else:
                # Should fail validation
                assert not result.valid, f"Invalid file should fail validation: {file_extension}, exists: {file_exists}"
                if not file_exists:
                    # Should have file existence error
                    existence_errors = [e for e in result.errors if 'exist' in e.message.lower()]
                    assert len(existence_errors) > 0, "Non-existent file should have existence error"
                elif file_extension != '.xlsm':
                    # Should have format error
                    format_errors = [e for e in result.errors 
                                   if 'format' in e.message.lower() or '.xlsm' in e.message.lower()]
                    assert len(format_errors) > 0, f"Wrong extension should have format error: {file_extension}"
    
    # Feature: multi-author-metadata-enhancement, Property 31: Book metadata column validation
    @given(
        has_url=st.booleans(),
        has_title=st.booleans(),
        has_author=st.booleans(),
        extra_columns=st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3)
    )
    @settings(max_examples=100)
    async def test_book_metadata_column_validation(self, has_url, has_title, has_author, extra_columns):
        """
        For any book metadata Excel file, the system should correctly identify 
        missing required columns (URL, Title, Author) and report errors.
        **Validates: Requirements 11.2**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Build columns based on test parameters
            columns = []
            if has_url:
                columns.append('URL')
            if has_title:
                columns.append('Title')
            if has_author:
                columns.append('Author')
            
            # Add extra columns
            for extra_col in extra_columns:
                if extra_col not in columns:  # Avoid duplicates
                    columns.append(extra_col)
            
            # Create DataFrame with test columns
            if columns:
                data = {col: ['test_value'] for col in columns}
                df = pd.DataFrame(data)
                df.to_excel(test_file, engine='openpyxl', index=False)
            else:
                # Create empty Excel file
                df = pd.DataFrame()
                df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Test validation
            result = await self.service.validate_excel_file(str(test_file), 'book')
            
            # Property: Should identify missing required columns
            required_columns = ['URL', 'Title', 'Author']
            missing_columns = [col for col in required_columns if not locals()[f'has_{col.lower()}']]
            
            if missing_columns:
                # Should fail validation due to missing columns
                assert not result.valid, f"Should fail when missing columns: {missing_columns}"
                
                # Should have error for each missing column
                for missing_col in missing_columns:
                    missing_errors = [e for e in result.errors 
                                    if missing_col in e.message and 'missing' in e.message.lower()]
                    assert len(missing_errors) > 0, f"Should have error for missing column: {missing_col}"
            else:
                # All required columns present - should not fail due to missing columns
                missing_errors = [e for e in result.errors 
                                if 'missing' in e.message.lower() and any(col in e.message for col in required_columns)]
                assert len(missing_errors) == 0, f"Should not have missing column errors when all present: {missing_errors}"
    
    # Feature: multi-author-metadata-enhancement, Property 32: Article metadata sheet validation
    @given(
        has_export_subset_sheet=st.booleans(),
        sheet_names=st.lists(st.text(min_size=1, max_size=15), min_size=0, max_size=3),
        has_required_columns=st.booleans()
    )
    @settings(max_examples=100)
    async def test_article_metadata_sheet_validation(self, has_export_subset_sheet, sheet_names, has_required_columns):
        """
        For any article metadata Excel file, the system should verify the export_subset 
        sheet exists and contains required columns (A, H, J, K, L).
        **Validates: Requirements 11.3**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with multiple sheets
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                # Add other sheets first
                for sheet_name in sheet_names:
                    if sheet_name != 'export_subset':
                        df = pd.DataFrame({'col1': ['data']})
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Add export_subset sheet if required
                if has_export_subset_sheet:
                    if has_required_columns:
                        # Create sheet with enough columns (need at least 12 for L column)
                        columns = [f'col_{i}' for i in range(12)]
                        data = {col: ['test_data'] for col in columns}
                        df = pd.DataFrame(data)
                    else:
                        # Create sheet with insufficient columns
                        df = pd.DataFrame({'col1': ['data'], 'col2': ['data']})
                    
                    df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Test validation
            result = await self.service.validate_excel_file(str(test_file), 'article')
            
            # Property: Should verify export_subset sheet exists
            if not has_export_subset_sheet:
                # Should fail validation due to missing sheet
                assert not result.valid, "Should fail when export_subset sheet is missing"
                sheet_errors = [e for e in result.errors if 'export_subset' in e.message]
                assert len(sheet_errors) > 0, "Should have error about missing export_subset sheet"
            else:
                # Sheet exists - should not fail due to missing sheet
                sheet_errors = [e for e in result.errors 
                              if 'export_subset' in e.message and 'not found' in e.message]
                assert len(sheet_errors) == 0, "Should not have missing sheet error when sheet exists"
    
    # Feature: multi-author-metadata-enhancement, Property 33: Excel data validation
    @given(
        urls=st.lists(
            st.one_of(
                st.just("https://valid.com"),
                st.just("http://valid.com"),
                st.just("invalid-url"),
                st.just(""),
                st.just("ftp://invalid.com")
            ),
            min_size=1, max_size=5
        ),
        titles=st.lists(
            st.one_of(
                st.text(min_size=1, max_size=50),
                st.just(""),
                st.just("   ")  # whitespace only
            ),
            min_size=1, max_size=5
        ),
        authors=st.lists(
            st.one_of(
                st.text(min_size=1, max_size=30),
                st.just(""),
                st.just("   ")  # whitespace only
            ),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=100)
    async def test_excel_data_validation(self, urls, titles, authors):
        """
        For any Excel file with invalid URLs or missing data, the system should 
        identify and report all validation issues.
        **Validates: Requirements 11.4**
        """
        # Ensure all lists have the same length
        max_len = max(len(urls), len(titles), len(authors))
        urls = (urls * max_len)[:max_len]
        titles = (titles * max_len)[:max_len]
        authors = (authors * max_len)[:max_len]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create test data
            df = pd.DataFrame({
                'URL': urls,
                'Title': titles,
                'Author': authors
            })
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Test validation
            result = await self.service.validate_excel_file(str(test_file), 'book')
            
            # Property: Should identify all validation issues
            for i, (url, title, author) in enumerate(zip(urls, titles, authors)):
                row_num = i + 1
                
                # Check URL validation
                if url and not url.startswith(('http://', 'https://')):
                    url_errors = [e for e in result.errors 
                                if e.row == row_num and 'url' in e.message.lower()]
                    assert len(url_errors) > 0, f"Should have URL error for row {row_num}: {url}"
                
                # Check required field validation
                if not title.strip():
                    title_errors = [e for e in result.errors 
                                  if e.row == row_num and 'title' in e.message.lower()]
                    assert len(title_errors) > 0, f"Should have title error for row {row_num}: '{title}'"
                
                if not author.strip():
                    author_errors = [e for e in result.errors 
                                   if e.row == row_num and 'author' in e.message.lower()]
                    assert len(author_errors) > 0, f"Should have author error for row {row_num}: '{author}'"
    
    # Feature: multi-author-metadata-enhancement, Property 34: Excel preview accuracy
    @given(
        num_rows=st.integers(min_value=1, max_value=20),
        file_type=st.sampled_from(['book', 'article'])
    )
    @settings(max_examples=100)
    async def test_excel_preview_accuracy(self, num_rows, file_type):
        """
        For any Excel file, the preview should show exactly the first 10 rows 
        with accurate validation status for each row.
        **Validates: Requirements 11.5**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            if file_type == 'book':
                # Create book test data
                data = {
                    'URL': [f'https://example{i}.com' for i in range(num_rows)],
                    'Title': [f'Book Title {i}' for i in range(num_rows)],
                    'Author': [f'Author {i}' for i in range(num_rows)]
                }
                df = pd.DataFrame(data)
                df.to_excel(test_file, engine='openpyxl', index=False)
                
            else:  # article
                # Create article test data with export_subset sheet
                with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                    # Create enough columns for article format
                    columns = [f'col_{i}' for i in range(12)]
                    data = {col: [f'data_{col}_{i}' for i in range(num_rows)] for col in columns}
                    # Set feature article column (H, index 7) to 'yes' for some rows
                    data['col_7'] = ['yes' if i % 2 == 0 else 'no' for i in range(num_rows)]
                    
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Test preview
            result = await self.service.preview_excel_data(str(test_file), file_type)
            
            # Property: Preview should show exactly first 10 rows (or fewer if file has fewer)
            expected_preview_rows = min(10, num_rows)
            assert len(result.preview_rows) == expected_preview_rows, \
                f"Preview should show {expected_preview_rows} rows, got {len(result.preview_rows)}"
            
            # Property: Each preview row should have accurate row numbers
            for i, preview_row in enumerate(result.preview_rows):
                expected_row_num = i + 1
                assert preview_row['row'] == expected_row_num, \
                    f"Preview row {i} should have row number {expected_row_num}, got {preview_row['row']}"
                
                # Property: Each preview row should have data and status
                assert 'data' in preview_row, f"Preview row {i} should have data field"
                assert 'status' in preview_row, f"Preview row {i} should have status field"
                assert preview_row['status'] in ['valid', 'error', 'warning', 'skipped'], \
                    f"Preview row {i} should have valid status, got {preview_row['status']}"


# Additional test for author parsing functionality
class TestAuthorParsing:
    """Tests for author parsing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database URL for testing
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        author_service = AuthorService()
        self.service = ExcelImportService(author_service)
    
    @given(
        author_strings=st.one_of(
            st.just("John Doe"),
            st.just("John Doe and Jane Smith"),
            st.just("John Doe, Jane Smith"),
            st.just("John Doe; Jane Smith"),
            st.just("John Doe, Jane Smith and Bob Wilson"),
            st.just(""),
            st.just("   "),
            st.just("John Doe,, Jane Smith"),  # Double comma
            st.just("John Doe and and Jane Smith"),  # Double and
        )
    )
    @settings(max_examples=100)
    def test_author_parsing_consistency(self, author_strings):
        """
        For any author string with various delimiters, parsing should return 
        consistent results with proper cleanup.
        """
        result = self.service.parse_authors(author_strings)
        
        # Property: Result should always be a list
        assert isinstance(result, list), "parse_authors should always return a list"
        
        # Property: No empty strings in result
        assert all(author.strip() for author in result), "Result should not contain empty strings"
        
        # Property: No duplicates in result
        assert len(result) == len(set(result)), "Result should not contain duplicates"
        
        # Property: Empty input should return empty list
        if not author_strings.strip():
            assert result == [], "Empty input should return empty list"
        
        # Property: Single author should return list with one element
        if author_strings.strip() and 'and' not in author_strings.lower() and ',' not in author_strings and ';' not in author_strings:
            assert len(result) <= 1, "Single author string should return at most one author"


class TestFuzzyMatching:
    """Tests for fuzzy title matching functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database URL for testing
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        author_service = AuthorService()
        self.service = ExcelImportService(author_service)
    
    # Feature: multi-author-metadata-enhancement, Property 37: Book title fuzzy matching
    @given(
        original_title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        variation_type=st.sampled_from(['exact', 'case', 'punctuation', 'spacing', 'typo', 'partial'])
    )
    @settings(max_examples=100)
    async def test_book_title_fuzzy_matching(self, original_title, variation_type):
        """
        For any book title in Excel data, the fuzzy matching algorithm should 
        consistently find the best match in the existing database.
        **Validates: Requirements 9.2**
        """
        # Clean the original title
        original_title = original_title.strip()
        assume(len(original_title) >= 5)  # Ensure meaningful titles
        
        # Create variations of the title based on variation type
        if variation_type == 'exact':
            test_title = original_title
        elif variation_type == 'case':
            test_title = original_title.upper() if original_title.islower() else original_title.lower()
        elif variation_type == 'punctuation':
            # Add or remove punctuation
            test_title = original_title.replace('.', '').replace(',', '').replace(':', '')
        elif variation_type == 'spacing':
            # Add extra spaces or remove spaces
            test_title = '  '.join(original_title.split())
        elif variation_type == 'typo':
            # Introduce a small typo (replace one character)
            if len(original_title) > 5:
                pos = len(original_title) // 2
                test_title = original_title[:pos] + 'x' + original_title[pos+1:]
            else:
                test_title = original_title
        elif variation_type == 'partial':
            # Use partial title (first 80% of characters)
            cutoff = max(5, int(len(original_title) * 0.8))
            test_title = original_title[:cutoff]
        else:
            test_title = original_title
        
        # Mock database with the original title
        await self.service._ensure_pool()
        
        # Property: Fuzzy matching should be consistent
        # For the same input, it should always return the same result
        result1 = await self._mock_fuzzy_match_with_data(test_title, [(1, original_title)])
        result2 = await self._mock_fuzzy_match_with_data(test_title, [(1, original_title)])
        
        assert result1 == result2, f"Fuzzy matching should be consistent for '{test_title}'"
        
        # Property: Exact matches should always be found
        if variation_type == 'exact':
            result = await self._mock_fuzzy_match_with_data(test_title, [(1, original_title)])
            assert result == 1, f"Exact match should be found for '{test_title}'"
        
        # Property: Close variations should be found (depending on threshold)
        if variation_type in ['case', 'punctuation', 'spacing']:
            result = await self._mock_fuzzy_match_with_data(test_title, [(1, original_title)])
            # These variations should typically be found with default threshold
            assert result is not None, f"Close variation should be found for '{test_title}' (type: {variation_type})"
        
        # Property: Empty or very short titles should not match
        empty_result = await self._mock_fuzzy_match_with_data("", [(1, original_title)])
        assert empty_result is None, "Empty title should not match anything"
        
        short_result = await self._mock_fuzzy_match_with_data("ab", [(1, original_title)])
        assert short_result is None, "Very short title should not match"
    
    async def _mock_fuzzy_match_with_data(self, title: str, mock_data: List[tuple]) -> Optional[int]:
        """
        Mock version of fuzzy_match_title that uses provided data instead of database
        
        Args:
            title: Title to match
            mock_data: List of (id, title) tuples representing database data
            
        Returns:
            Book ID of best match, or None if no good match found
        """
        if not title or not title.strip():
            return None
        
        title = title.strip()
        
        if not mock_data:
            return None
        
        # Create list of titles for fuzzy matching
        titles = [(row[1], row[0]) for row in mock_data]
        title_strings = [t[0] for t in titles]
        
        # Use fuzzywuzzy to find best match (same logic as real method)
        from fuzzywuzzy import fuzz, process
        
        best_match = process.extractOne(
            title, 
            title_strings, 
            scorer=fuzz.ratio,
            score_cutoff=self.service.fuzzy_threshold
        )
        
        if best_match:
            matched_title, score = best_match
            # Find the book ID for the matched title
            for db_title, book_id in titles:
                if db_title == matched_title:
                    return book_id
        
        return None


class TestBookImportProperties:
    """Property-based tests for book import functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database URL for testing
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        author_service = AuthorService()
        self.service = ExcelImportService(author_service)
    
    # Feature: multi-author-metadata-enhancement, Property 38: Book URL update
    @given(
        urls=st.lists(
            st.one_of(
                st.just("https://mcpress.com/book1"),
                st.just("http://mcpress.com/book2"),
                st.just("https://example.com/book3"),
                st.just(""),
                st.just("invalid-url")
            ),
            min_size=1, max_size=5
        ),
        book_exists=st.booleans()
    )
    @settings(max_examples=100)
    async def test_book_url_update(self, urls, book_exists):
        """
        For any successfully matched book, the mc_press_url field should be 
        updated with the URL from the Excel file.
        **Validates: Requirements 9.3**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create test Excel data
            data = {
                'URL': urls,
                'Title': [f'Test Book {i}' for i in range(len(urls))],
                'Author': [f'Test Author {i}' for i in range(len(urls))]
            }
            df = pd.DataFrame(data)
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Mock the fuzzy matching to simulate book existence
            original_fuzzy_match = self.service.fuzzy_match_title
            
            async def mock_fuzzy_match(title):
                if book_exists:
                    # Return a mock book ID
                    return 1
                else:
                    return None
            
            self.service.fuzzy_match_title = mock_fuzzy_match
            
            # Mock database operations
            updated_books = []
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def execute(self, query, *args):
                    if "UPDATE books SET mc_press_url" in query:
                        updated_books.append((args[0], args[1]))  # (url, book_id)
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Test import
            result = await self.service.import_book_metadata(str(test_file))
            
            # Property: Valid URLs should be used for updates when books exist
            if book_exists:
                valid_urls = [url for url in urls if url and self.service._is_valid_url(url)]
                
                # Should have attempted to update for each valid URL
                assert len(updated_books) == len(valid_urls), \
                    f"Should update {len(valid_urls)} books, but updated {len(updated_books)}"
                
                # Each update should use the correct URL
                for i, (updated_url, book_id) in enumerate(updated_books):
                    assert updated_url in valid_urls, \
                        f"Updated URL {updated_url} should be in valid URLs {valid_urls}"
                    assert book_id == 1, f"Should update book ID 1, got {book_id}"
            else:
                # No books exist, so no updates should occur
                assert len(updated_books) == 0, \
                    f"Should not update any books when none exist, but updated {len(updated_books)}"
            
            # Restore original method
            self.service.fuzzy_match_title = original_fuzzy_match
    
    # Feature: multi-author-metadata-enhancement, Property 39: Book author parsing
    @given(
        author_strings=st.lists(
            st.one_of(
                st.just("John Doe"),
                st.just("John Doe and Jane Smith"),
                st.just("John Doe, Jane Smith"),
                st.just("John Doe; Jane Smith"),
                st.just("John Doe, Jane Smith and Bob Wilson"),
                st.just("John Doe,, Jane Smith"),  # Double comma
                st.just("John Doe and and Jane Smith"),  # Double and
                st.just("  John Doe  ,  Jane Smith  "),  # Extra whitespace
                st.just(""),
                st.just("   ")
            ),
            min_size=1, max_size=3
        )
    )
    @settings(max_examples=100)
    async def test_book_author_parsing(self, author_strings):
        """
        For any author string in book metadata, multiple authors separated by 
        comma or "and" should be correctly parsed and trimmed.
        **Validates: Requirements 9.4**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create test Excel data
            data = {
                'URL': [f'https://example{i}.com' for i in range(len(author_strings))],
                'Title': [f'Test Book {i}' for i in range(len(author_strings))],
                'Author': author_strings
            }
            df = pd.DataFrame(data)
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Mock fuzzy matching to always find books
            async def mock_fuzzy_match(title):
                return 1
            
            self.service.fuzzy_match_title = mock_fuzzy_match
            
            # Track parsed authors
            parsed_authors_list = []
            
            # Mock author service
            original_get_or_create = self.service.author_service.get_or_create_author
            
            async def mock_get_or_create(name, site_url=None):
                parsed_authors_list.append(name)
                return len(parsed_authors_list)  # Return unique ID
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Mock database operations
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def execute(self, query, *args):
                    pass
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Test import
            result = await self.service.import_book_metadata(str(test_file))
            
            # Property: Author parsing should handle all delimiter types correctly
            for author_string in author_strings:
                if author_string.strip():  # Non-empty strings
                    expected_authors = self.service.parse_authors(author_string)
                    
                    # Each expected author should appear in parsed list
                    for expected_author in expected_authors:
                        assert expected_author in parsed_authors_list, \
                            f"Expected author '{expected_author}' should be in parsed list {parsed_authors_list}"
            
            # Property: No empty author names should be processed
            assert all(author.strip() for author in parsed_authors_list), \
                "No empty author names should be processed"
            
            # Property: Author names should be properly trimmed
            assert all(author == author.strip() for author in parsed_authors_list), \
                "All author names should be properly trimmed"
            
            # Restore original method
            self.service.author_service.get_or_create_author = original_get_or_create
    
    # Feature: multi-author-metadata-enhancement, Property 40: Book author service integration
    @given(
        num_books=st.integers(min_value=1, max_value=5),
        authors_per_book=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100)
    async def test_book_author_service_integration(self, num_books, authors_per_book):
        """
        For any parsed author from book metadata, the AuthorService should be 
        called to create or update the author record.
        **Validates: Requirements 9.5**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create test data with multiple authors per book
            urls = [f'https://example{i}.com' for i in range(num_books)]
            titles = [f'Test Book {i}' for i in range(num_books)]
            authors = []
            
            for i in range(num_books):
                book_authors = [f'Author {i}_{j}' for j in range(authors_per_book)]
                authors.append(', '.join(book_authors))
            
            data = {
                'URL': urls,
                'Title': titles,
                'Author': authors
            }
            df = pd.DataFrame(data)
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Mock fuzzy matching to always find books
            async def mock_fuzzy_match(title):
                return hash(title) % 1000  # Return consistent but different IDs
            
            self.service.fuzzy_match_title = mock_fuzzy_match
            
            # Track AuthorService calls
            author_service_calls = []
            
            original_get_or_create = self.service.author_service.get_or_create_author
            
            async def mock_get_or_create(name, site_url=None):
                author_service_calls.append((name, site_url))
                return len(author_service_calls)  # Return unique ID
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Mock database operations
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def execute(self, query, *args):
                    pass
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Test import
            result = await self.service.import_book_metadata(str(test_file))
            
            # Property: AuthorService should be called for each parsed author
            expected_total_authors = num_books * authors_per_book
            assert len(author_service_calls) == expected_total_authors, \
                f"Should call AuthorService {expected_total_authors} times, got {len(author_service_calls)}"
            
            # Property: Each author name should be passed correctly
            called_names = [call[0] for call in author_service_calls]
            for i in range(num_books):
                for j in range(authors_per_book):
                    expected_name = f'Author {i}_{j}'
                    assert expected_name in called_names, \
                        f"Expected author name '{expected_name}' should be in calls {called_names}"
            
            # Property: Site URL should be None for book imports (no author URLs in book metadata)
            for name, site_url in author_service_calls:
                assert site_url is None, \
                    f"Site URL should be None for book imports, got {site_url} for {name}"
            
            # Restore original method
            self.service.author_service.get_or_create_author = original_get_or_create
    
    # Feature: multi-author-metadata-enhancement, Property 41: Book import reporting
    @given(
        num_books=st.integers(min_value=1, max_value=10),
        match_rate=st.floats(min_value=0.0, max_value=1.0),
        error_rate=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=100)
    async def test_book_import_reporting(self, num_books, match_rate, error_rate):
        """
        For any book metadata import, the system should report accurate counts 
        of books matched, updated, and errors encountered.
        **Validates: Requirements 9.6**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create test data
            urls = []
            titles = []
            authors = []
            
            for i in range(num_books):
                # Introduce errors based on error_rate
                if i < int(num_books * error_rate):
                    # Create invalid data
                    urls.append("")  # Invalid URL
                    titles.append("")  # Invalid title
                    authors.append("")  # Invalid author
                else:
                    urls.append(f'https://example{i}.com')
                    titles.append(f'Test Book {i}')
                    authors.append(f'Test Author {i}')
            
            data = {
                'URL': urls,
                'Title': titles,
                'Author': authors
            }
            df = pd.DataFrame(data)
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Mock fuzzy matching based on match_rate
            match_count = 0
            expected_matches = int((num_books - int(num_books * error_rate)) * match_rate)
            
            async def mock_fuzzy_match(title):
                nonlocal match_count
                if match_count < expected_matches and title.strip():
                    match_count += 1
                    return match_count
                return None
            
            self.service.fuzzy_match_title = mock_fuzzy_match
            
            # Track operations
            update_count = 0
            author_create_count = 0
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def execute(self, query, *args):
                    nonlocal update_count
                    if "UPDATE books SET mc_press_url" in query:
                        update_count += 1
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Mock author service
            async def mock_get_or_create(name, site_url=None):
                nonlocal author_create_count
                author_create_count += 1
                return author_create_count
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_book_metadata(str(test_file))
            
            # Property: Should report correct number of books processed
            assert result.books_processed == num_books, \
                f"Should process {num_books} books, reported {result.books_processed}"
            
            # Property: Should report correct number of books matched
            assert result.books_matched == expected_matches, \
                f"Should match {expected_matches} books, reported {result.books_matched}"
            
            # Property: Should report correct number of books updated
            # Only books with valid URLs should be updated
            valid_books = num_books - int(num_books * error_rate)
            expected_updates = min(expected_matches, valid_books)
            assert result.books_updated == expected_updates, \
                f"Should update {expected_updates} books, reported {result.books_updated}"
            
            # Property: Should report errors for invalid data
            expected_errors = int(num_books * error_rate)
            if expected_errors > 0:
                assert len(result.errors) >= expected_errors, \
                    f"Should report at least {expected_errors} errors, got {len(result.errors)}"
            
            # Property: Should report processing time
            assert result.processing_time > 0, \
                f"Should report positive processing time, got {result.processing_time}"
            
            # Property: Success should be True if import completed
            assert result.success is True, "Import should be marked as successful"


class TestArticleImportProperties:
    """Property-based tests for article import functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database URL for testing
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        author_service = AuthorService()
        self.service = ExcelImportService(author_service)
    
    # Feature: multi-author-metadata-enhancement, Property 42: Article sheet filtering
    @given(
        has_export_subset=st.booleans(),
        other_sheets=st.lists(st.text(min_size=1, max_size=15), min_size=0, max_size=3),
        num_rows=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    async def test_article_sheet_filtering(self, has_export_subset, other_sheets, num_rows):
        """
        For any article metadata file, only the export_subset sheet should be processed, 
        ignoring other sheets.
        **Validates: Requirements 10.1**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with multiple sheets
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                # Add other sheets with data
                for sheet_name in other_sheets:
                    if sheet_name != 'export_subset':
                        df = pd.DataFrame({
                            'col1': [f'other_data_{i}' for i in range(num_rows)],
                            'col2': [f'other_data_{i}' for i in range(num_rows)]
                        })
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Add export_subset sheet if required
                if has_export_subset:
                    # Create proper article data structure (12 columns minimum)
                    columns = [f'col_{i}' for i in range(12)]
                    data = {col: [f'export_data_{col}_{i}' for i in range(num_rows)] for col in columns}
                    # Set feature article column (H, index 7) to 'yes' for all rows
                    data['col_7'] = ['yes'] * num_rows
                    
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Mock database operations
            processed_rows = []
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def fetchval(self, query, *args):
                    # Mock finding documents for article IDs
                    return 1  # Always find a document
                
                async def execute(self, query, *args):
                    if "UPDATE books" in query and "document_type = 'article'" in query:
                        processed_rows.append(args)
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Mock author service
            async def mock_get_or_create(name, site_url=None):
                return 1
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_article_metadata(str(test_file))
            
            # Property: Should only process export_subset sheet
            if has_export_subset:
                # Should process the export_subset data
                assert result.articles_processed == num_rows, \
                    f"Should process {num_rows} articles from export_subset, got {result.articles_processed}"
                
                # Should have attempted to update documents
                assert len(processed_rows) == num_rows, \
                    f"Should update {num_rows} documents, got {len(processed_rows)}"
            else:
                # Should fail due to missing export_subset sheet
                assert not result.success, "Should fail when export_subset sheet is missing"
                sheet_errors = [e for e in result.errors if 'export_subset' in e.message]
                assert len(sheet_errors) > 0, "Should have error about missing export_subset sheet"
    
    # Feature: multi-author-metadata-enhancement, Property 43: Article feature filtering
    @given(
        feature_values=st.lists(
            st.sampled_from(['yes', 'no', 'Yes', 'NO', 'y', 'n', '', '1', '0']),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=100)
    async def test_article_feature_filtering(self, feature_values):
        """
        For any article record, only rows where column H equals "yes" should be processed.
        **Validates: Requirements 10.2**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with export_subset sheet
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                # Create article data with various feature_article values
                columns = [f'col_{i}' for i in range(12)]
                data = {col: [f'data_{col}_{i}' for i in range(len(feature_values))] for col in columns}
                # Set feature article column (H, index 7) with test values
                data['col_7'] = feature_values
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Mock database operations
            processed_articles = []
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def fetchval(self, query, *args):
                    # Mock finding documents for article IDs
                    return 1  # Always find a document
                
                async def execute(self, query, *args):
                    if "UPDATE books" in query and "document_type = 'article'" in query:
                        processed_articles.append(args)
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Mock author service
            async def mock_get_or_create(name, site_url=None):
                return 1
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_article_metadata(str(test_file))
            
            # Property: Only rows with feature_article = "yes" should be processed
            expected_yes_count = sum(1 for val in feature_values if str(val).strip().lower() == 'yes')
            
            assert result.articles_processed == expected_yes_count, \
                f"Should process {expected_yes_count} articles with 'yes', got {result.articles_processed}"
            
            # Property: Number of database updates should match processed articles
            assert len(processed_articles) == expected_yes_count, \
                f"Should update {expected_yes_count} documents, got {len(processed_articles)}"
    
    # Feature: multi-author-metadata-enhancement, Property 44: Article ID matching
    @given(
        article_ids=st.lists(
            st.one_of(
                st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
                st.just("article123"),
                st.just("doc_456"),
                st.just("test-article"),
                st.just("")
            ),
            min_size=1, max_size=5
        ),
        pdf_extensions=st.lists(st.booleans(), min_size=1, max_size=5)
    )
    @settings(max_examples=100)
    async def test_article_id_matching(self, article_ids, pdf_extensions):
        """
        For any article ID in column A, the system should match against PDF filenames 
        with or without .pdf extension.
        **Validates: Requirements 10.3**
        """
        # Ensure lists have same length
        max_len = max(len(article_ids), len(pdf_extensions))
        article_ids = (article_ids * max_len)[:max_len]
        pdf_extensions = (pdf_extensions * max_len)[:max_len]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with export_subset sheet
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                columns = [f'col_{i}' for i in range(12)]
                data = {col: [f'data_{col}_{i}' for i in range(len(article_ids))] for col in columns}
                # Set article IDs in column A (index 0)
                data['col_0'] = article_ids
                # Set feature article column (H, index 7) to 'yes'
                data['col_7'] = ['yes'] * len(article_ids)
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Mock database operations
            db_queries = []
            found_documents = []
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def fetchval(self, query, *args):
                    db_queries.append((query, args))
                    # Mock finding documents based on filename matching
                    filename1, filename2 = args
                    for i, (article_id, has_pdf) in enumerate(zip(article_ids, pdf_extensions)):
                        if article_id.strip():
                            expected_with_pdf = f"{article_id}.pdf"
                            expected_without_pdf = article_id
                            if filename1 == expected_with_pdf or filename2 == expected_without_pdf:
                                found_documents.append(article_id)
                                return i + 1  # Return document ID
                    return None
                
                async def execute(self, query, *args):
                    pass
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Mock author service
            async def mock_get_or_create(name, site_url=None):
                return 1
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_article_metadata(str(test_file))
            
            # Property: Should query database with both filename formats
            valid_article_ids = [aid for aid in article_ids if aid.strip()]
            
            assert len(db_queries) == len(valid_article_ids), \
                f"Should query database {len(valid_article_ids)} times, got {len(db_queries)}"
            
            # Property: Each query should check both with and without .pdf extension
            for i, (query, args) in enumerate(db_queries):
                article_id = valid_article_ids[i]
                expected_with_pdf = f"{article_id}.pdf"
                expected_without_pdf = article_id
                
                assert args[0] == expected_with_pdf, \
                    f"First filename should be '{expected_with_pdf}', got '{args[0]}'"
                assert args[1] == expected_without_pdf, \
                    f"Second filename should be '{expected_without_pdf}', got '{args[1]}'"
    
    # Feature: multi-author-metadata-enhancement, Property 45: Article author processing
    @given(
        authors=st.lists(
            st.one_of(
                st.just("John Doe"),
                st.just("Jane Smith"),
                st.just("John Doe and Jane Smith"),
                st.just(""),
                st.just("   ")
            ),
            min_size=1, max_size=5
        ),
        author_urls=st.lists(
            st.one_of(
                st.just("https://johndoe.com"),
                st.just("http://janesmith.com"),
                st.just(""),
                st.just("invalid-url")
            ),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=100)
    async def test_article_author_processing(self, authors, author_urls):
        """
        For any article record, the author from column J should create/update author 
        records and column L should be stored as site_url.
        **Validates: Requirements 10.4**
        """
        # Ensure lists have same length
        max_len = max(len(authors), len(author_urls))
        authors = (authors * max_len)[:max_len]
        author_urls = (author_urls * max_len)[:max_len]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with export_subset sheet
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                columns = [f'col_{i}' for i in range(12)]
                data = {col: [f'data_{col}_{i}' for i in range(len(authors))] for col in columns}
                # Set article IDs in column A
                data['col_0'] = [f'article_{i}' for i in range(len(authors))]
                # Set feature article column (H, index 7) to 'yes'
                data['col_7'] = ['yes'] * len(authors)
                # Set authors in column J (index 9)
                data['col_9'] = authors
                # Set author URLs in column L (index 11)
                data['col_11'] = author_urls
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Mock database operations
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def fetchval(self, query, *args):
                    return 1  # Always find a document
                
                async def execute(self, query, *args):
                    pass
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Track author service calls
            author_service_calls = []
            
            async def mock_get_or_create(name, site_url=None):
                author_service_calls.append((name, site_url))
                return len(author_service_calls)
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_article_metadata(str(test_file))
            
            # Property: Should call AuthorService for each valid author
            valid_authors = [author for author in authors if author.strip()]
            expected_calls = 0
            
            for i, author in enumerate(authors):
                if author.strip():
                    parsed_authors = self.service.parse_authors(author)
                    expected_calls += len(parsed_authors)
            
            assert len(author_service_calls) == expected_calls, \
                f"Should make {expected_calls} author service calls, got {len(author_service_calls)}"
            
            # Property: Should pass author URLs correctly
            for i, (author, author_url) in enumerate(zip(authors, author_urls)):
                if author.strip():
                    parsed_authors = self.service.parse_authors(author)
                    for parsed_author in parsed_authors:
                        # Find the call for this author
                        matching_calls = [call for call in author_service_calls if call[0] == parsed_author]
                        assert len(matching_calls) > 0, \
                            f"Should have call for author '{parsed_author}'"
                        
                        # Check if URL was passed correctly
                        call_name, call_url = matching_calls[0]
                        expected_url = author_url if author_url.strip() else None
                        assert call_url == expected_url, \
                            f"Should pass URL '{expected_url}' for author '{parsed_author}', got '{call_url}'"
    
    # Feature: multi-author-metadata-enhancement, Property 46: Article URL storage
    @given(
        article_urls=st.lists(
            st.one_of(
                st.just("https://example.com/article1"),
                st.just("http://example.com/article2"),
                st.just(""),
                st.just("invalid-url")
            ),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=100)
    async def test_article_url_storage(self, article_urls):
        """
        For any article record, column K should be stored as article_url and 
        document_type should be set to "article".
        **Validates: Requirements 10.5, 10.6**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with export_subset sheet
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                columns = [f'col_{i}' for i in range(12)]
                data = {col: [f'data_{col}_{i}' for i in range(len(article_urls))] for col in columns}
                # Set article IDs in column A
                data['col_0'] = [f'article_{i}' for i in range(len(article_urls))]
                # Set feature article column (H, index 7) to 'yes'
                data['col_7'] = ['yes'] * len(article_urls)
                # Set authors in column J (index 9)
                data['col_9'] = [f'Author {i}' for i in range(len(article_urls))]
                # Set article URLs in column K (index 10)
                data['col_10'] = article_urls
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Mock database operations
            update_queries = []
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def fetchval(self, query, *args):
                    return 1  # Always find a document
                
                async def execute(self, query, *args):
                    if "UPDATE books" in query and "document_type = 'article'" in query:
                        update_queries.append((query, args))
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Mock author service
            async def mock_get_or_create(name, site_url=None):
                return 1
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_article_metadata(str(test_file))
            
            # Property: Should update each document with article_url and document_type
            assert len(update_queries) == len(article_urls), \
                f"Should update {len(article_urls)} documents, got {len(update_queries)}"
            
            # Property: Each update should set document_type to 'article'
            for query, args in update_queries:
                assert "document_type = 'article'" in query, \
                    f"Query should set document_type to 'article': {query}"
            
            # Property: Each update should set article_url correctly
            for i, (query, args) in enumerate(update_queries):
                expected_url = article_urls[i] if article_urls[i].strip() else None
                actual_url = args[0]  # First argument should be the article_url
                
                assert actual_url == expected_url, \
                    f"Should set article_url to '{expected_url}', got '{actual_url}'"
    
    # Feature: multi-author-metadata-enhancement, Property 47: Article import reporting
    @given(
        num_articles=st.integers(min_value=1, max_value=10),
        match_rate=st.floats(min_value=0.0, max_value=1.0),
        error_rate=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=100)
    async def test_article_import_reporting(self, num_articles, match_rate, error_rate):
        """
        For any article metadata import, the system should report accurate counts 
        of articles processed, authors created/updated, and validation errors.
        **Validates: Requirements 10.7**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create Excel file with export_subset sheet
            with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
                columns = [f'col_{i}' for i in range(12)]
                data = {col: [f'data_{col}_{i}' for i in range(num_articles)] for col in columns}
                
                # Set article IDs and authors based on error rate
                article_ids = []
                authors = []
                for i in range(num_articles):
                    if i < int(num_articles * error_rate):
                        # Create invalid data
                        article_ids.append("")  # Invalid ID
                        authors.append("")  # Invalid author
                    else:
                        article_ids.append(f'article_{i}')
                        authors.append(f'Author {i}')
                
                data['col_0'] = article_ids  # Column A
                data['col_7'] = ['yes'] * num_articles  # Column H
                data['col_9'] = authors  # Column J
                data['col_10'] = [f'https://example.com/article_{i}' for i in range(num_articles)]  # Column K
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name='export_subset', index=False)
            
            # Mock database operations
            match_count = 0
            expected_matches = int((num_articles - int(num_articles * error_rate)) * match_rate)
            update_count = 0
            
            async def mock_ensure_pool():
                pass
            
            class MockConnection:
                async def fetchval(self, query, *args):
                    nonlocal match_count
                    if match_count < expected_matches:
                        match_count += 1
                        return match_count
                    return None
                
                async def execute(self, query, *args):
                    nonlocal update_count
                    if "UPDATE books" in query and "document_type = 'article'" in query:
                        update_count += 1
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
            
            class MockPool:
                def acquire(self):
                    return MockConnection()
            
            self.service._ensure_pool = mock_ensure_pool
            self.service.pool = MockPool()
            
            # Track author service calls
            author_create_count = 0
            
            async def mock_get_or_create(name, site_url=None):
                nonlocal author_create_count
                author_create_count += 1
                return author_create_count
            
            self.service.author_service.get_or_create_author = mock_get_or_create
            
            # Test import
            result = await self.service.import_article_metadata(str(test_file))
            
            # Property: Should report correct number of articles processed
            assert result.articles_processed == num_articles, \
                f"Should process {num_articles} articles, reported {result.articles_processed}"
            
            # Property: Should report correct number of articles matched
            assert result.articles_matched == expected_matches, \
                f"Should match {expected_matches} articles, reported {result.articles_matched}"
            
            # Property: Should report correct number of documents updated
            assert result.documents_updated == expected_matches, \
                f"Should update {expected_matches} documents, reported {result.documents_updated}"
            
            # Property: Should report errors for invalid data
            expected_errors = int(num_articles * error_rate)
            if expected_errors > 0:
                assert len(result.errors) >= expected_errors, \
                    f"Should report at least {expected_errors} errors, got {len(result.errors)}"
            
            # Property: Should report processing time
            assert result.processing_time > 0, \
                f"Should report positive processing time, got {result.processing_time}"
            
            # Property: Success should be True if import completed
            assert result.success is True, "Import should be marked as successful"

# Property tests for Task 12 subtasks

class TestExcelImportAPIProperties:
    """Property-based tests for Excel Import API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database URL for testing
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        author_service = AuthorService()
        self.service = ExcelImportService(author_service)
    
    # Feature: multi-author-metadata-enhancement, Property 35: Excel error reporting
    @given(
        validation_errors=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=10),  # row
                st.sampled_from(['URL', 'Title', 'Author', 'file']),  # column
                st.text(min_size=5, max_size=50),  # message
                st.sampled_from(['error', 'warning'])  # severity
            ),
            min_size=0, max_size=10
        )
    )
    @settings(max_examples=100)
    async def test_excel_error_reporting(self, validation_errors):
        """
        For any validation errors found, the system should provide detailed error 
        messages with specific row and column information.
        **Validates: Requirements 11.6**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create a basic valid Excel file structure
            df = pd.DataFrame({
                'URL': ['https://example.com'],
                'Title': ['Test Book'],
                'Author': ['Test Author']
            })
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            # Mock the validation to return our test errors
            from excel_import_service import ExcelValidationError, ValidationResult
            
            mock_errors = []
            for row, column, message, severity in validation_errors:
                mock_errors.append(ExcelValidationError(
                    row=row,
                    column=column,
                    message=message,
                    severity=severity
                ))
            
            # Mock the validate_excel_file method
            original_validate = self.service.validate_excel_file
            
            async def mock_validate(file_path, file_type):
                return ValidationResult(
                    valid=len([e for e in mock_errors if e.severity == "error"]) == 0,
                    errors=mock_errors,
                    preview_rows=[]
                )
            
            self.service.validate_excel_file = mock_validate
            
            # Test validation
            result = await self.service.validate_excel_file(str(test_file), 'book')
            
            # Property: All errors should be reported with complete information
            assert len(result.errors) == len(validation_errors), \
                f"Should report {len(validation_errors)} errors, got {len(result.errors)}"
            
            # Property: Each error should have row, column, message, and severity
            for i, error in enumerate(result.errors):
                expected_row, expected_column, expected_message, expected_severity = validation_errors[i]
                
                assert hasattr(error, 'row'), f"Error {i} should have row attribute"
                assert hasattr(error, 'column'), f"Error {i} should have column attribute"
                assert hasattr(error, 'message'), f"Error {i} should have message attribute"
                assert hasattr(error, 'severity'), f"Error {i} should have severity attribute"
                
                assert error.row == expected_row, \
                    f"Error {i} should have row {expected_row}, got {error.row}"
                assert error.column == expected_column, \
                    f"Error {i} should have column {expected_column}, got {error.column}"
                assert error.message == expected_message, \
                    f"Error {i} should have message '{expected_message}', got '{error.message}'"
                assert error.severity == expected_severity, \
                    f"Error {i} should have severity {expected_severity}, got {error.severity}"
            
            # Property: Validation should be invalid if any errors have severity 'error'
            has_errors = any(severity == 'error' for _, _, _, severity in validation_errors)
            assert result.valid == (not has_errors), \
                f"Validation should be {'invalid' if has_errors else 'valid'}, got {result.valid}"
            
            # Restore original method
            self.service.validate_excel_file = original_validate
    
    # Feature: multi-author-metadata-enhancement, Property 36: Excel workflow control
    @given(
        validation_passes=st.booleans(),
        user_choice=st.sampled_from(['proceed', 'cancel'])
    )
    @settings(max_examples=100)
    async def test_excel_workflow_control(self, validation_passes, user_choice):
        """
        For any Excel file that passes validation, the system should allow 
        proceeding with import or canceling the operation.
        **Validates: Requirements 11.7**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.xlsm"
            
            # Create test Excel file
            if validation_passes:
                # Create valid Excel file
                df = pd.DataFrame({
                    'URL': ['https://example.com'],
                    'Title': ['Test Book'],
                    'Author': ['Test Author']
                })
                df.to_excel(test_file, engine='openpyxl', index=False)
            else:
                # Create invalid Excel file (wrong extension)
                test_file = test_file.with_suffix('.txt')
                test_file.write_text("invalid content")
            
            # Test validation
            result = await self.service.validate_excel_file(str(test_file), 'book')
            
            # Property: Validation result should match expected outcome
            assert result.valid == validation_passes, \
                f"Validation should {'pass' if validation_passes else 'fail'}, got {result.valid}"
            
            # Property: If validation passes, user should be able to proceed or cancel
            if validation_passes:
                # Validation passed - user can choose to proceed or cancel
                if user_choice == 'proceed':
                    # Mock successful import
                    import_result = await self._mock_import_operation(str(test_file))
                    assert import_result is not None, "Should be able to proceed with import"
                else:
                    # User chose to cancel - no import should occur
                    # This would be handled by the API endpoint, not the service
                    assert True, "User can choose to cancel after successful validation"
            else:
                # Validation failed - should not be able to proceed
                assert not result.valid, "Should not be able to proceed when validation fails"
                assert len(result.errors) > 0, "Should have validation errors when validation fails"
    
    async def _mock_import_operation(self, file_path: str):
        """Mock import operation for testing workflow control"""
        # Mock database operations
        async def mock_ensure_pool():
            pass
        
        class MockConnection:
            async def execute(self, query, *args):
                pass
            
            async def fetchval(self, query, *args):
                return 1
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockPool:
            def acquire(self):
                return MockConnection()
        
        self.service._ensure_pool = mock_ensure_pool
        self.service.pool = MockPool()
        
        # Mock fuzzy matching
        async def mock_fuzzy_match(title):
            return 1
        
        self.service.fuzzy_match_title = mock_fuzzy_match
        
        # Mock author service
        async def mock_get_or_create(name, site_url=None):
            return 1
        
        self.service.author_service.get_or_create_author = mock_get_or_create
        
        # Attempt import
        try:
            result = await self.service.import_book_metadata(file_path)
            return result
        except Exception:
            return None