# AI Frontend Generation Prompts for PDF Chatbot Application

## Overview
This document contains comprehensive prompts for generating frontend components for a multi-modal PDF chatbot application. Each prompt includes detailed specifications for component structure, styling, interactions, and API integration.

## Project Context
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript with React 18
- **Styling**: Tailwind CSS
- **Backend**: FastAPI at http://localhost:8001
- **Features**: Multi-modal PDF processing, real-time streaming chat, semantic search, document management

---

## 1. Main Dashboard Layout Prompt

### Prompt for AI Code Generation:

```
Create a responsive main dashboard layout for a PDF chatbot application using Next.js 14 with App Router, React 18, and TypeScript. The layout should include:

**Layout Structure:**
- Fixed sidebar (320px width on desktop, collapsible on mobile)
- Main content area with flexible width
- Header with application title and status indicators
- Clean, modern design with excellent UX

**Sidebar Components:**
- File upload area at the top
- Document list in the middle
- Future space for search interface
- Clean dividers between sections

**Main Content Area:**
- Chat interface taking full height
- Responsive design for mobile/tablet/desktop
- Smooth transitions and animations

**Technical Requirements:**
- TypeScript interfaces for all props and state
- Tailwind CSS for styling with design system colors:
  - Primary: blue-600/blue-700
  - Secondary: gray-50/gray-100/gray-200
  - Accent: green-600 for success
  - Error: red-600/red-700
- Responsive breakpoints:
  - Mobile: < 768px (single column, collapsible sidebar)
  - Tablet: 768px - 1024px (adaptive sidebar)
  - Desktop: > 1024px (full sidebar visibility)

**Accessibility:**
- WCAG 2.1 AA compliance
- ARIA labels and semantic HTML
- Keyboard navigation support
- Focus management
- Screen reader compatibility

**State Management:**
- React hooks for component state
- Props for parent-child communication
- State for sidebar visibility on mobile
- Loading states and error handling

**Performance:**
- Lazy loading for heavy components
- Optimized re-renders
- Efficient scroll handling
- Code splitting where appropriate

**Example Structure:**
```tsx
interface DashboardProps {
  children: React.ReactNode;
}

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}
```

Include proper TypeScript types, responsive design patterns, and accessibility features. Use Inter font family and maintain consistent spacing (1rem standard, 0.5rem compact).
```

---

## 2. Chat Interface with Streaming Responses Prompt

### Prompt for AI Code Generation:

```
Create a real-time streaming chat interface component for a PDF chatbot using React 18, TypeScript, and Tailwind CSS. The component should handle Server-Sent Events for streaming responses.

**Core Features:**
- Real-time message streaming with incremental text building
- Markdown rendering with syntax highlighting for code blocks
- Source citations display after each AI response
- Auto-scroll to latest message with smooth behavior
- Typing indicators during streaming
- Message history preservation
- Error handling with graceful degradation

**Technical Implementation:**
- Fetch API with ReadableStream for SSE
- ReactMarkdown with remark-gfm for GitHub Flavored Markdown
- Custom code block styling with syntax highlighting
- Proper TypeScript interfaces for all data structures

**API Integration:**
- Endpoint: POST http://localhost:8001/chat
- Payload: { message: string, conversation_id?: string }
- Response: Server-Sent Events with data chunks
- Event types: 'content' (partial response), 'done' (with sources)

**UI Components:**
- Message bubbles with role-based styling:
  - User: blue-600 background, white text, right-aligned
  - Assistant: gray-100 background, gray-800 text, left-aligned
- Code blocks: dark theme (gray-800 bg, gray-100 text)
- Source citations: small cards with filename and page info
- Typing indicator: three animated dots
- Input area: full-width with send button

**State Management:**
```tsx
interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{
    filename: string;
    page: string | number;
    relevance_score?: number;
  }>;
}

