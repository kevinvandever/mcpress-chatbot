# Requirements Document

## Introduction

MC ChatMaster has a working freemium usage gate (v1) that tracks questions per user email in PostgreSQL, enforces a configurable free question limit (currently 5), and shows a simple remaining-questions banner plus a paywall overlay when questions are exhausted. This v2 enhancement raises the free question limit to 8, introduces a progressive warning system with stage-specific marketing copy, updates subscription pricing display to $19.95/month, adds a Product-Qualified Lead (PQL) detection signal, and considers email/newsletter capture for warm leads. The goal is to increase free-to-paid conversion by giving users more room to experience value before hitting friction, while surfacing upgrade prompts at psychologically optimal moments.

These changes were requested by the MC Press partner based on real user behavior: the 5-question limit is too tight for a knowledge assistant where the "aha moment" may require one real question plus follow-ups.

**Out of scope:** A/B testing (explicitly deferred by partner), Google Analytics integration (separate task), changes to the login flow (working from v1), changes to subscription verification (working from v1).

## Glossary

- **Usage_Gate**: The backend component (`backend/usage_gate.py`) that tracks and enforces the free question limit for free-tier users.
- **Free_Tier_User**: A registered user with `subscription_status` of `"free"` — they have created an account but do not have an active Appstle subscription.
- **Subscribed_User**: A registered user with `subscription_status` of `"active"` — they have an active Appstle subscription and unlimited chat access.
- **Free_Question_Limit**: The maximum number of lifetime free questions a free-tier user may ask. Configured via the `FREE_QUESTION_LIMIT` environment variable (new default: 8).
- **Progressive_Warning_System**: A frontend component that displays stage-specific messaging based on how many questions a free-tier user has consumed, replacing the simple remaining-questions banner from v1.
- **Warning_Stage**: One of five distinct messaging stages: silent (questions 1–5), soft warning (question 6), stronger warning (question 7), final answer with upgrade prompt (question 8), and hard gate (question 9+).
- **Paywall_Overlay**: The frontend UI component displayed when a free-tier user has exhausted all free questions, blocking further input and prompting subscription.
- **Remaining_Questions_Banner**: The existing v1 frontend component (`RemainingQuestionsBanner.tsx`) that will be replaced by the Progressive_Warning_System.
- **PQL_Signal**: A Product-Qualified Lead indicator — a flag set when a free-tier user asks 3 or more technical questions in a single browser session, suggesting they are working through a real problem and are a high-value conversion target.
- **PQL_Upgrade_Prompt**: A variant of the upgrade messaging shown to PQL-flagged users that is more direct and problem-aware.
- **Newsletter_Capture_Prompt**: An optional UI element shown around question 6 that invites free-tier users to join the MC Press mailing list or newsletter, since they have already authenticated with email.
- **Chat_Endpoint**: The backend `/chat` API endpoint that handles streaming chat responses.
- **SSE_Metadata**: The Server-Sent Events metadata object included in chat responses for free-tier users, containing `questions_used`, `questions_limit`, and `questions_remaining`.
- **Subscription_Signup_URL**: The URL where users are directed to purchase a subscription. Configured via the `SUBSCRIPTION_SIGNUP_URL` environment variable.

## Requirements

### Requirement 1: Raise Free Question Limit Default to 8

**User Story:** As a product owner, I want the default free question limit raised from 5 to 8, so that users have enough room to experience the value of MC ChatMaster before hitting the paywall.

#### Acceptance Criteria

1. WHEN the `FREE_QUESTION_LIMIT` environment variable is not set, THE Usage_Gate SHALL default to 8 free questions.
2. WHEN the `FREE_QUESTION_LIMIT` environment variable is set to a valid integer, THE Usage_Gate SHALL use that value as the free question limit.
3. WHEN the `FREE_QUESTION_LIMIT` environment variable contains a non-integer value, THE Usage_Gate SHALL log a warning and default to 8 free questions.
4. WHEN the `FREE_QUESTION_LIMIT` environment variable is set to 0, THE Usage_Gate SHALL require subscription for all chat requests from free-tier users.

### Requirement 2: Silent Phase — No Warnings for Questions 1 Through 5

**User Story:** As a free-tier user, I want to use my first 5 questions without any friction or warnings, so that I can explore MC ChatMaster without feeling pressured.

#### Acceptance Criteria

1. WHILE a Free_Tier_User has used fewer than 6 questions (questions_used < 6), THE Progressive_Warning_System SHALL display no warning banner or upgrade messaging.
2. WHILE a Free_Tier_User has used fewer than 6 questions, THE frontend SHALL render the chat experience identically to a Subscribed_User except for the absence of the "Unlimited Queries" footer text.

