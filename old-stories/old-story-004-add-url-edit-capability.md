# Story: Add MC Press URL Edit Capability

## Story
**ID**: STORY-004  
**Title**: Add MC Press URL Edit Capability  
**Status**: Completed

As a content manager, I want to be able to add and edit MC Press website URLs for books through the UI so that I can maintain accurate links to the MC Press store without needing backend access.

## Acceptance Criteria
- [x] The document edit dialog includes a field for MC Press URL
- [x] Users can add a URL to books that don't have one
- [x] Users can edit/update existing URLs
- [x] URL field validates input is a proper URL format
- [x] Save button updates the book's URL in the database
- [x] Success/error feedback is shown after save
- [x] The URL field is clearly labeled and has helpful placeholder text

## Dev Notes
- Depends on STORY-003 being completed first (database column)
- Need to update MetadataEditDialog.tsx component
- Must handle the new mc_press_url field in the update API call
- Consider adding URL format validation on frontend

## Testing
- Test adding URL to a book without one
- Test editing an existing URL
- Test with invalid URL formats
- Test clearing a URL (making it empty)
- Verify changes persist after page reload
- Test error handling for failed saves

## Tasks  
- [x] Update MetadataEditDialog.tsx component
  - [x] Add URL input field to the form
  - [x] Add proper label and placeholder text
  - [x] Position field logically in the form layout
- [x] Add URL validation
  - [x] Create URL validation function
  - [x] Show validation errors inline
  - [x] Prevent save with invalid URL
- [x] Update the save handler
  - [x] Include mc_press_url in the update request payload
  - [x] Handle the new field in the API call
- [x] Enhance the UpdateMetadataRequest type
  - [x] Add mc_press_url to the request interface
  - [x] Update any TypeScript types
- [x] Add proper error handling
  - [x] Show error messages for failed saves
  - [x] Handle network errors gracefully
- [x] Add success feedback
  - [x] Show success message on save
  - [x] Update local state to reflect changes
- [x] Style the new field
  - [x] Match existing form field styles
  - [x] Ensure responsive design
  - [x] Add appropriate spacing
- [x] Update any relevant help text or documentation

---

## Dev Agent Record

### Agent
Model: Claude

### Debug Log References
- Updated MetadataEditDialog.tsx interface to include currentUrl prop
- Added mc_press_url state management and validation in dialog component
- Updated DocumentList.tsx interface to include mc_press_url field
- Modified MetadataEditDialog usage in DocumentList to pass URL parameter

### Completion Notes
- **UI Integration**: Added URL input field to MetadataEditDialog with proper styling and positioning
- **URL Validation**: Implemented client-side URL validation using JavaScript URL constructor
- **Error Handling**: Added validation error messages for invalid URL formats
- **API Integration**: Updated API call to include mc_press_url in metadata update request
- **Type Safety**: Updated TypeScript interfaces to support optional URL field
- **User Experience**: Added helpful placeholder text and optional field indication
- **Backend Compatibility**: Full integration with STORY-003 database schema changes

### File List
- frontend/components/MetadataEditDialog.tsx (modified - added URL field and validation)
- frontend/components/DocumentList.tsx (modified - updated interface and prop passing)

### Change Log
- [Date] - Story created
- 2025-01-28 - Implemented URL editing capability in metadata dialog with validation

---