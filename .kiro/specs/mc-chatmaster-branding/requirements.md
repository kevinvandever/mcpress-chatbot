# Requirements Document

## Introduction

This specification covers a comprehensive branding refresh of the MC Press Chatbot frontend to align with the "MC ChatMaster" product identity. The refresh updates all user-facing text, labels, and messaging across the chat interface to reinforce the MC ChatMaster brand, convey mastery-oriented language, and present a professional identity tailored to IBM i professionals.

## Glossary

- **Frontend**: The Next.js 14 application deployed on Netlify that serves the user-facing chat interface
- **Chat_Interface**: The React component (`ChatInterface.tsx`) that renders the chat messages, input field, welcome state, and typing indicators
- **Page_Shell**: The root page component (`page.tsx`) that renders the header, status bar, quick start prompts, footer, and wraps the Chat_Interface
- **Compact_Sources**: The React component (`CompactSources.tsx`) that renders source attribution cards with reference buttons after AI responses
- **Layout**: The root layout component (`layout.tsx`) that defines the HTML metadata including the browser tab title
- **Status_Bar**: The colored banner in the Page_Shell that displays system readiness and document count
- **Quick_Start_Section**: The prompt button area in the Page_Shell that displays suggested starter questions
- **Welcome_State**: The empty-chat placeholder in the Chat_Interface that displays a greeting and subtext when no messages exist

## Requirements

### Requirement 1: Update Section Heading to MC ChatMaster Assistant

**User Story:** As a user, I want the chat section heading to say "MC ChatMaster Assistant" so that I recognize the product brand immediately.

#### Acceptance Criteria

1. THE Page_Shell SHALL display "MC ChatMaster Assistant" as the chat section heading text where "AI Assistant" currently appears
2. THE Page_Shell SHALL retain the existing chat bubble SVG icon next to the heading

### Requirement 2: Update Status Bar Messaging

**User Story:** As a user, I want the status bar to reflect the MC ChatMaster brand and content scope so that I understand what the system offers.

#### Acceptance Criteria

1. WHEN the system status is ready and documents are loaded, THE Status_Bar SHALL display "MC ChatMaster Ready!" as the primary status text in place of "System Ready!"
2. WHEN the system status is ready and documents are loaded, THE Status_Bar SHALL display "{bookCount} Books & {articleCount} Articles Loaded • Instant Expertise Active" as the secondary status text, where `bookCount` and `articleCount` are dynamically computed from the loaded documents by counting entries with `document_type` equal to `"book"` and `"article"` respectively
3. THE Status_Bar SHALL retain the existing green checkmark icon and success styling

### Requirement 3: Update Quick Start Section Title and Button Labels

**User Story:** As a user, I want the quick start section to use mastery-oriented language so that the prompts feel aligned with the ChatMaster brand.

#### Acceptance Criteria

1. THE Quick_Start_Section SHALL display "Instant Insights: Try These RPG & IBM i Questions" as the section title in place of "Quick Start - Try these questions:"
2. THE Quick_Start_Section SHALL display "Master DB2 Config on IBM i" as the label for the first prompt button, with the prompt value "How do I configure DB2 on IBM i?" unchanged
3. THE Quick_Start_Section SHALL display "Optimize Your RPG Skills" as the label for the second prompt button, with the prompt value "RPG programming best practices" unchanged
4. THE Quick_Start_Section SHALL apply orange (`--mc-orange`) background color to action-oriented buttons and purple background color to RPG-related buttons
5. THE Quick_Start_Section SHALL retain the existing hover, scale, and focus-ring interaction styles on all buttons

### Requirement 4: Update Welcome State Messaging

**User Story:** As a user, I want the welcome message to reinforce the MC ChatMaster identity so that I feel confident in the product from the first interaction.

#### Acceptance Criteria

1. WHEN no messages exist and documents are loaded, THE Welcome_State SHALL display "MC ChatMaster Ready for Your Query! ✨" as the primary welcome text in place of "Ready to help! ✨"
2. WHEN no messages exist and documents are loaded, THE Welcome_State SHALL display "Your 24/7 Guide to Mastering RPG, DB2, System Administration, and IBM i Best Practices – Fresh Insights Added as MC Press Publishes" as the subtext in place of "Ask me anything about your MC Press books"

### Requirement 5: Update Input Field Placeholder Text

**User Story:** As a user, I want the input placeholder to reflect the MC ChatMaster brand so that the interface feels cohesive.

#### Acceptance Criteria

1. WHEN documents are loaded, THE Chat_Interface SHALL display "Ask MC ChatMaster Anything" as the input field placeholder text in place of "Ask me about your MC Press books..."
2. WHEN documents are not loaded, THE Chat_Interface SHALL retain the existing "Upload documents first to start chatting..." placeholder text

### Requirement 6: Update Footer Branding

**User Story:** As a user, I want the footer to display the MC ChatMaster brand and tagline so that the product identity is consistent throughout the page.

#### Acceptance Criteria

1. THE Page_Shell SHALL display "MC ChatMaster: Instant AI-Powered IBM i Expertise" as the primary footer text in place of "MC Press Chatbot - Powered by AI"
2. THE Page_Shell SHALL display "POWERED BY AI IBM i EXPERTISE" as a secondary line below the primary footer text
3. THE Page_Shell SHALL style the secondary footer line in uppercase with smaller, lighter text

### Requirement 7: Update Reference Button Labels in Source Cards

**User Story:** As a user, I want the source attribution section to use clearer labels so that I understand what each button does.

#### Acceptance Criteria

1. THE Compact_Sources SHALL display "Sources" as the section header label in place of "References"
2. THE Compact_Sources SHALL display "View Author Profile" as the label on single-author website buttons in place of "Author"
3. THE Compact_Sources SHALL display "View Author Profiles" as the label on multi-author website dropdown buttons in place of "Authors"
4. THE Compact_Sources SHALL display "Access Source" as the label on article link buttons in place of "Read"
5. THE Compact_Sources SHALL retain the existing purple background color for author buttons and green background color for article buttons
6. THE Compact_Sources SHALL retain the "Buy" label on book purchase buttons unchanged

### Requirement 8: Update Browser Tab Title

**User Story:** As a user, I want the browser tab to display the MC ChatMaster brand so that I can identify the tab among other open tabs.

#### Acceptance Criteria

1. THE Layout SHALL set the HTML document title to "MC ChatMaster | Instant AI-Powered IBM i Expertise" in place of "MC Press Chatbot - AI-Powered Document Assistant"
2. THE Layout SHALL set the HTML meta description to "Your 24/7 AI-powered guide to mastering RPG, DB2, System Administration, and IBM i best practices from MC Press technical books and articles"
