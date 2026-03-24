# Requirements Document

## Introduction

MC ChatMaster currently requires all users to have an active Appstle subscription before accessing the chat. This feature introduces a freemium usage gate that gives registered (but non-subscribed) users a configurable number of free questions before requiring a paid subscription. The goal is to let potential customers create an account, experience the value of MC ChatMaster, and then convert to a paid subscription. All usage is tracked per authenticated user for marketing and follow-up purposes.

## Glossary

- **Usage_Gate**: The backend component that tracks and enforces the free question limit for free-tier users.
- **Free_Tier_User**: A registered user who has created an account (email + password) but does not have an active Appstle subscription. They receive a limited number of free questions.
- **Subscribed_User**: A registered user with an active Appstle subscription. They have unlimited chat access.
- **Free_Question_Limit**: The maximum number of chat questions a free-tier user may ask before being required to subscribe. Configured via the `FREE_QUESTION_LIMIT` environment variable.
- **Question_Counter**: A server-side record (in PostgreSQL) that maps a user email to the number of questions that user has asked.
- **Subscription_Signup_URL**: The URL where users are directed to purchase an MC Press subscription via Appstle/Shopify. Configured via the `SUBSCRIPTION_SIGNUP_URL` environment variable.
- **Chat_Endpoint**: The backend `/chat` API endpoint that handles streaming chat responses.
- **Paywall_Overlay**: The frontend UI component displayed to free-tier users who have exhausted their free questions, prompting them to subscribe.
- **Remaining_Questions_Banner**: A frontend UI element that shows free-tier users how many free questions they have left.

## Requirements

### Requirement 1: Environment Variable Configuration

**User Story:** As an administrator, I want to configure the free question limit via an environment variable, so that I can adjust the freemium threshold without code changes.

#### Acceptance Criteria

1. THE Usage_Gate SHALL read the free question limit from the `FREE_QUESTION_LIMIT` environment variable.
2. WHEN the `FREE_QUESTION_LIMIT` environment variable is not set, THE Usage_Gate SHALL default to 5 free questions.
3. WHEN the `FREE_QUESTION_LIMIT` environment variable contains a non-integer value, THE Usage_Gate SHALL log a warning and default to 5 free questions.
4. WHEN the `FREE_QUESTION_LIMIT` environment variable is set to 0, THE Usage_Gate SHALL require subscription for all chat requests from free-tier users.

### Requirement 2: Free-Tier User Login

**User Story:** As a potential customer, I want to create an account and log in without needing a subscription first, so that I can try the product before committing.

#### Acceptance Criteria

1. WHEN a user attempts to log in with a valid email and password but has no active Appstle subscription, THE login flow SHALL allow the login and issue a session token with `subscription_status` set to `"free"`.
2. WHEN a new user creates an account (first login) with no active Appstle subscription, THE login flow SHALL create their `customer_passwords` record and issue a session token with `subscription_status` set to `"free"`.
3. THE session token for free-tier users SHALL contain a `subscription_status` claim of `"free"` to distinguish them from subscribed users.
4. WHEN a user logs in with an active Appstle subscription, THE login flow SHALL continue to work as it does today, issuing a token with `subscription_status` set to `"active"`.

### Requirement 3: Server-Side Question Counting by User Email

**User Story:** As a system operator, I want question counts tracked per registered user on the server, so that usage is accurately tied to real accounts for marketing and analytics.

#### Acceptance Criteria

1. THE Usage_Gate SHALL store Question_Counter records in a PostgreSQL table mapping each user email to a question count and a last-used timestamp.
2. WHEN a free-tier user sends a chat message, THE Usage_Gate SHALL increment the Question_Counter for that user's email by 1.
3. THE Usage_Gate SHALL increment the Question_Counter only after the chat response stream begins successfully (not on failed requests).
4. WHEN the Question_Counter for a user email reaches the Free_Question_Limit, THE Chat_Endpoint SHALL reject subsequent requests with HTTP status 402 and a JSON body containing the Subscription_Signup_URL.
5. THE Usage_Gate SHALL include the current question count and the Free_Question_Limit in every successful chat response metadata for free-tier users.

### Requirement 4: Subscribed User Bypass

**User Story:** As a subscribed user, I want unlimited access to MC ChatMaster, so that the freemium gate does not affect my experience.

#### Acceptance Criteria

