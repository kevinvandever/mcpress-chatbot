# Requirements Document: ChatMaster Password Authentication

## Introduction

This specification adds a local password authentication layer to the existing Appstle subscription-based login for the MC ChatMaster application. Currently, users log in with email only, and the backend verifies their subscription via the Appstle API. This feature adds a ChatMaster-level password that users must create and enter alongside their email. The login flow becomes: verify email + password locally → verify subscription via Appstle API → issue JWT. The existing Appstle email subscription verification remains completely unchanged.

**SCOPE NOTE**: This specification covers **customer password authentication only**. The existing admin authentication system (`/api/admin/*` routes) and the Appstle subscription verification logic are **out of scope** and remain completely unchanged.

## Glossary

- **Auth_Service**: Backend FastAPI service that handles customer login, password verification, and token issuance
- **Password_Store**: PostgreSQL table storing customer email-password records (hashed with bcrypt)
- **Login_Page**: Frontend page where users enter email and password to access the chatbot
- **Password_Hasher**: Component that hashes and verifies passwords using bcrypt with a work factor of 12
- **Password_Rules**: The set of complexity requirements a password must satisfy to be accepted
- **Reset_Token**: A cryptographically secure, time-limited token used to authorize a password reset
- **Reset_Page**: Frontend page where users set a new password using a valid Reset_Token
- **Email_Service**: Backend component that sends password reset emails to customers
- **Appstle_API**: The external Appstle subscription management API used to verify active subscriptions (unchanged)
- **Auth_Token**: JWT issued by the backend upon successful password verification and subscription confirmation
- **Session_Cookie**: HTTP-only secure cookie storing the Auth_Token for authenticated sessions
- **Middleware**: Next.js middleware that checks authentication state and redirects unauthenticated users
- **Admin_Auth**: The existing separate admin authentication system (unchanged by this spec)
- **Chat_Interface**: The main chatbot page accessible only to authenticated users

## Requirements

### Requirement 1: Customer Password Storage

**User Story:** As the system, I want to store customer passwords securely in the database, so that users can authenticate with email and password at the ChatMaster level.

#### Acceptance Criteria

1. THE Password_Store SHALL store customer records with email (unique), password hash, created_at, and updated_at fields
2. THE Password_Hasher SHALL hash passwords using bcrypt with a work factor of 12
3. THE Password_Store SHALL enforce a unique constraint on the email column
4. THE Auth_Service SHALL use the existing Railway PostgreSQL database for the Password_Store
5. WHEN a customer record is created or updated, THE Password_Store SHALL set the updated_at timestamp to the current UTC time

### Requirement 2: Password Creation Rules

**User Story:** As a user, I want clear password requirements, so that I create a strong password that protects my account.

#### Acceptance Criteria

1. THE Auth_Service SHALL require passwords to be at least 8 characters long
2. THE Auth_Service SHALL require passwords to contain at least one uppercase letter
3. THE Auth_Service SHALL require passwords to contain at least one lowercase letter
4. THE Auth_Service SHALL require passwords to contain at least one digit
5. THE Auth_Service SHALL require passwords to contain at least one special character from the set: !@#$%^&*()_+-=[]{}|;:,.<>?
6. WHEN a password does not meet any single rule, THE Auth_Service SHALL return a specific error message identifying the failed rule
7. THE Login_Page SHALL display the password requirements to the user during account creation

### Requirement 3: Account Creation Flow

**User Story:** As a new user with an active Appstle subscription, I want to create a ChatMaster password, so that I can securely access the chatbot.

#### Acceptance Criteria

1. WHEN a user submits email and password to the login endpoint and no Password_Store record exists for that email, THE Auth_Service SHALL verify the email against the Appstle_API first
2. WHEN the Appstle_API confirms an active subscription and no Password_Store record exists, THE Auth_Service SHALL create a new Password_Store record with the provided email and hashed password
3. WHEN the Appstle_API confirms an active subscription and a new Password_Store record is created, THE Auth_Service SHALL issue an Auth_Token and return a success response
4. WHEN the Appstle_API does not confirm an active subscription, THE Auth_Service SHALL deny account creation and return the subscription status with a redirect URL to the signup page
5. THE Auth_Service SHALL validate the password against Password_Rules before creating the account
6. WHEN the password does not meet Password_Rules during account creation, THE Auth_Service SHALL return a 400 response with the specific validation error

### Requirement 4: Login with Email and Password