### Requirement 3: Soft Warning at Question 6

**User Story:** As a free-tier user, I want a gentle notification after my 6th question, so that I know how many free questions I have left without feeling alarmed.

#### Acceptance Criteria

1. WHEN a Free_Tier_User completes their 6th question (questions_used equals 6), THE Progressive_Warning_System SHALL display the message: "You've used 6 of your 8 free MC ChatMaster questions. You still have 2 left to explore the MC Press knowledge base."
2. THE soft warning message SHALL be styled with an informational appearance (blue or neutral tone) and SHALL NOT use urgent or alarming colors.
3. THE soft warning banner SHALL appear below the chat messages area and above the input field.

### Requirement 4: Stronger Warning at Question 7

**User Story:** As a free-tier user, I want a clearer warning after my 7th question, so that I understand I am about to run out of free access and can consider upgrading.

#### Acceptance Criteria

1. WHEN a Free_Tier_User completes their 7th question (questions_used equals 7), THE Progressive_Warning_System SHALL display the message: "You have 1 free question remaining. Upgrade anytime for unlimited source-backed IBM i answers."
2. THE stronger warning message SHALL be styled with a cautionary appearance (amber or warm tone) to convey urgency without alarm.
3. THE stronger warning banner SHALL appear below the chat messages area and above the input field.

### Requirement 5: Final Question — Full Answer Then Upgrade Prompt at Question 8

**User Story:** As a free-tier user, I want my 8th question answered fully before seeing the upgrade prompt, so that I leave with a positive impression of the product even as I hit the limit.

#### Acceptance Criteria

1. WHEN a Free_Tier_User submits their 8th question (questions_used equals 7 at time of submission, will become 8 after response), THE Chat_Endpoint SHALL process and stream the full answer.
2. WHEN the SSE_Metadata for a Free_Tier_User indicates questions_remaining equals 0 after the 8th question, THE Progressive_Warning_System SHALL display the upgrade prompt with the following copy: "You've reached your 8 free questions. Continue with unlimited access to MC ChatMaster for $19.95/month. Get instant, source-linked answers from 113+ MC Press books and 6,300+ technical articles."
3. THE upgrade prompt SHALL include a primary call-to-action button with the text "Start Unlimited Access — $19.95/month" that opens the Subscription_Signup_URL in a new browser tab.
4. THE upgrade prompt SHALL include the text "Cancel anytime." displayed near the pricing information.
5. AFTER the upgrade prompt is displayed, THE frontend SHALL disable the chat input field and send button to prevent further questions.
6. THE upgrade prompt SHALL not block the display of previous chat messages including the 8th answer.

### Requirement 6: Hard Gate at Question 9 and Beyond

**User Story:** As a product owner, I want users who have exhausted all 8 free questions to be blocked from asking more, so that they must subscribe to continue.

#### Acceptance Criteria

1. WHEN a Free_Tier_User has used all free questions (questions_used >= Free_Question_Limit) and submits a new chat request, THE Chat_Endpoint SHALL reject the request with HTTP status 402.
2. THE HTTP 402 response body SHALL include the `signup_url` and `usage` object with `questions_used`, `questions_limit`, and `questions_remaining` fields.
3. WHEN the frontend receives an HTTP 402 response, THE Paywall_Overlay SHALL be displayed with the same upgrade copy and pricing as the question 8 prompt.
4. WHILE the Paywall_Overlay is displayed, THE frontend SHALL disable the chat input field and send button.

### Requirement 7: Updated Subscription Pricing Display

**User Story:** As a product owner, I want the subscription price of $19.95/month displayed in all upgrade prompts, so that users see clear, consistent pricing throughout the conversion funnel.

#### Acceptance Criteria

1. THE upgrade prompt at question 8 SHALL display the price "$19.95/month".
2. THE Paywall_Overlay (question 9+ hard gate) SHALL display the price "$19.95/month".
3. THE stronger warning at question 7 SHALL reference upgrading but SHALL NOT display the specific price (to avoid premature price anchoring).
4. THE primary call-to-action button text SHALL be "Start Unlimited Access — $19.95/month" in both the question 8 prompt and the Paywall_Overlay.
5. THE text "Cancel anytime." SHALL appear near the pricing in both the question 8 prompt and the Paywall_Overlay.

### Requirement 8: Subscribed User Bypass — No Changes

**User Story:** As a subscribed user, I want unlimited access to MC ChatMaster with no warnings or banners, so that the freemium gate does not affect my experience.

#### Acceptance Criteria