1. WHEN a request to the Chat_Endpoint includes a valid session token with `subscription_status` of `"active"`, THE Usage_Gate SHALL skip the free question limit check entirely.
2. THE Usage_Gate SHALL not increment any Question_Counter for subscribed users.
3. WHEN a previously free-tier user subscribes via Appstle and logs back in, THE Chat_Endpoint SHALL serve requests using the subscribed path with no question limit.

### Requirement 5: Authentication Required for Chat

**User Story:** As a product owner, I want all users to create an account before using the chat, so that we can track all usage for marketing and follow-up purposes.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to the root URL (`/`), THE frontend SHALL redirect them to the `/login` page.
2. THE frontend middleware SHALL require a valid `session_token` cookie for access to the chat page.
3. THE `/login` page SHALL allow users to create an account or sign in regardless of their Appstle subscription status.
4. AFTER successful login, THE frontend SHALL redirect the user to the chat page.

### Requirement 6: Frontend Free-Tier Chat Experience

**User Story:** As a free-tier user, I want to see how many free questions I have remaining, so that I know when I'll need to subscribe.

#### Acceptance Criteria

1. WHEN a free-tier user is logged in, THE Remaining_Questions_Banner SHALL display the number of questions remaining (e.g., "3 of 5 free questions remaining").
2. WHEN a free-tier user has 1 free question remaining, THE Remaining_Questions_Banner SHALL display a warning-styled message indicating the last free question.
3. THE Remaining_Questions_Banner SHALL be hidden for subscribed users.
4. THE frontend SHALL determine the user's tier from the `subscription_status` claim in the session token (or from the `/api/auth/me` response).

### Requirement 7: Paywall Enforcement on Exhaustion

**User Story:** As a product owner, I want free-tier users who exhaust their free questions to be directed to the subscription page, so that they convert to paying customers.

#### Acceptance Criteria

1. WHEN the Chat_Endpoint returns HTTP 402 for a free-tier user, THE frontend SHALL display the Paywall_Overlay.
2. THE Paywall_Overlay SHALL display a kind, thoughtful message explaining that free questions have been used and a subscription is needed to continue.
3. THE Paywall_Overlay SHALL include a "Subscribe Now" button that opens the Subscription_Signup_URL in a new browser tab.
4. THE Paywall_Overlay SHALL include a "Sign In" link for users who have already subscribed and need to re-authenticate.
5. WHILE the Paywall_Overlay is displayed, THE frontend SHALL disable the chat input field and send button.
6. THE Paywall_Overlay SHALL not block the display of previous chat messages from the current session.

### Requirement 8: Usage Metadata in API Response

**User Story:** As a frontend developer, I want the API to return usage metadata, so that the frontend can display accurate remaining question counts.

#### Acceptance Criteria

1. THE Chat_Endpoint SHALL include a `usage` object in the SSE metadata event for free-tier users containing `questions_used`, `questions_limit`, and `questions_remaining` fields.
2. WHEN the user is a subscribed user, THE Chat_Endpoint SHALL omit the `usage` object from the metadata event.

### Requirement 9: Database Schema for Question Tracking

**User Story:** As a developer, I want a dedicated database table for tracking user question usage, so that question counts survive server restarts and deployments.

#### Acceptance Criteria

1. THE Usage_Gate SHALL use a `free_usage_tracking` table with columns: `id` (serial primary key), `user_email` (varchar, unique, indexed), `questions_used` (integer, default 0), `created_at` (timestamp), and `last_question_at` (timestamp).
2. THE Usage_Gate SHALL create the `free_usage_tracking` table on application startup if the table does not exist.
3. WHEN inserting or updating a Question_Counter, THE Usage_Gate SHALL use an upsert operation (INSERT ON CONFLICT UPDATE) to handle concurrent requests safely.

### Requirement 10: Remove Anonymous Access

**User Story:** As a product owner, I want all anonymous/fingerprint-based access removed, so that every user is tracked via their registered account.

#### Acceptance Criteria

1. THE backend SHALL NOT accept or process `X-Anonymous-Id` headers.
2. THE frontend SHALL NOT generate or store browser fingerprints in localStorage.
3. THE frontend middleware SHALL redirect unauthenticated users from `/` to `/login` (restore the original login-required behavior).
4. THE `free_usage_tracking` table SHALL use `user_email` as the tracking key instead of `fingerprint`.
