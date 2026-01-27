# Manual Testing Guide: Multi-Author Button Display

## Overview
This guide provides steps to manually test the multi-author button behavior in the CompactSources component after the fix has been deployed.

## Prerequisites
- Frontend changes deployed to Netlify
- Access to the production chatbot at https://mcpress-chatbot-production.up.railway.app
- At least one book in the database with 2+ authors having website URLs

## Test Setup

### Option 1: Add Test Data via API

Run this script to add a test book with multiple authors having websites:

```python
import requests

API_URL = "https://mcpress-chatbot-production.up.railway.app"

# Create test authors
authors_data = [
    {"name": "John Doe", "site_url": "https://johndoe.com"},
    {"name": "Jane Smith", "site_url": "https://janesmith.com"}
]

# Create a test book (you'll need admin access)
# This is just an example - actual implementation depends on your API
```

### Option 2: Update Existing Book

If you have books with multiple authors but no websites, add website URLs:

```bash
# Use the author update endpoint
curl -X PATCH "https://mcpress-chatbot-production.up.railway.app/api/authors/1" \
  -H "Content-Type: application/json" \
  -d '{"site_url": "https://example.com"}'
```

## Test Cases

### Test Case 1: Single Author with Website
**Expected:** Button shows "Author" (singular) as a direct link

1. Find a book with only one author who has a website
2. Ask a question that returns this book as a source
3. Verify the button shows "Author" (not "Authors")
4. Verify clicking the button opens the author's website directly
5. Verify no dropdown appears

**Example Query:** "Tell me about [book title]"

### Test Case 2: Multiple Authors, Only One with Website
**Expected:** Button shows "Author" (singular) as a direct link

1. Find a book with multiple authors where only one has a website
2. Ask a question that returns this book as a source
3. Verify the button shows "Author" (singular)
4. Verify clicking opens the one author's website
5. Verify no dropdown appears

### Test Case 3: Multiple Authors with Websites ⭐ PRIMARY TEST
**Expected:** Button shows "Authors" (plural) with dropdown

1. Find a book with 2+ authors who all have websites
2. Ask a question that returns this book as a source
3. **Verify the button shows "Authors" (PLURAL)**
4. **Verify hovering over the button shows a dropdown**
5. **Verify the dropdown lists all authors with their websites**
6. Verify clicking an author in the dropdown opens their website
7. Verify the dropdown stays open while hovering over it

**Example Query:** "Tell me about [multi-author book title]"

### Test Case 4: Multiple Authors, None with Websites
**Expected:** No author button shown

1. Find a book with multiple authors but no websites
2. Ask a question that returns this book as a source
3. Verify no "Author" or "Authors" button appears
4. Verify author names still appear in the text (e.g., "by John Doe, Jane Smith")

### Test Case 5: Three or More Authors with Websites
**Expected:** Button shows "Authors" (plural) with dropdown listing all

1. Find a book with 3+ authors who have websites
2. Ask a question that returns this book as a source
3. Verify the button shows "Authors" (plural)
4. Verify the dropdown shows all authors
5. Verify all author links work correctly

## Visual Verification Checklist

For the multi-author dropdown (Test Case 3):

- [ ] Button text is "Authors" (plural, not "Author")
- [ ] Button has purple background (bg-purple-600)
- [ ] Button changes to darker purple on hover (hover:bg-purple-700)
- [ ] Dropdown appears on hover
- [ ] Dropdown has white background with border
- [ ] Dropdown has shadow for depth
- [ ] Each author entry shows:
  - [ ] Author name in bold
  - [ ] Website URL below name
  - [ ] Hover effect (gray background)
- [ ] Clicking an author opens their website in new tab
- [ ] Dropdown stays open while hovering over it
- [ ] Dropdown closes when mouse moves away

## Known Issues to Watch For

### Bug Symptoms (Should NOT occur after fix):
- ❌ Button shows "Author" (singular) when multiple authors have websites
- ❌ Button links directly to first author instead of showing dropdown
- ❌ Dropdown doesn't appear on hover
- ❌ Dropdown disappears immediately when trying to hover over it

### Expected Behavior (Should occur after fix):
- ✅ Button shows "Authors" (plural) when 2+ authors have websites
- ✅ Dropdown appears and stays open on hover
- ✅ All authors with websites are listed in dropdown
- ✅ Each author link works correctly

## Debugging

If the button behavior is incorrect:

1. **Check browser console** for JavaScript errors
2. **Inspect the source data** in browser DevTools:
   - Open Network tab
   - Find the chat response
   - Look for the `sources` array in the response
   - Verify each source has an `authors` array
   - Verify authors have `site_url` fields

3. **Check the component rendering**:
   - Right-click the button and "Inspect Element"
   - Verify the button text
   - Check if dropdown div exists in DOM
   - Verify CSS classes are applied correctly

4. **Test with different books**:
   - Try books with different author counts
   - Verify the logic works for 2, 3, 4+ authors

## Reporting Issues

If you find issues, report with:
- Book title that exhibits the problem
- Number of authors and how many have websites
- Screenshot of the button/dropdown
- Browser console errors (if any)
- Expected vs actual behavior

## Success Criteria

The fix is successful when:
1. ✅ Single author with website → "Author" button (direct link)
2. ✅ Multiple authors, one with website → "Author" button (direct link)
3. ✅ Multiple authors with websites → "Authors" button (dropdown)
4. ✅ Dropdown shows all authors with websites
5. ✅ Dropdown is usable (doesn't disappear on hover)
6. ✅ All author links work correctly
