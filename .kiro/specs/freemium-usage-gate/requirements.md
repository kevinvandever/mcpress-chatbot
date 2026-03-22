# Requirements Document

## Introduction

MC ChatMaster currently requires all users to sign in with an MC Press subscription before accessing the chat. This feature introduces a freemium usage gate that allows anonymous (non-authenticated) users to ask a configurable number of free questions before being required to sign up for a subscription. The goal is to let potential customers experience the value of MC ChatMaster before committing to a subscription, increasing conversion rates.

## Glossary

- **Usage_Gate**: The backend component that tracks and enforces the free question limit for anonymous users.
- **Anonymous_User**: A visitor who has not signed in with an MC Press subscription. Identified by a browser-generated fingerprint stored in localStorage.
- **Free_Question_Limit**: The maximum number of chat questions an anonymous user may ask before being required to subscribe. Configured via the `FREE_QUESTION_LIMIT` environment variable.
- **Fingerprint**: A unique identifier generated per browser and persisted in localStorage to track anonymous user question counts.
- **Question_Counter**: A server-side record (in PostgreSQL) that maps a Fingerprint to the number of questions that anonymous user has asked.
- **Subscription_Signup_URL**: The URL where users are redirected to purchase an MC Press subscription. Configured via the existing `SUBSCRIPTION_SIGNUP_URL` environment variable.
- **Chat_Endpoint**: The backend `/chat` API endpoint that handles streaming chat responses.
- **Paywall_Overlay**: The frontend UI component displayed to anonymous users who have exhausted their free questions, prompting them to subscribe.
- **Remaining_Questions_Banner**: A frontend UI element that shows anonymous users how many free questions they have left.

## Requirements

### Requirement 1: Environment Variable Configuration

**User Story:** As an administrator, I want to configure the free question limit via an environment variable, so that I can adjust the freemium threshold without code changes.

#### Acceptance Criteria

1. THE Usage_Gate SHALL read the free question limit from the `FREE_QUESTION_LIMIT` environment variable.
2. WHEN the `FREE_QUESTION_LIMIT` environment variable is not set, THE Usage_Gate SHALL default to 5 free questions.
3. WHEN the `FREE_QUESTION_LIMIT` environment variable contains a non-integer value, THE Usage_Gate SHALL log a warning and default to 5 free questions.
4. WHEN the `FREE_QUESTION_LIMIT` environment variable is set to 0, THE Usage_Gate SHALL require subscription for all chat requests from anonymous users.

### Requirement 2: Anonymous User Identification

**User Story:** As a system operator, I want anonymous users to be uniquely identified across sessions, so that the free question limit is enforced per user rather than per page load.

#### Acceptance Criteria

1. WHEN an anonymous user visits MC ChatMaster for the first time, THE Chat_Endpoint SHALL generate a UUID-based Fingerprint and return it in the response headers.
2. THE Chat_Endpoint SHALL accept the Fingerprint via an `X-Anonymous-Id` request header on subsequent requests.
3. WHEN an anonymous user provides a valid Fingerprint, THE Usage_Gate SHALL use the provided Fingerprint to look up the Question_Counter.
4. WHEN an anonymous user does not provide a Fingerprint, THE Usage_Gate SHALL generate a new Fingerprint and treat the user as having zero prior questions.
5. THE frontend SHALL persist the Fingerprint in localStorage under the key `anonymousUserId`.
6. IF localStorage is cleared or unavailable, THEN THE Usage_Gate SHALL treat the user as a new anonymous user with a fresh Fingerprint.

### Requirement 3: Server-Side Question Counting

**User Story:** As a system operator, I want question counts tracked on the server, so that users cannot bypass the limit by clearing browser storage alone.

#### Acceptance Criteria

1. THE Usage_Gate SHALL store Question_Counter records in a PostgreSQL table mapping each Fingerprint to a question count and a last-used timestamp.
2. WHEN an anonymous user sends a chat message, THE Usage_Gate SHALL increment the Question_Counter for that Fingerprint by 1.
3. THE Usage_Gate SHALL increment the Question_Counter only after the chat response stream begins successfully (not on failed requests).
4. WHEN the Question_Counter for a Fingerprint reaches the Free_Question_Limit, THE Chat_Endpoint SHALL reject subsequent requests from that Fingerprint with HTTP status 402 and a JSON body containing the Subscription_Signup_URL.
5. THE Usage_Gate SHALL include the current question count and the Free_Question_Limit in every successful chat response metadata.

