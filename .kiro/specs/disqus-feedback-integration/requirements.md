# Requirements Document

## Introduction

This feature integrates Disqus commenting into the MC ChatMaster site, providing a "Community Feedback" section below the chat interface on the main page. The integration uses a single, site-wide comment thread (not per-page) and is presented in a collapsible panel that stays collapsed by default to preserve the chat-first experience. All comments are public and visible to all users. The Disqus shortname is `mc-chatmaster-disqus-com`.

## Glossary

- **Feedback_Panel**: The collapsible UI section rendered below the ChatInterface component on the main page that contains the Disqus embed.
- **Disqus_Embed**: The third-party Disqus Universal Code script that loads and renders the comment thread inside the Feedback_Panel.
- **Chat_Page**: The main page of MC ChatMaster (`frontend/app/page.tsx`) where the ChatInterface and Feedback_Panel reside.
- **Collapse_Toggle**: The clickable header element of the Feedback_Panel that expands or collapses the Disqus comment thread.

## Requirements

### Requirement 1: Collapsible Feedback Panel

**User Story:** As a site visitor, I want a collapsible "Community Feedback" section below the chat interface, so that I can optionally view and leave comments without the comments dominating the chat experience.

#### Acceptance Criteria

1. THE Chat_Page SHALL render a Feedback_Panel below the ChatInterface component and above the footer.
2. THE Feedback_Panel SHALL display a Collapse_Toggle with the label "Community Feedback" and a visual expand/collapse indicator (e.g., chevron icon).
3. WHEN the Chat_Page loads, THE Feedback_Panel SHALL be in a collapsed state, hiding the Disqus_Embed content.
4. WHEN a user clicks the Collapse_Toggle while the Feedback_Panel is collapsed, THE Feedback_Panel SHALL expand to reveal the Disqus_Embed.
5. WHEN a user clicks the Collapse_Toggle while the Feedback_Panel is expanded, THE Feedback_Panel SHALL collapse to hide the Disqus_Embed.
6. WHILE the Feedback_Panel is collapsed, THE Feedback_Panel SHALL occupy minimal vertical space (toggle header only, no comment content visible).

### Requirement 2: Disqus Embed Integration

**User Story:** As a site visitor, I want to see and participate in a Disqus comment thread, so that I can share feedback and read what other users have said about MC ChatMaster.

#### Acceptance Criteria

1. WHEN the Feedback_Panel is expanded for the first time, THE Disqus_Embed SHALL load the Disqus Universal Code using the shortname `mc-chatmaster-disqus-com`.
2. THE Disqus_Embed SHALL use a single, fixed page identifier and URL so that all visitors share one site-wide comment thread regardless of the page URL or query parameters.
3. THE Disqus_Embed SHALL render inside a container with the id `disqus_thread`.
4. IF the Disqus script fails to load (e.g., network error or ad blocker), THEN THE Feedback_Panel SHALL display a fallback message indicating that comments could not be loaded.

### Requirement 3: Visual Consistency and Minimal Footprint

**User Story:** As a product owner, I want the feedback section to match the existing MC ChatMaster design language and remain unobtrusive, so that the chat interface stays the primary focus of the page.

#### Acceptance Criteria

1. THE Feedback_Panel SHALL use the same card styling (white background, rounded corners, border, shadow) as the existing chat section on the Chat_Page.
2. THE Feedback_Panel SHALL be contained within the same `max-w-7xl` content wrapper used by the chat section.
3. WHILE the Feedback_Panel is collapsed, THE Feedback_Panel SHALL have a maximum height equal to the Collapse_Toggle header row only.
4. THE Collapse_Toggle SHALL use the MC ChatMaster brand color palette (e.g., `var(--mc-blue)` or `var(--text-primary)`) for the heading text and icon.

### Requirement 4: Lazy Loading of Disqus Script

**User Story:** As a developer, I want the Disqus script to load only when the user expands the feedback panel, so that page load performance is not impacted by the third-party embed.

#### Acceptance Criteria

1. WHEN the Chat_Page loads, THE Chat_Page SHALL NOT load the Disqus embed script.
2. WHEN the Feedback_Panel is expanded for the first time, THE Feedback_Panel SHALL inject the Disqus embed script into the DOM.
3. WHEN the Feedback_Panel is collapsed after having been expanded, THE Disqus_Embed SHALL remain in the DOM (no re-load on subsequent expand).
4. THE Disqus_Embed script SHALL load asynchronously and SHALL NOT block rendering of the Chat_Page.

### Requirement 5: Accessibility

**User Story:** As a user relying on assistive technology, I want the feedback panel to be keyboard-navigable and screen-reader friendly, so that I can access the community comments.

#### Acceptance Criteria

1. THE Collapse_Toggle SHALL be focusable via keyboard tab navigation.
2. WHEN a user presses Enter or Space while the Collapse_Toggle is focused, THE Feedback_Panel SHALL toggle between expanded and collapsed states.
3. THE Collapse_Toggle SHALL include an `aria-expanded` attribute that reflects the current state of the Feedback_Panel (`true` when expanded, `false` when collapsed).
4. THE Disqus_Embed container SHALL include an `aria-label` attribute with the value "Community feedback comments".
