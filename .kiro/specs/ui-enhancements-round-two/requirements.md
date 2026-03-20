# Requirements Document

## Introduction

A second round of UI enhancements for the MC ChatMaster application. This feature covers branding refinements to the header, assistant title, status bar, quick-start section, welcome message, input field, footer, responsive design, and favicon. The goal is to tighten MC Press brand consistency, improve mobile usability, and ensure dynamic (non-hardcoded) content metrics throughout the interface.

## Glossary

- **App**: The MC ChatMaster Next.js 14 frontend application located in `frontend/`.
- **Header**: The top bar of the App containing the logo, tagline, and navigation buttons.
- **Logo**: The "MC|CHATMASTER" wordmark displayed in the Header, styled with "MC |" in black with an orange/red bar, "CHAT" in bold red, and "MASTER" in black.
- **Tagline**: The text "Instant AI-Powered IBM i Expertise" displayed near the Logo in the Header.
- **Sub_Line**: The secondary text "Your 24/7 Knowledge Assistant" displayed below the Tagline.
- **Powered_Note**: A small note or link reading "Powered by MC Press Knowledge" linking to https://mc-store.com/products/mc-chatmaster.
- **Assistant_Title**: The heading "MC ChatMaster Assistant" displayed above the chat area.
- **Status_Bar**: The colored banner below the Assistant_Title showing system readiness and document counts.
- **Book_Count**: The dynamically fetched number of books loaded in the knowledge base.
- **Article_Count**: The dynamically fetched number of articles loaded in the knowledge base.
- **Quick_Start_Section**: The area containing preset prompt buttons that users can click to start a conversation.
- **MC_Press_Palette**: The brand color palette defined in design tokens: orange/red (#EF9537, #990000) for actions, purple for advanced topics, green (#A1A88B) for admin/security.
- **Welcome_Message**: The central message displayed when no chat messages exist, including the chat bubble icon.
- **Input_Field**: The textarea where users type their questions.
- **Send_Button**: The button that submits the user's message.
- **Hint_Text**: Subtle text displayed below the Input_Field providing usage guidance.
- **Footer**: The bottom bar of the App containing branding, links, and a privacy note.
- **Background_Ovals**: Faint scattered light blue oval/ellipse shapes rendered behind main content for visual continuity.
- **Favicon**: The browser tab icon for the App.
- **Tooltip**: A small informational popup that appears on hover over an element.

## Requirements

### Requirement 1: Header Logo Styling

**User Story:** As a user, I want the header logo to match the exact MC ChatMaster brand style, so that the application looks professional and on-brand.

#### Acceptance Criteria

1. THE Header SHALL display the Logo with "MC |" in black text with an orange/red vertical bar, "CHAT" in bold red (#990000), and "MASTER" in black text.
2. THE Header SHALL render subtle scattered light blue ovals in the background behind the Logo area.
3. THE Header SHALL display the Tagline "Instant AI-Powered IBM i Expertise" next to or below the Logo on desktop viewports.
4. WHILE the viewport width is less than 640px, THE Header SHALL shorten or stack the Tagline to prevent text truncation.
5. THE Header SHALL display the Sub_Line "Your 24/7 Knowledge Assistant" below the Tagline.
6. THE Header SHALL display the Powered_Note "Powered by MC Press Knowledge" as a link to https://mc-store.com/products/mc-chatmaster.

### Requirement 2: Assistant Title Enhancement

**User Story:** As a user, I want the assistant title to be visually prominent, so that I can clearly identify the chat assistant section.

#### Acceptance Criteria

1. THE Assistant_Title SHALL display the text "MC ChatMaster – Your IBM i Expertise Companion".
2. THE Assistant_Title SHALL render in a larger font size and bolder weight than the current implementation.
3. THE Assistant_Title SHALL include a subtle underline or accent in orange/red (#EF9537 or #990000) below the title text.

### Requirement 3: Dynamic Status Bar

**User Story:** As a user, I want the status bar to show live, dynamic content counts and an engaging message, so that I know the knowledge base is current and actively maintained.

#### Acceptance Criteria

1. WHEN the system status is "ready" and documents are loaded, THE Status_Bar SHALL display the text "MC ChatMaster Primed & Continuously Updating! {Book_Count} Books & {Article_Count}+ Articles Loaded – Fresh Insights Added as MC Press Publishes" using the dynamically fetched Book_Count and Article_Count values.
2. THE Status_Bar SHALL NOT hardcode the Book_Count or Article_Count values.
3. THE Status_Bar SHALL use consistent emoji and spacing in the status message.
4. WHEN a user hovers over the Status_Bar, THE App SHALL display a Tooltip with the text "Knowledge base auto-updates with every new MC Press publication".

### Requirement 4: Quick Start Section Refinement

**User Story:** As a user, I want the quick-start buttons to be visually consistent with the MC Press brand and cover more topics, so that I can quickly explore relevant IBM i questions.

#### Acceptance Criteria

1. THE Quick_Start_Section SHALL display the title "Instant Mastery Insights: Try These Expert IBM i & RPG Questions".
2. THE Quick_Start_Section SHALL style action buttons using orange/red colors from the MC_Press_Palette.
3. THE Quick_Start_Section SHALL style advanced-topic buttons using purple colors.
4. THE Quick_Start_Section SHALL style admin/security buttons using green colors from the MC_Press_Palette.
5. THE Quick_Start_Section SHALL include at least 6 prompt buttons, including buttons for "Modernize Legacy RPG to Free-Format" and "High Availability with PowerHA Essentials".
6. THE Quick_Start_Section SHALL refine button labels to reference MC Press source tie-ins where applicable.

### Requirement 5: Central Welcome Message Enhancement

**User Story:** As a user, I want the welcome message to be visually engaging and clearly communicate the value proposition, so that I understand what MC ChatMaster offers.

#### Acceptance Criteria

1. THE Welcome_Message SHALL render the words "24/7" and "Mastering" in orange/red color (#EF9537 or #990000) for emphasis.
2. THE Welcome_Message SHALL include the line "Get Precise, Sourced Answers – Every Response Links to Original MC Press Articles/Books".
3. THE Welcome_Message SHALL display the chat bubble icon at a larger size than the current 80x80px implementation.
4. THE Welcome_Message SHALL apply a subtle pulse animation to the chat bubble icon that respects the prefers-reduced-motion media query.

### Requirement 6: Input Field and Send Button Redesign

**User Story:** As a user, I want the input field and send button to be clearly branded and informative, so that I feel confident asking questions.

#### Acceptance Criteria

1. THE Input_Field SHALL display the placeholder text "Ask MC ChatMaster Anything About IBM i, RPG, DB2...".
2. THE Send_Button SHALL use an orange/red background color (#EF9537 or #990000) instead of the current blue.
3. THE Send_Button SHALL display the label "Ask Expert" when not in a streaming state.
4. WHILE the App is in a streaming state, THE Send_Button SHALL display the label "Thinking..." with a spinner animation.
5. THE App SHALL display Hint_Text below the Input_Field reading "Unlimited Queries • 24/7 • Sources Always Linked".

### Requirement 7: Footer Enhancement

**User Story:** As a user, I want the footer to provide useful links and reinforce trust, so that I can access MC Press resources and feel confident about privacy.

#### Acceptance Criteria

1. THE Footer SHALL display the text "MC ChatMaster: Instant AI-Powered IBM i Expertise – Powered by MC Press Online".
2. THE Footer SHALL include a link to mcpressonline.com and a link to mc-store.com.
3. THE Footer SHALL display the privacy note "Private • Secure • Continuously Updated Knowledge Base".
4. THE Footer SHALL render subtle Background_Ovals for visual continuity with the Header.

### Requirement 8: Responsive Design

**User Story:** As a user on a mobile device or tablet, I want the application to be fully usable and visually correct, so that I can access MC ChatMaster from any device.

#### Acceptance Criteria

1. WHILE the viewport width is less than 640px, THE App SHALL stack Quick_Start_Section buttons vertically to prevent horizontal overflow.
2. WHILE the viewport width is less than 640px, THE Input_Field SHALL occupy the full width of the viewport with appropriate padding.
3. WHILE the viewport width is less than 640px, THE Send_Button SHALL occupy the full width below the Input_Field or remain appropriately sized for touch targets (minimum 44x44px).
4. THE App SHALL ensure all text content remains readable without horizontal scrolling on viewports as narrow as 320px.
5. THE App SHALL ensure the chat message area and answer display are fully scrollable and readable on mobile viewports.
6. WHILE the viewport width is between 640px and 1024px, THE App SHALL adapt layout spacing and font sizes for tablet viewports.

### Requirement 9: Favicon

**User Story:** As a user, I want the browser tab to show the MC ChatMaster logo, so that I can easily identify the tab among other open tabs.

#### Acceptance Criteria

1. THE App SHALL use the MC ChatMaster logo as the favicon displayed in the browser tab.
2. THE App SHALL provide favicon files in multiple sizes (16x16, 32x32, and 180x180 for Apple touch icon) for cross-browser compatibility.

### Requirement 10: Brand Consistency and Visual Polish

**User Story:** As a user, I want the entire application to use consistent branding, so that the experience feels polished and professional.

#### Acceptance Criteria

1. THE App SHALL use "MC ChatMaster" (with capital C in Chat and capital M in Master) consistently across all visible text.
2. THE App SHALL render faint scattered light blue Background_Ovals behind the main content area for visual continuity.
3. WHEN the App displays a chat response, THE App SHALL append the text "Need more details? Dive into the full source: [link]" at the end of each response where source links are available.
4. THE App SHALL ensure all dynamic statistics (Book_Count, Article_Count) are fetched from the backend API and are never hardcoded.