**User Story:** As a user, I want to log in with my email and password, so that the system verifies my identity locally and then confirms my subscription.

#### Acceptance Criteria

1. THE Login_Page SHALL present email and password input fields to the user
2. WHEN a user submits email and password, THE Auth_Service SHALL first verify the password against the Password_Store record for that email
3. WHEN the password matches the stored hash, THE Auth_Service SHALL then verify the email against the Appstle_API to confirm an active subscription
4. WHEN both password verification and Appstle subscription verification succeed, THE Auth_Service SHALL issue an Auth_Token and return a success response
5. WHEN the password does not match the stored hash, THE Auth_Service SHALL return a 401 response with the message "Invalid email or password"
6. WHEN no Password_Store record exists for the email and the Appstle_API confirms an active subscription, THE Auth_Service SHALL prompt the user to create a password (first-time setup)
7. WHEN the Appstle_API does not confirm an active subscription (after successful password verification), THE Auth_Service SHALL return a 403 response with the subscription status and redirect URL
8. WHEN the Appstle_API is unreachable or returns an error, THE Auth_Service SHALL return a 503 response with the message "Subscription service temporarily unavailable"

### Requirement 5: Login Page UI Updates

**User Story:** As a user, I want a clear login interface with both email and password fields, so that I can authenticate to the chatbot.

#### Acceptance Criteria

1. THE Login_Page SHALL display an email input field and a password input field
2. THE Login_Page SHALL display a "Forgot Password?" link below the password field
3. THE Login_Page SHALL display loading state while authentication is in progress
4. THE Login_Page SHALL display error messages returned by the Auth_Service
5. WHEN the Auth_Service indicates first-time setup is needed, THE Login_Page SHALL display the password requirements and a "Create Password" button
6. WHEN a subscription issue is returned, THE Login_Page SHALL display the status-specific message and a "Subscribe Now" link
7. THE Login_Page SHALL preserve the existing visual design and branding (MC ChatMaster logo, gradient background, blue theme)

### Requirement 6: Forgot Password - Request Reset

**User Story:** As a user who has forgotten my password, I want to request a password reset, so that I can regain access to my account.

#### Acceptance Criteria

1. WHEN a user submits an email to the forgot-password endpoint, THE Auth_Service SHALL generate a cryptographically secure Reset_Token
2. THE Auth_Service SHALL store the Reset_Token in the database with the associated email and an expiration time of 1 hour from creation
3. THE Auth_Service SHALL send an email to the provided address containing a link with the Reset_Token
4. WHEN the email does not exist in the Password_Store, THE Auth_Service SHALL return the same success response as when the email exists (to prevent email enumeration)
5. THE Auth_Service SHALL invalidate any previously issued Reset_Tokens for the same email when a new reset is requested
6. THE Auth_Service SHALL rate-limit forgot-password requests to 3 requests per email per hour

### Requirement 7: Forgot Password - Reset Execution

**User Story:** As a user with a valid reset link, I want to set a new password, so that I can access my account again.

#### Acceptance Criteria

1. WHEN a user submits a new password with a valid Reset_Token, THE Auth_Service SHALL validate the new password against Password_Rules
2. WHEN the new password meets Password_Rules and the Reset_Token is valid and not expired, THE Auth_Service SHALL update the Password_Store record with the new hashed password
3. WHEN the password is successfully reset, THE Auth_Service SHALL invalidate the used Reset_Token
4. WHEN the Reset_Token is expired (older than 1 hour), THE Auth_Service SHALL return a 400 response with the message "Reset link has expired. Please request a new one."
5. WHEN the Reset_Token is invalid or already used, THE Auth_Service SHALL return a 400 response with the message "Invalid reset link. Please request a new one."
6. THE Reset_Page SHALL display the password requirements and a form for entering the new password
7. THE Reset_Page SHALL display a confirmation message upon successful password reset with a link to the Login_Page

### Requirement 8: Password Reset Email Delivery

**User Story:** As the system, I want to send password reset emails reliably, so that users can recover their accounts.

#### Acceptance Criteria

1. THE Email_Service SHALL send password reset emails using a configurable SMTP provider or transactional email API
2. THE Email_Service SHALL include the reset link in the format: {FRONTEND_URL}/reset-password?token={Reset_Token}
3. THE Email_Service SHALL include the MC ChatMaster branding in the email template
4. THE Email_Service SHALL set the email subject to "MC ChatMaster - Password Reset"
5. WHEN the Email_Service fails to send an email, THE Auth_Service SHALL log the error and return a 500 response with the message "Unable to send reset email. Please try again later."
6. THE System SHALL require EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_FROM_ADDRESS, and EMAIL_SMTP_PASSWORD environment variables for email delivery configuration