### Requirement 4: Authenticated User Bypass

**User Story:** As a subscribed user, I want unlimited access to MC ChatMaster, so that the freemium gate does not affect my experience.

#### Acceptance Criteria

1. WHEN a request to the Chat_Endpoint includes a valid subscription authentication token (cookie-based JWT), THE Usage_Gate SHALL skip the free question limit check entirely.
2. THE Usage_Gate SHALL not increment any Question_Counter for authenticated users.
3. WHEN a previously anonymous user signs in, THE Chat_Endpoint SHALL serve requests using the authenticated path with no question limit.

### Requirement 5: Frontend Anonymous Chat Flow

**User Story:** As an anonymous visitor, I want to use MC ChatMaster without signing in, so that I can evaluate the product before subscribing.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to the MC ChatMaster home page, THE frontend SHALL display the chat interface without requiring login.
2. THE frontend SHALL generate and store a Fingerprint in localStorage on first visit.
3. THE frontend SHALL send the Fingerprint in the `X-Anonymous-Id` header with every chat request.
4. WHILE an anonymous user has remaining free questions, THE Remaining_Questions_Banner SHALL display the number of questions remaining (e.g., "3 of 5 free questions remaining").
5. WHEN an anonymous user has 1 free question remaining, THE Remaining_Questions_Banner SHALL display a warning-styled message indicating the last free question.

### Requirement 6: Paywall Enforcement on Exhaustion

**User Story:** As a product owner, I want anonymous users who exhaust their free questions to be directed to the subscription page, so that they convert to paying customers.

#### Acceptance Criteria

1. WHEN the Chat_Endpoint returns HTTP 402 for an anonymous user, THE frontend SHALL display the Paywall_Overlay.
2. THE Paywall_Overlay SHALL display a message explaining that free questions have been used and a subscription is required to continue.
3. THE Paywall_Overlay SHALL include a "Subscribe Now" button that opens the Subscription_Signup_URL in a new browser tab.
4. THE Paywall_Overlay SHALL include a "Sign In" link that navigates to the existing `/login` page for users who already have a subscription.
5. WHILE the Paywall_Overlay is displayed, THE frontend SHALL disable the chat input field and send button.
6. THE Paywall_Overlay SHALL not block the display of previous chat messages from the current session.

### Requirement 7: Remaining Questions Metadata in API Response

**User Story:** As a frontend developer, I want the API to return usage metadata, so that the frontend can display accurate remaining question counts.

#### Acceptance Criteria

1. THE Chat_Endpoint SHALL include a `usage` object in the SSE metadata event for anonymous users containing `questions_used`, `questions_limit`, and `questions_remaining` fields.
2. WHEN the user is authenticated, THE Chat_Endpoint SHALL omit the `usage` object from the metadata event.
3. THE Chat_Endpoint SHALL include the `X-Anonymous-Id` header in the response so the frontend can persist the Fingerprint.

### Requirement 8: Database Schema for Question Tracking

**User Story:** As a developer, I want a dedicated database table for tracking anonymous usage, so that question counts survive server restarts and deployments.

#### Acceptance Criteria

1. THE Usage_Gate SHALL use a `free_usage_tracking` table with columns: `id` (serial primary key), `fingerprint` (varchar, unique, indexed), `questions_used` (integer, default 0), `created_at` (timestamp), and `last_question_at` (timestamp).
2. THE Usage_Gate SHALL create the `free_usage_tracking` table on application startup if the table does not exist.
3. WHEN inserting or updating a Question_Counter, THE Usage_Gate SHALL use an upsert operation (INSERT ON CONFLICT UPDATE) to handle concurrent requests safely.

### Requirement 9: Landing Page Routing for Anonymous Users

**User Story:** As an anonymous visitor, I want to reach the chat page directly, so that I do not have to navigate through a login wall to try the product.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to the root URL (`/`), THE frontend SHALL display the chat interface with the freemium experience instead of redirecting to `/login`.
2. THE frontend SHALL check authentication status on page load and render either the full authenticated experience or the freemium anonymous experience accordingly.
3. WHILE in anonymous mode, THE frontend SHALL hide UI elements that require authentication (History button, Logout button, user email display).
4. THE frontend SHALL display a "Sign In" link in the header during anonymous mode.
