#!/usr/bin/env python3
"""
Test URL normalization via Railway API
This creates a test CSV file and validates it through the API to verify URL normalization
"""

import requests
import csv
import tempfile
import os

def create_test_csv_with_bad_urls():
    """Create a test CSV file with URLs that need normalization"""
    
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
    
    # Write CSV with URLs that need fixing
    writer = csv.writer(temp_file)
    writer.writerow(['URL', 'Title', 'Author'])  # Header
    writer.writerow(['http://ww.mcpressonline.com/book1', 'Test Book 1', 'Test Author 1'])
    writer.writerow(['https://ww.mcpressonline.com/book2', 'Test Book 2', 'Test Author 2'])
    writer.writerow(['http://www.mcpressonline.com/book3', 'Test Book 3', 'Test Author 3'])  # Already correct
    
    temp_file.close()
    return temp_file.name

def test_url_normalization_via_api():
    """Test URL normalization through the Railway API"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("Creating test CSV file with URLs that need normalization...")
    csv_file_path = create_test_csv_with_bad_urls()
    
    try:
        print(f"Testing URL normalization via API at {api_url}")
        
        # Test the validation endpoint
        with open(csv_file_path, 'rb') as f:
            files = {'file': ('test-books.csv', f, 'text/csv')}
            data = {'file_type': 'book'}
            
            response = requests.post(
                f"{api_url}/api/excel/validate",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API call successful")
            
            # Check if URLs were normalized in the preview
            if 'preview_rows' in result:
                print("\nChecking URL normalization in preview:")
                all_normalized = True
                
                for i, row in enumerate(result['preview_rows'], 1):
                    if 'data' in row and 'URL' in row['data']:
                        url = row['data']['URL']
                        print(f"Row {i}: {url}")
                        
                        # Check if ww.mcpressonline.com was fixed to www.mcpressonline.com
                        if 'ww.mcpressonline.com' in url:
                            print(f"  ❌ URL not normalized: {url}")
                            all_normalized = False
                        elif 'www.mcpressonline.com' in url:
                            print(f"  ✓ URL properly normalized: {url}")
                
                if all_normalized:
                    print("\n🎉 All URLs were properly normalized!")
                    print("The Excel import service is correctly fixing 'ww.mcpressonline.com' to 'www.mcpressonline.com'")
                    return True
                else:
                    print("\n❌ Some URLs were not normalized properly")
                    return False
            else:
                print("❌ No preview_rows in response")
                return False
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False
    finally:
        # Clean up temp file
        try:
            os.unlink(csv_file_path)
        except:
            pass

if __name__ == "__main__":
    success = test_url_normalization_via_api()
    if success:
        print("\n✅ Task 2 verification complete: URL normalization is working in the deployed service!")
    else:
        print("\n❌ Task 2 verification failed!")