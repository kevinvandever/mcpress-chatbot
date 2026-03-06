# Requirements Document: Appstle Subscription Authentication

## Introduction

This specification defines the replacement of the current demo password login with Appstle subscription-based authentication for the MC Press Chatbot. Users will log in with email and password, which the backend will verify against the Appstle API to confirm an active subscription. Users without a valid subscription will be redirected to a signup/subscription page on the Appstle/MC Press storefront.

**SCOPE NOTE**: This specification covers **customer/user authentication only**. The existing admin authentication system (email/password with bcrypt + JWT for `/api/admin/*` routes) is **out of scope** and will remain completely unchanged.

## Glossary

- **Appstle_API**: The Appstle subscription management API used to verify customer subscription status
- **Login_Service**: Backend FastAPI service that handles user login by verifying credentials against Appstle
- **Subscription_Status**: The state of a customer's Appstle subscription (active, cancelled, expired, paused)
- **Auth_Token**: JWT issued by the backend upon successful subscription verification
- **Login_Page**: Frontend page where users enter email and password
- **Signup_Page**: External page on the MC Press/Appstle storefront where users can purchase a subscription
- **Session_Cookie**: HTTP-only secure cookie storing the Auth_Token for authenticated sessions
- **Middleware**: Next.js middleware that checks authentication state and redirects unauthenticated users
- **Admin_Auth**: The existing separate admin authentication system (unchanged by this spec)
- **Chat_Interface**: The main chatbot page accessible only to authenticated users with valid subscriptions

## Requirements

### Requirement 1: User Login with Appstle Verification

**User Story:** As a user, I want to log in with my email and password, so that the system verifies my Appstle subscription and grants me access to the chatbot.

#### Acceptance Criteria

1. THE Login_Page SHALL present email and password input fields to the user
2. WHEN a user submits email and password, THE Login_Service SHALL send a verification request to the Appstle_API with the provided credentials
3. WHEN the Appstle_API confirms a valid active subscription, THE Login_Service SHALL issue an Auth_Token containing the user email and subscription status
4. WHEN the Appstle_API confirms a valid active subscription, THE Login_Service SHALL return the Auth_Token to the frontend
5. WHEN the Appstle_API returns invalid credentials, THE Login_Service SHALL return a 401 response with the message "Invalid email or password"
6. WHEN the Appstle_API is unreachable, THE Login_Service SHALL return a 503 response with the message "Subscription service temporarily unavailable"

### Requirement 2: Subscription Validation

**User Story:** As the system, I want to verify subscription status during login, so that only users with active subscriptions can access the chatbot.

#### Acceptance Criteria

1. WHEN the Appstle_API returns an active subscription status, THE Login_Service SHALL grant access
2. WHEN the Appstle_API returns a cancelled subscription status, THE Login_Service SHALL deny access and return a redirect URL to the Signup_Page
3. WHEN the Appstle_API returns an expired subscription status, THE Login_Service SHALL deny access and return a redirect URL to the Signup_Page
4. WHEN the Appstle_API returns a paused subscription status, THE Login_Service SHALL deny access and return a redirect URL to the Signup_Page
5. WHEN the Appstle_API returns no subscription found for the user, THE Login_Service SHALL deny access and return a redirect URL to the Signup_Page
6. THE Login_Service SHALL include the subscription expiration date in the Auth_Token claims when access is granted

### Requirement 3: Auth Token Management

**User Story:** As the system, I want to issue and validate JWT tokens, so that authenticated users maintain secure sessions.

#### Acceptance Criteria

1. THE Login_Service SHALL create a JWT Auth_Token containing sub (user email), subscription_status, subscription_expires_at, iat, and exp claims
2. THE Login_Service SHALL set Auth_Token expiration to 1 hour from issuance
3. THE Login_Service SHALL sign the Auth_Token using a configurable secret key from the JWT_SECRET_KEY environment variable
4. WHEN a protected API request is received, THE Login_Service SHALL verify the Auth_Token signature and expiration
5. WHEN the Auth_Token is expired, THE Login_Service SHALL return a 401 response
6. WHEN the Auth_Token signature is invalid, THE Login_Service SHALL return a 401 response
7. THE Login_Service SHALL store the Auth_Token in an HTTP-only secure cookie with SameSite=Lax
8. THE Login_Service SHALL expose a POST /api/auth/refresh endpoint that re-verifies the user's subscription with the Appstle_API and issues a new Auth_Token
9. WHEN the refresh endpoint is called, THE Login_Service SHALL verify the existing Auth_Token (even if expired within a grace window of 5 minutes) before re-verifying with Appstle
10. WHEN the Appstle_API confirms the subscription is still active during refresh, THE Login_Service SHALL issue a new 1-hour Auth_Token
11. WHEN the Appstle_API indicates the subscription is no longer active during refresh, THE Login_Service SHALL return a 403 response with a redirect URL to the Signup_Page

### Requirement 4: Frontend Authentication Flow

**User Story:** As a user, I want to be redirected to the login page when unauthenticated, so that I can access the chatbot after logging in.

