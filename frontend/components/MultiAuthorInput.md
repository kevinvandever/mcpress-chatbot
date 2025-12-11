# MultiAuthorInput Component

A comprehensive React component for managing multiple authors in the MC Press document management system. This component provides a complete author management interface with search, autocomplete, drag-and-drop reordering, and inline URL editing.

## Features

- **Author Search & Autocomplete**: Integrates with `/api/authors/search` endpoint
- **Add New Authors**: Create new authors inline when they don't exist in the system
- **Drag & Drop Reordering**: HTML5 drag-and-drop support for author reordering
- **Inline URL Editing**: Click-to-edit functionality for author website URLs
- **Last Author Protection**: Prevents removal of the last author (documents must have ≥1 author)
- **MC Press Styling**: Uses official MC Press design tokens and color scheme
- **Keyboard Navigation**: Full keyboard accessibility with arrow keys and Enter/Escape
- **URL Validation**: Validates URLs must start with http:// or https://

## Usage

```tsx
import MultiAuthorInput from './MultiAuthorInput'

function DocumentEditForm() {
  const [authors, setAuthors] = useState([
    {
      id: 1,
      name: 'John Doe',
      site_url: 'https://johndoe.com',
      order: 0
    }
  ])

  return (
    <MultiAuthorInput
      authors={authors}
      onChange={setAuthors}
      placeholder="Search for authors..."
      maxAuthors={10}
      disabled={false}
    />
  )
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `authors` | `Author[]` | Required | Array of current authors |
| `onChange` | `(authors: Author[]) => void` | Required | Callback when authors change |
| `disabled` | `boolean` | `false` | Disable all interactions |
| `className` | `string` | `''` | Additional CSS classes |
| `placeholder` | `string` | `'Search for authors...'` | Search input placeholder |
| `maxAuthors` | `number` | `10` | Maximum number of authors allowed |

## Author Type

```tsx
interface Author {
  id?: number        // Optional - undefined for new authors
  name: string       // Author's full name
  site_url?: string  // Optional website URL
  order: number      // Display order (0-based)
}
```

## API Integration

The component integrates with the following backend endpoints:

- `GET /api/authors/search?q={query}&limit={limit}` - Search existing authors
- Returns authors with `id`, `name`, `site_url`, and `document_count`

## Keyboard Shortcuts

- **Arrow Down/Up**: Navigate search results
- **Enter**: Select highlighted result or add new author
- **Escape**: Close search dropdown
- **Tab**: Navigate between UI elements

## Drag & Drop

Authors can be reordered using:
1. **Drag handles**: Drag the grip icon on the left of each author
2. **Arrow buttons**: Use up/down arrow buttons
3. **Keyboard**: Focus and use arrow keys (when implemented)

## URL Editing

Author website URLs can be edited inline:
1. Click the edit icon next to the URL
2. Modify the URL in the input field
3. Click save (✓) or press Enter to confirm
4. Click cancel (✗) or press Escape to abort

URLs are validated to ensure they start with `http://` or `https://`.

## Validation Rules

- **Minimum Authors**: Documents must have at least 1 author
- **Maximum Authors**: Configurable via `maxAuthors` prop (default: 10)
- **URL Format**: Must be valid HTTP/HTTPS URLs or empty
- **Duplicate Prevention**: Cannot add the same author twice

## Styling

The component uses MC Press design tokens:
- `--mc-blue` for primary actions and focus states
- `--mc-orange` for CTA elements
- `--mc-green` for success states
- `--mc-red` for danger/error states
- `--mc-gray` for neutral elements

## Accessibility

- Full keyboard navigation support
- ARIA attributes for screen readers
- Focus management for modal interactions
- High contrast mode support
- Reduced motion support

## Requirements Validation

This component validates the following requirements:
- **5.1**: Display authors with add/remove capability
- **5.2**: Provide autocomplete suggestions
- **5.3**: Create new author records
- **5.4**: Reuse existing author records
- **5.5**: Allow inline editing of author details
- **5.7**: Prevent removal of last author

## Testing

The component includes comprehensive tests covering:
- Rendering and display
- Search functionality
- Adding/removing authors
- Drag & drop reordering
- URL editing and validation
- Keyboard navigation
- Accessibility features

Run tests with:
```bash
npm test MultiAuthorInput.test.tsx
```

## Example Integration

See `MultiAuthorInput.example.tsx` for complete usage examples including:
- Basic component usage
- Form integration
- Document type handling
- Error handling patterns