interface ChatState {
  messages: Message[];
  input: string;
  isStreaming: boolean;
  error: string | null;
}
```

**Responsive Design:**
- Mobile: Simplified layout, touch-optimized controls
- Tablet: Optimized chat bubbles, enhanced touch targets
- Desktop: Full layout with hover interactions, keyboard shortcuts

**Accessibility Features:**
- ARIA labels for all interactive elements
- Keyboard navigation (Enter to send, Escape to cancel)
- Screen reader announcements for new messages
- Focus management for input field
- Alt text for any icons or images

**Performance Optimizations:**
- Debounced input handling
- Efficient re-renders with React.memo where appropriate
- Virtualized message list for large conversations (future)
- Proper cleanup of event listeners and streams

**Error Handling:**
- Network error recovery
- Malformed SSE data handling
- Loading states and error messages
- Retry mechanism for failed requests

**Styling Requirements:**
- Tailwind CSS with consistent design system
- Smooth animations and transitions
- Proper contrast ratios for accessibility
- Mobile-first responsive design
- Custom scrollbar styling

Include proper cleanup in useEffect, error boundaries, and comprehensive TypeScript types. The component should be production-ready with excellent UX.
```

---

## 3. File Upload with Progress Tracking Prompt

### Prompt for AI Code Generation:

```
Create a comprehensive file upload component with drag-and-drop functionality and progress tracking for PDF files. Built with React 18, TypeScript, react-dropzone, and Tailwind CSS.

**Core Features:**
- Drag and drop PDF file support
- Click to select files alternative
- Real-time upload progress indication
- File validation (PDF only, max 50MB)
- Visual feedback for drag states
- Error handling with user-friendly messages
- Success callbacks for parent component integration

**Technical Implementation:**
- react-dropzone for drag-and-drop functionality
- Axios for file uploads with progress tracking
- FormData for multipart file uploads
- TypeScript interfaces for all props and state
- Proper error handling and user feedback

**API Integration:**
- Endpoint: POST http://localhost:8001/upload
- Content-Type: multipart/form-data
- Max file size: 50MB
- Supported formats: PDF only
- Response: { status: 'success', chunks_created: number, images_processed: number, code_blocks_found: number, total_pages: number }

**UI States:**
- Default: Gray dashed border, hover effects
- Drag Active: Blue border, blue background tint
- Uploading: Progress bar, disabled state, loading indicator
- Success: Green checkmark, success message
- Error: Red border, error message display

**Component Interface:**
```tsx
interface FileUploadProps {
  onUploadSuccess: (filename: string, metadata: UploadMetadata) => void;
  onUploadError?: (error: string) => void;
  disabled?: boolean;
  maxSize?: number;
}

interface UploadMetadata {
  chunks_created: number;
  images_processed: number;
  code_blocks_found: number;
  total_pages: number;
}

interface UploadState {
  uploading: boolean;
  progress: number;
  error: string | null;
  dragActive: boolean;
}
```

**Styling Requirements:**
- Tailwind CSS with design system colors
- Responsive design for all screen sizes
- Smooth transitions and hover effects
- Accessibility-compliant contrast ratios
- Mobile-optimized touch targets

**Progress Tracking:**
- Visual progress bar during upload
- Percentage display
- Estimated time remaining (if available)
- Cancel upload functionality
- Speed indicators

**File Validation:**
- PDF mime type checking
- File size validation (50MB max)
- Extension validation (.pdf)
- Multiple file handling (single file only)
- Clear error messages for each validation failure

**Accessibility Features:**
- ARIA labels for all interactive elements
- Keyboard navigation support
- Screen reader compatibility
- Focus management
- Alternative text for visual indicators

**Error Handling:**
- Network errors with retry options
- File validation errors
- Server errors with user-friendly messages
- Upload timeout handling
- Graceful degradation for older browsers

**Mobile Considerations:**
- Touch-friendly interface
- Optimized for mobile file selection
- Responsive layout adjustments
- Performance optimization for mobile devices

**Visual Design:**
- Clean, modern interface
- Clear visual hierarchy
- Consistent with overall app design
- Smooth animations and micro-interactions
- Professional appearance

Include proper TypeScript types, comprehensive error handling, and follow React best practices. The component should integrate seamlessly with the parent dashboard component.
```

---

## 4. Search Interface with Filtering Prompt

### Prompt for AI Code Generation:

```
Create a comprehensive search interface component with content type filtering for semantic search across PDF documents. Built with React 18, TypeScript, and Tailwind CSS.

**Core Features:**
- Real-time search with debounced input
- Advanced filtering options (content type, document, relevance)
- Search history with recent queries
- Pagination for large result sets
- Result highlighting and relevance scoring
- Auto-complete suggestions
- Search analytics and insights

**Technical Implementation:**
- Debounced search queries (300ms delay)
- REST API integration with proper error handling
- TypeScript interfaces for all data structures
- Efficient result caching and state management
- Keyboard shortcuts for power users

**API Integration:**
- Endpoint: GET http://localhost:8001/search
- Parameters: { q: string, n_results?: number, content_type?: string, document?: string }
- Response: { query: string, results: SearchResult[], total_count: number }

**Search Result Interface:**
```tsx
interface SearchResult {
  id: string;
  content: string;
  filename: string;
  page: number | string;
  relevance_score: number;
  content_type: 'text' | 'code' | 'image';
  context_before?: string;
  context_after?: string;
  highlights?: string[];
}

interface SearchState {
  query: string;
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  filters: SearchFilters;
  pagination: PaginationState;
  searchHistory: string[];
}

interface SearchFilters {
  content_type: 'all' | 'text' | 'code' | 'image';
  document: string | 'all';
  min_relevance: number;
  date_range?: { start: Date; end: Date };
}
```

**UI Components:**
- Search input with autocomplete dropdown
- Filter panel with content type toggles
- Result cards with highlighting
- Pagination controls
- Search history sidebar
- Loading states and error messages

**Filter Options:**
- Content Type: All, Text, Code, Images
- Document: All documents or specific PDF
- Relevance Score: Minimum threshold slider
- Date Range: Upload date filtering (future)
- Page Range: Specific page numbers (future)

**Result Display:**
- Result cards with content preview
- Highlighted matching terms
- Relevance score visualization
- Source document and page info
- Context snippets (before/after)
- Content type badges

**Search Features:**
- Auto-complete with suggestion dropdown
- Search history with recent queries
- Keyboard shortcuts (Ctrl+K to focus, Escape to clear)
- Advanced search operators (quotes, wildcards)
- Search within results functionality

**Responsive Design:**
- Mobile: Simplified filters, touch-optimized controls
- Tablet: Collapsible filter panel, optimized result cards
- Desktop: Full sidebar filters, keyboard navigation

**Performance Optimizations:**
- Debounced input to reduce API calls
- Result caching with TTL
- Virtualized result list for large sets
- Efficient re-renders with React.memo
- Progressive loading for images

**Accessibility Features:**
- ARIA labels for all interactive elements
- Keyboard navigation for all components
- Screen reader compatibility
- Focus management
- High contrast mode support

**Search Analytics:**
- Query tracking and analytics
- Popular searches display
- Search success metrics
- User behavior insights

**Error Handling:**
- Network errors with retry options
- Invalid query handling
- Empty result states
- Search timeout handling
- Graceful degradation

**Styling Requirements:**
- Tailwind CSS with design system
- Smooth animations and transitions
- Consistent with app design language
- Professional search interface
- Mobile-first responsive design

Include proper TypeScript types, comprehensive error handling, and follow React best practices. The component should provide excellent search UX with advanced filtering capabilities.
```

---

## 5. Document Management Cards Prompt

### Prompt for AI Code Generation:

```
Create a comprehensive document management component with rich metadata display and actions. Built with React 18, TypeScript, and Tailwind CSS.

**Core Features:**
- Document cards with rich metadata display
- Content type indicators (text, images, code)
- Document actions (view, delete, download)
- Sorting and filtering options
- Bulk operations support
- Loading states and error handling
- Responsive grid layout

**Technical Implementation:**
- React hooks for state management
- TypeScript interfaces for all data structures
- Axios for API communication
- Optimistic updates for better UX
- Error boundaries for graceful error handling

**API Integration:**
- List: GET http://localhost:8001/documents
- Delete: DELETE http://localhost:8001/documents/{filename}
- Response: { documents: Document[], total_count: number }

**Document Interface:**
```tsx
interface Document {
  filename: string;
  total_chunks: number;
  total_pages: number;
  has_images: boolean;
  has_code: boolean;
  file_size: number;
  upload_date: string;
  last_accessed?: string;
  processing_status: 'completed' | 'processing' | 'failed';
  content_summary?: string;
}