1. WHEN a request to the Chat_Endpoint includes a valid session token with `subscription_status` of `"active"`, THE Usage_Gate SHALL skip the free question limit check entirely.
2. THE Progressive_Warning_System SHALL not render any warning banners or upgrade prompts for Subscribed_Users.
3. THE Chat_Endpoint SHALL not increment any question counter for Subscribed_Users.

### Requirement 9: Product-Qualified Lead Detection

**User Story:** As a product owner, I want users who ask 3 or more technical questions in a single session flagged as product-qualified leads, so that high-intent users receive more targeted upgrade messaging.

#### Acceptance Criteria

1. THE frontend SHALL track the number of questions asked by a Free_Tier_User in the current browser session (using in-memory state, not persisted across page reloads).
2. WHEN a Free_Tier_User asks 3 or more questions in a single browser session, THE frontend SHALL set a PQL_Signal flag for that session.
3. WHEN the PQL_Signal is set and the user reaches the question 8 upgrade prompt, THE Progressive_Warning_System SHALL display the PQL variant copy: "Looks like you're working through a real IBM i issue. Unlock unlimited access and keep going without interruption." followed by the standard pricing and call-to-action.
4. WHEN the PQL_Signal is set and the user reaches the hard gate (question 9+), THE Paywall_Overlay SHALL display the PQL variant copy instead of the standard copy.
5. WHEN the PQL_Signal is not set (user reached question 8 across multiple sessions), THE Progressive_Warning_System SHALL display the standard upgrade copy.

### Requirement 10: Newsletter Capture Prompt at Question 6

**User Story:** As a product owner, I want to invite free-tier users to join the MC Press newsletter around question 6, so that we capture warm leads for marketing follow-up without adding friction to the early trial experience.

#### Acceptance Criteria

1. WHEN a Free_Tier_User completes their 6th question and the PQL_Signal is not yet set, THE Newsletter_Capture_Prompt SHALL display an optional, dismissible prompt inviting the user to join the MC Press newsletter or mailing list.
2. THE Newsletter_Capture_Prompt SHALL be non-blocking — the user SHALL be able to dismiss the prompt and continue asking questions without subscribing to the newsletter.
3. THE Newsletter_Capture_Prompt SHALL pre-fill the user's email address from their authenticated session (since they are already logged in).
4. WHEN the user dismisses the Newsletter_Capture_Prompt, THE frontend SHALL not show the prompt again during the same browser session.
5. IF the user has already dismissed the Newsletter_Capture_Prompt or has already signed up for the newsletter, THE frontend SHALL not display the prompt again.

### Requirement 11: Event Emission for Analytics Readiness

**User Story:** As a developer, I want the progressive warning system to emit trackable events at each warning stage, so that analytics integration (e.g., Google Analytics) can be added later without code changes to the warning system.

#### Acceptance Criteria

1. WHEN the Progressive_Warning_System transitions to a new Warning_Stage (soft warning, stronger warning, upgrade prompt, or hard gate), THE frontend SHALL emit a custom DOM event or call a tracking callback with the stage name and questions_used count.
2. WHEN a Free_Tier_User clicks the "Start Unlimited Access" call-to-action button, THE frontend SHALL emit a trackable event with the action "upgrade_click" and the current Warning_Stage.
3. WHEN a Free_Tier_User dismisses the Newsletter_Capture_Prompt, THE frontend SHALL emit a trackable event with the action "newsletter_dismissed".
4. WHEN a Free_Tier_User submits the Newsletter_Capture_Prompt, THE frontend SHALL emit a trackable event with the action "newsletter_signup".
5. THE event emission mechanism SHALL be implemented as a simple callback or custom event pattern that does not depend on any specific analytics library.

### Requirement 12: Progressive Warning Copy Driven by Backend Usage Data

**User Story:** As a developer, I want the progressive warning stages determined by the existing `questions_used` and `questions_limit` values from the backend, so that no new backend API changes are needed for the warning system.

#### Acceptance Criteria

1. THE frontend SHALL determine the current Warning_Stage by comparing `questions_used` from the SSE_Metadata against the `questions_limit` value.
2. THE Progressive_Warning_System SHALL compute warning stages as follows: silent when questions_used < (questions_limit - 2), soft warning when questions_used equals (questions_limit - 2), stronger warning when questions_used equals (questions_limit - 1), upgrade prompt when questions_used equals questions_limit, hard gate when questions_used > questions_limit.
3. WHEN the `questions_limit` value changes (e.g., environment variable updated), THE Progressive_Warning_System SHALL adapt the warning thresholds automatically without frontend code changes.
4. THE frontend SHALL NOT hardcode the number 8 for warning stage calculations — all thresholds SHALL be derived from the `questions_limit` value returned by the backend.