### Requirement 9: Token and Session Management

**User Story:** As the system, I want to maintain the existing JWT session management, so that authenticated sessions continue to work as before.

#### Acceptance Criteria

1. THE Auth_Service SHALL continue to issue Auth_Tokens with the same claims structure: sub (email), subscription_status, subscription_expires_at, iat, and exp
2. THE Auth_Service SHALL continue to set Auth_Token expiration to 1 hour from issuance
3. THE Auth_Service SHALL continue to store the Auth_Token in an HTTP-only secure cookie with SameSite=Lax
4. THE Auth_Service SHALL continue to support the existing refresh flow: verify token (with 5-minute grace window) → re-verify subscription via Appstle_API → issue new token
5. THE Auth_Service SHALL NOT require password re-entry during token refresh (only subscription re-verification)

### Requirement 10: Rate Limiting

**User Story:** As the system, I want to limit login and password reset attempts, so that brute-force attacks are mitigated.

#### Acceptance Criteria

1. THE Auth_Service SHALL continue to enforce the existing rate limit of 5 failed login attempts per IP address per 15 minutes
2. WHEN an IP address exceeds 5 failed login attempts within 15 minutes, THE Auth_Service SHALL return a 429 response with the message "Too many login attempts. Please try again later."
3. WHEN a successful login occurs, THE Auth_Service SHALL reset the login attempt counter for that IP address
4. THE Auth_Service SHALL enforce a rate limit of 3 forgot-password requests per email address per hour
5. WHEN an email address exceeds 3 forgot-password requests within 1 hour, THE Auth_Service SHALL return a 429 response with the message "Too many reset requests. Please try again later."

### Requirement 11: Admin Auth Isolation

**User Story:** As an administrator, I want the admin authentication system to remain unchanged, so that admin access is not affected by the new password feature.

#### Acceptance Criteria

1. THE System SHALL preserve the existing Admin_Auth routes at `/api/admin/login`, `/api/admin/logout`, `/api/admin/verify`, and `/api/admin/refresh`
2. THE System SHALL preserve the existing Admin_Auth email/password with bcrypt verification
3. THE System SHALL NOT modify the admin login page at `/admin/login`
4. THE Auth_Service for customer authentication SHALL continue to use the `/api/auth/*` route prefix, separate from Admin_Auth

### Requirement 12: Database Migration

**User Story:** As a developer, I want a database migration that creates the customer password table, so that the feature can be deployed safely.

#### Acceptance Criteria

1. THE System SHALL provide a SQL migration file that creates the customer_passwords table with columns: id (serial primary key), email (varchar, unique, not null), password_hash (varchar, not null), created_at (timestamp, default current_timestamp), updated_at (timestamp, default current_timestamp)
2. THE System SHALL provide a SQL migration file that creates the password_reset_tokens table with columns: id (serial primary key), email (varchar, not null), token (varchar, unique, not null), expires_at (timestamp, not null), used (boolean, default false), created_at (timestamp, default current_timestamp)
3. THE migration SHALL be idempotent (safe to run multiple times)
4. THE migration SHALL follow the existing migration naming convention (e.g., 004_customer_password_auth.sql)

### Requirement 13: Environment Configuration

**User Story:** As a developer, I want clear environment variable requirements, so that the password auth and email features can be configured correctly on Railway.

#### Acceptance Criteria

1. THE System SHALL continue to use the existing APPSTLE_API_URL, APPSTLE_API_KEY, SUBSCRIPTION_SIGNUP_URL, and JWT_SECRET_KEY environment variables
2. THE System SHALL require EMAIL_SMTP_HOST environment variable for the SMTP server hostname
3. THE System SHALL require EMAIL_SMTP_PORT environment variable for the SMTP server port
4. THE System SHALL require EMAIL_FROM_ADDRESS environment variable for the sender email address
5. THE System SHALL require EMAIL_SMTP_PASSWORD environment variable for SMTP authentication
6. THE System SHALL require FRONTEND_URL environment variable for constructing password reset links
7. WHEN a required email environment variable is missing, THE System SHALL log a warning at startup and disable the forgot-password feature
8. WHEN the forgot-password feature is disabled, THE Auth_Service SHALL return a 503 response for forgot-password requests with the message "Password reset is temporarily unavailable"