interface DocumentListState {
  documents: Document[];
  loading: boolean;
  error: string | null;
  selectedDocuments: string[];
  sortBy: 'name' | 'date' | 'size' | 'pages';
  sortDirection: 'asc' | 'desc';
  filters: DocumentFilters;
}

interface DocumentFilters {
  content_type: 'all' | 'text' | 'code' | 'image';
  processing_status: 'all' | 'completed' | 'processing' | 'failed';
  date_range?: { start: Date; end: Date };
}
```

**Card Components:**
- Document thumbnail or icon
- Title with truncation
- Metadata badges (pages, chunks, content types)
- Action buttons (view, delete, download)
- Progress indicators for processing
- Context menu for additional actions

**Metadata Display:**
- File size in human-readable format
- Upload date with relative time
- Page count and chunk count
- Content type badges with icons:
  - 📄 Text content
  - 📷 Images detected
  - 💻 Code blocks found
- Processing status indicators

**Document Actions:**
- View document details (modal/sidebar)
- Delete with confirmation dialog
- Download original file
- Share document (future)
- Rename document (future)
- Archive/favorite (future)

**Layout Options:**
- Grid view: Card-based layout
- List view: Table-like compact layout
- Compact view: Minimal information display
- Responsive breakpoints for optimal viewing

**Sorting & Filtering:**
- Sort by: Name, Date, Size, Pages, Relevance
- Filter by: Content type, Processing status, Date range
- Search within documents
- Bulk selection for operations

**Responsive Design:**
- Mobile: Single column, touch-optimized
- Tablet: 2-column grid, collapsible filters
- Desktop: 3-4 column grid, full features

**Loading States:**
- Skeleton cards during initial load
- Individual card loading for operations
- Progress bars for bulk operations
- Shimmer effects for smooth UX

**Error Handling:**
- Network errors with retry options
- Individual document errors
- Bulk operation error handling
- Graceful degradation for missing data

**Accessibility Features:**
- ARIA labels for all interactive elements
- Keyboard navigation support
- Screen reader compatibility
- Focus management
- High contrast mode support

**Performance Optimizations:**
- Virtualized scrolling for large lists
- Lazy loading for document thumbnails
- Efficient re-renders with React.memo
- Debounced search and filter operations

**Bulk Operations:**
- Multi-select with checkboxes
- Bulk delete with confirmation
- Bulk download as ZIP
- Bulk tag management (future)
- Select all/none functionality

**Visual Design:**
- Clean, modern card design
- Consistent with app design system
- Smooth hover effects and transitions
- Professional appearance
- Clear visual hierarchy

**Context Menu:**
- Right-click context menu
- Touch-friendly long-press support
- Keyboard shortcut support
- Consistent with OS conventions

Include proper TypeScript types, comprehensive error handling, and follow React best practices. The component should provide excellent document management UX with intuitive interactions.
```

---

## 6. Mobile Responsive Layouts Prompt

### Prompt for AI Code Generation:

```
Create comprehensive mobile-responsive layouts for the PDF chatbot application with adaptive design patterns. Built with React 18, TypeScript, and Tailwind CSS.

**Responsive Strategy:**
- Mobile-first design approach
- Progressive enhancement for larger screens
- Touch-optimized interactions
- Performance optimization for mobile devices
- Consistent UX across all device sizes

**Breakpoint System:**
- Mobile: < 768px (sm)
- Tablet: 768px - 1024px (md/lg)
- Desktop: > 1024px (xl)
- Large Desktop: > 1440px (2xl)

**Mobile Layout Adaptations:**

**1. Dashboard Layout (Mobile):**
- Single column stack layout
- Collapsible sidebar with overlay
- Fixed header with hamburger menu
- Bottom navigation for quick actions
- Swipe gestures for navigation
- Touch-friendly spacing (min 44px targets)

**2. Chat Interface (Mobile):**
- Full-screen chat experience
- Optimized message bubbles for narrow screens
- Sticky input bar at bottom
- Swipe-to-reply functionality (future)
- Voice input support (future)
- Optimized keyboard handling

**3. File Upload (Mobile):**
- Simplified drag-and-drop area
- Camera integration for document scanning
- Touch-optimized file selection
- Mobile-specific progress indicators
- Optimized error messages

**4. Search Interface (Mobile):**
- Expandable search bar
- Slide-up filter panel
- Touch-friendly filter controls
- Swipe-to-dismiss results
- Mobile-optimized pagination

**5. Document Management (Mobile):**
- Single column card layout
- Swipe actions for document operations
- Pull-to-refresh functionality
- Infinite scroll for large lists
- Touch-optimized context menus

**Technical Implementation:**
```tsx
interface ResponsiveLayoutProps {
  children: React.ReactNode;
  variant: 'mobile' | 'tablet' | 'desktop';
}