#### Acceptance Criteria

1. WHEN an unauthenticated user visits the Chat_Interface, THE Middleware SHALL redirect the user to the Login_Page
2. WHEN a user successfully logs in, THE Login_Page SHALL redirect the user to the Chat_Interface
3. WHEN a user's subscription is not valid, THE Login_Page SHALL display a message indicating the subscription is required and provide a link to the Signup_Page
4. WHEN a user clicks the subscription link, THE Login_Page SHALL open the Signup_Page in a new browser tab
5. THE Login_Page SHALL display loading state while the Appstle_API verification is in progress
6. THE Login_Page SHALL display error messages returned by the Login_Service
7. WHEN a user is already authenticated with a valid Auth_Token, THE Login_Page SHALL redirect the user to the Chat_Interface

### Requirement 5: Logout

**User Story:** As a user, I want to log out of the chatbot, so that my session is terminated securely.

#### Acceptance Criteria

1. THE Chat_Interface SHALL display a logout button when the user is authenticated
2. WHEN a user clicks the logout button, THE System SHALL clear the Session_Cookie
3. WHEN a user clicks the logout button, THE System SHALL redirect the user to the Login_Page
4. WHEN the Session_Cookie is cleared, THE Middleware SHALL treat subsequent requests as unauthenticated

### Requirement 6: Rate Limiting on Login

**User Story:** As the system, I want to limit login attempts, so that brute-force attacks are mitigated.

#### Acceptance Criteria

1. THE Login_Service SHALL track login attempts per IP address
2. WHEN an IP address exceeds 5 failed login attempts within 15 minutes, THE Login_Service SHALL return a 429 response with the message "Too many login attempts. Please try again later."
3. WHEN a successful login occurs, THE Login_Service SHALL reset the attempt counter for that IP address
4. THE Login_Service SHALL use an in-memory rate limiter consistent with the existing Admin_Auth rate limiting pattern

### Requirement 7: Admin Auth Isolation

**User Story:** As an administrator, I want the admin authentication system to remain unchanged, so that admin access is not affected by the new subscription login.

#### Acceptance Criteria

1. THE System SHALL preserve the existing Admin_Auth routes at `/api/admin/login`, `/api/admin/logout`, `/api/admin/verify`, and `/api/admin/refresh`
2. THE System SHALL preserve the existing Admin_Auth email/password with bcrypt verification
3. THE System SHALL preserve the existing Admin_Auth JWT token issuance and validation
4. THE System SHALL NOT modify the admin login page at `/admin/login`
5. THE Login_Service for customer authentication SHALL use a separate API route prefix from Admin_Auth

### Requirement 8: Environment Configuration

**User Story:** As a developer, I want clear environment variable requirements, so that the Appstle integration can be configured correctly on Railway.

#### Acceptance Criteria

1. THE System SHALL require APPSTLE_API_URL environment variable for the Appstle API base URL
2. THE System SHALL require APPSTLE_API_KEY environment variable for authenticating with the Appstle API
3. THE System SHALL require SUBSCRIPTION_SIGNUP_URL environment variable for the subscription purchase page URL
4. THE System SHALL use the existing JWT_SECRET_KEY environment variable for token signing
5. WHEN a required Appstle environment variable is missing, THE System SHALL log a warning at startup and disable subscription verification
6. WHEN subscription verification is disabled, THE Login_Service SHALL return a 503 response for all login attempts

### Requirement 9: Error Handling and Resilience

**User Story:** As the system, I want to handle Appstle API failures gracefully, so that users receive clear feedback when issues occur.

#### Acceptance Criteria

1. WHEN the Appstle_API returns a non-200 response, THE Login_Service SHALL return a 503 response with a user-friendly error message
2. WHEN the Appstle_API request times out after 10 seconds, THE Login_Service SHALL return a 503 response with the message "Subscription service temporarily unavailable"
3. WHEN the Appstle_API returns malformed data, THE Login_Service SHALL log the error and return a 500 response
4. THE Login_Service SHALL log all Appstle_API request outcomes (success, failure, timeout) with timestamp and user email
5. IF the Appstle_API returns an unexpected subscription status, THEN THE Login_Service SHALL treat the status as inactive and deny access

### Requirement 10: Frontend Subscription Redirect

**User Story:** As a user without a subscription, I want to be directed to purchase a subscription, so that I can gain access to the chatbot.

#### Acceptance Criteria

1. WHEN the Login_Service returns a subscription-required response, THE Login_Page SHALL display a message explaining that an active subscription is needed
2. WHEN the Login_Page displays the subscription-required message, THE Login_Page SHALL include a button labeled "Subscribe Now" linking to the Signup_Page
3. THE Login_Page SHALL display different messages based on subscription status: "Your subscription has expired" for expired, "Your subscription is paused" for paused, "Your subscription has been cancelled" for cancelled, and "No subscription found" for missing subscriptions
4. WHEN the user has no subscription, THE Login_Page SHALL display the Signup_Page URL configured via the SUBSCRIPTION_SIGNUP_URL environment variable