interface MobileNavigationProps {
  isOpen: boolean;
  onToggle: () => void;
  items: NavigationItem[];
}

interface TouchGestureProps {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onLongPress?: () => void;
  children: React.ReactNode;
}
```

**Adaptive Components:**
- Responsive navigation (hamburger menu on mobile)
- Adaptive sidebars (overlay on mobile, fixed on desktop)
- Touch-optimized buttons and inputs
- Swipe gesture handlers
- Device-specific optimizations

**Performance Optimizations:**
- Lazy loading for off-screen content
- Optimized bundle sizes for mobile
- Efficient scroll handling
- Touch event optimization
- Reduced animations on slow devices

**Touch Interactions:**
- Tap targets minimum 44px
- Swipe gestures for navigation
- Long-press context menus
- Pinch-to-zoom for documents
- Pull-to-refresh functionality

**Mobile-Specific Features:**
- Device orientation handling
- Safe area insets for notched devices
- Haptic feedback for interactions
- Native file picker integration
- Camera access for document scanning

**Accessibility on Mobile:**
- Screen reader optimization
- Voice control support
- High contrast mode
- Large text support
- Reduced motion preferences

**Responsive Utilities:**
```tsx
// Custom hooks for responsive design
export const useResponsive = () => {
  const [screenSize, setScreenSize] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
  // Implementation
};

export const useTouch = () => {
  const [isTouch, setIsTouch] = useState(false);
  // Implementation
};

export const useSwipeGesture = (callbacks: SwipeCallbacks) => {
  // Implementation
};
```

**Layout Patterns:**
- Stack layout for mobile (vertical)
- Sidebar layout for tablet (adaptive)
- Multi-column layout for desktop
- Grid systems with responsive breakpoints
- Flexible spacing and sizing

**Navigation Patterns:**
- Bottom tab navigation for mobile
- Slide-out sidebar for tablet
- Fixed sidebar for desktop
- Breadcrumb navigation for deep content
- Back button handling

**Content Adaptation:**
- Truncated text with expand options
- Collapsible sections
- Adaptive font sizes
- Responsive images and media
- Mobile-optimized tables

**Error Handling:**
- Mobile-friendly error messages
- Offline state handling
- Network error recovery
- Touch-friendly retry buttons
- Progress indicators for slow connections

**Testing Strategy:**
- Device testing on multiple screens
- Touch interaction testing
- Performance testing on mobile
- Accessibility testing
- Cross-browser compatibility

**Styling Requirements:**
- Tailwind CSS responsive utilities
- Mobile-first CSS approach
- Touch-optimized spacing
- Consistent design system
- Performance-optimized CSS

Include proper TypeScript types, comprehensive responsive patterns, and follow mobile-first design principles. The layouts should provide excellent UX across all device sizes with native-like interactions.
```

---

## 7. Complete Application Shell Prompt

### Prompt for AI Code Generation:

```
Create a complete application shell that integrates all components for the PDF chatbot application. Built with Next.js 14 App Router, React 18, TypeScript, and Tailwind CSS.

**Application Structure:**
- Root layout with global configuration
- Main dashboard page with integrated components
- Responsive design with mobile-first approach
- State management for inter-component communication
- Error boundaries and loading states
- SEO optimization and accessibility

**Root Layout (app/layout.tsx):**
```tsx
interface RootLayoutProps {
  children: React.ReactNode;
}

interface GlobalState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  documents: Document[];
  searchHistory: string[];
  user: User | null;
}
```

**Main Dashboard (app/page.tsx):**
```tsx
interface DashboardState {
  uploadedFiles: string[];
  refreshDocuments: number;
  activeView: 'chat' | 'search' | 'documents';
  sidebarCollapsed: boolean;
  notifications: Notification[];
}

interface ComponentProps {
  onUploadSuccess: (filename: string) => void;
  onDocumentSelect: (document: Document) => void;
  onSearchQuery: (query: string) => void;
  onViewChange: (view: string) => void;
}
```

**Integrated Features:**
- Global state management between components
- Real-time updates and synchronization
- Consistent error handling across all components
- Loading states and progress indicators
- Notification system for user feedback

**Component Integration:**
1. **Sidebar Integration:**
   - FileUpload component at top
   - DocumentList component in middle
   - Future search interface at bottom
   - Responsive collapse/expand behavior

2. **Main Content Integration:**
   - ChatInterface as primary content
   - Search results overlay
   - Document viewer integration (future)
   - Smooth transitions between views

3. **Cross-Component Communication:**
   - Upload success triggers document list refresh
   - Document selection affects chat context
   - Search queries integrate with chat
   - Global notification system

**State Management Pattern:**
```tsx
// Global app state
const [globalState, setGlobalState] = useState<GlobalState>({
  documents: [],
  uploadedFiles: [],
  refreshTrigger: 0,
  activeDocument: null,
  searchResults: [],
  notifications: []
});

// State update functions
const handleUploadSuccess = (filename: string) => {
  setGlobalState(prev => ({
    ...prev,
    uploadedFiles: [...prev.uploadedFiles, filename],
    refreshTrigger: prev.refreshTrigger + 1
  }));
};
```

**Error Handling:**
- Global error boundary component
- Component-level error handling
- User-friendly error messages
- Retry mechanisms for failed operations
- Graceful degradation for missing features

**Loading States:**
- Global loading indicator
- Component-specific loading states
- Skeleton screens for better UX
- Progressive loading for large datasets

**Accessibility:**
- WCAG 2.1 AA compliance
- Keyboard navigation throughout
- Screen reader compatibility
- Focus management
- Alternative text for all visual elements

**SEO Optimization:**
- Proper meta tags and titles
- Structured data markup
- Open Graph tags
- Twitter Card support
- Sitemap generation

**Performance Optimization:**
- Code splitting for better load times
- Lazy loading for non-critical components
- Efficient re-renders with React.memo
- Optimized bundle sizes
- Caching strategies

**Responsive Design:**
- Mobile-first approach
- Adaptive layouts for all screen sizes
- Touch-optimized interactions
- Consistent UX across devices

**TypeScript Configuration:**
- Strict type checking
- Comprehensive interfaces
- Proper error typing
- Generic types for reusability

**Development Features:**
- Hot module replacement
- Development error overlay
- Console warnings for accessibility
- Performance monitoring

**Production Considerations:**
- Environment variable handling
- Build optimization
- Asset optimization
- Security headers
- Error tracking integration

**Global Styles:**
```css
/* globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-family: 'Inter', system-ui, sans-serif;
  }
}

@layer components {
  .scrollbar-thin {
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 #f1f5f9;
  }
}
```

**Future Enhancements:**
- Dark mode support
- User authentication
- Real-time collaboration
- Advanced search features
- Mobile app integration

Include proper TypeScript types, comprehensive error handling, and follow Next.js best practices. The application should be production-ready with excellent performance and UX.
```

---

## Usage Instructions

Each prompt above is designed to be used independently with AI code generation tools like:

1. **v0.dev**: Copy the entire prompt and paste it into v0's interface
2. **Lovable**: Use the prompt as a detailed specification for component generation
3. **Claude Code**: Provide the prompt with specific component requirements
4. **Dev Agents**: Use as comprehensive requirements for implementation

### Key Points for Implementation:

1. **API Integration**: All components include proper API integration with the FastAPI backend
2. **TypeScript**: Comprehensive type definitions for all interfaces and props
3. **Responsive Design**: Mobile-first approach with proper breakpoints
4. **Accessibility**: WCAG 2.1 AA compliance throughout
5. **Performance**: Optimized for sub-second interactions and smooth UX
6. **Error Handling**: Comprehensive error handling with user-friendly messages
7. **State Management**: Proper React hooks patterns for state management

### Customization:

- Modify API endpoints to match your backend configuration
- Adjust styling to match your brand guidelines
- Add additional features as needed for your specific use case
- Integrate with your preferred state management solution

These prompts provide a comprehensive foundation for building a production-ready PDF chatbot frontend with modern best practices and excellent user experience.