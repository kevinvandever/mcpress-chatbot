# Requirements Document

## Introduction

This feature modifies the Appstle subscription authentication logic in the MC Press Chatbot backend. Currently, the system determines subscription access by checking the subscription contract status field (ACTIVE, PAUSED, CANCELLED, EXPIRED) from the Appstle API response. The new approach replaces this with a customer-tag-based strategy: the system reads customer tags from the Appstle API response to determine whether a subscription is active, paused, or inactive. This decouples access decisions from contract status and allows tag-driven control over subscription state.

## Glossary

- **Auth_Service**: The `SubscriptionAuthService` class in `backend/subscription_auth.py` responsible for verifying customer subscriptions and issuing JWT session tokens.
- **Appstle_API**: The external Appstle REST API endpoint at `/api/external/v2/subscription-contract-details/customers` that returns customer and subscription data.
- **Customer_Tag**: A string label attached to a customer record in the Appstle API response (e.g. within a `tags` or `customerTags` field) that indicates subscription state.
- **Active_Tag**: A customer tag whose value indicates the customer has an active subscription (e.g. `"active-subscriber"` or a configured tag pattern).
- **Paused_Tag**: A customer tag whose value indicates the customer's subscription is paused (e.g. `"paused-subscriber"` or a configured tag pattern).
- **Inactive_Tag**: A customer tag whose value indicates the customer's subscription is inactive or cancelled (e.g. `"inactive-subscriber"` or a configured tag pattern).
- **Tag_Parser**: The logic within Auth_Service that extracts and interprets Customer_Tags from the Appstle_API response to determine subscription state.
- **Subscription_Status**: The derived state (`active`, `paused`, `inactive`, `not_found`) determined by the Tag_Parser from Customer_Tags.

## Requirements

### Requirement 1: Parse Customer Tags from Appstle API Response

**User Story:** As a system administrator, I want the Auth_Service to read customer tags from the Appstle API response, so that subscription state is determined by tags rather than contract status fields.

#### Acceptance Criteria

1. WHEN the Appstle_API returns a customer record, THE Tag_Parser SHALL extract all Customer_Tags from the response.
2. WHEN the Appstle_API returns a customer record with no tags field or an empty tags list, THE Tag_Parser SHALL treat the customer as having no subscription tags.
3. THE Tag_Parser SHALL perform case-insensitive matching when comparing Customer_Tags against known tag patterns.
4. IF the Appstle_API response contains a malformed or unexpected tags structure, THEN THE Tag_Parser SHALL log a warning and treat the customer as having no subscription tags.

### Requirement 2: Determine Subscription Status from Customer Tags

**User Story:** As a system administrator, I want the Auth_Service to derive subscription status from customer tags, so that access control is tag-driven.

#### Acceptance Criteria

1. WHEN the Tag_Parser finds an Active_Tag among the Customer_Tags, THE Auth_Service SHALL set the Subscription_Status to `active` and mark the subscription as valid.
2. WHEN the Tag_Parser finds a Paused_Tag among the Customer_Tags and no Active_Tag is present, THE Auth_Service SHALL set the Subscription_Status to `paused` and mark the subscription as invalid.
3. WHEN the Tag_Parser finds an Inactive_Tag among the Customer_Tags and no Active_Tag is present, THE Auth_Service SHALL set the Subscription_Status to `inactive` and mark the subscription as invalid.
4. WHEN the Tag_Parser finds no recognized tags among the Customer_Tags, THE Auth_Service SHALL set the Subscription_Status to `not_found` and mark the subscription as invalid.
5. WHEN multiple conflicting tags are present (e.g. both Active_Tag and Paused_Tag), THE Auth_Service SHALL prioritize the Active_Tag and set the Subscription_Status to `active`.

### Requirement 3: Configure Tag Patterns via Environment Variables

**User Story:** As a system administrator, I want to configure which customer tags map to active, paused, and inactive states, so that tag mappings can be changed without code modifications.

#### Acceptance Criteria

1. THE Auth_Service SHALL read tag patterns from environment variables: `SUBSCRIPTION_TAG_ACTIVE`, `SUBSCRIPTION_TAG_PAUSED`, and `SUBSCRIPTION_TAG_INACTIVE`.
2. WHEN an environment variable for a tag pattern is not set, THE Auth_Service SHALL use a sensible default value (e.g. `"active-subscriber"`, `"paused-subscriber"`, `"inactive-subscriber"`).
3. THE Auth_Service SHALL support comma-separated values in each environment variable to allow multiple tag patterns per status (e.g. `SUBSCRIPTION_TAG_ACTIVE=active-subscriber,active-member`).
4. IF an environment variable contains only whitespace or empty strings after splitting, THEN THE Auth_Service SHALL fall back to the default tag pattern for that status.

### Requirement 4: Replace Contract Status Logic in verify_subscription

**User Story:** As a developer, I want the `verify_subscription` method to use customer tags instead of contract status fields, so that the authentication flow uses the new tag-based approach.

#### Acceptance Criteria

1. THE Auth_Service `verify_subscription` method SHALL call the Appstle_API and pass the response to the Tag_Parser instead of the contract-status parser.
2. THE Auth_Service SHALL return an `AppstleSubscriptionResponse` with `is_valid=True` only when the Subscription_Status derived from Customer_Tags is `active`.
3. WHEN the Subscription_Status is `paused`, THE Auth_Service SHALL return an `AppstleSubscriptionResponse` with `is_valid=False` and `subscription_status="PAUSED"`.
4. WHEN the Subscription_Status is `inactive`, THE Auth_Service SHALL return an `AppstleSubscriptionResponse` with `is_valid=False` and `subscription_status="CANCELLED"`.
5. WHEN the Subscription_Status is `not_found`, THE Auth_Service SHALL return an `AppstleSubscriptionResponse` with `is_valid=False` and `subscription_status=None`.

### Requirement 5: Maintain Existing Login and Refresh Behavior

**User Story:** As a customer, I want the login and token refresh flows to continue working with the same user-facing behavior, so that the tag-based change is transparent to me.

#### Acceptance Criteria

1. WHEN a customer with an Active_Tag logs in with valid credentials, THE Auth_Service SHALL issue a JWT session token and return a success response with `subscription_status="active"`.
2. WHEN a customer with a Paused_Tag logs in, THE Auth_Service SHALL deny login and return the message "Your subscription is paused".
3. WHEN a customer with an Inactive_Tag logs in, THE Auth_Service SHALL deny login and return the message "Your subscription has been cancelled".
4. WHEN a customer with no recognized tags logs in, THE Auth_Service SHALL deny login and return the message "No subscription found".
5. WHEN a token refresh is requested and the customer no longer has an Active_Tag, THE Auth_Service SHALL deny the refresh with a 403 status code.

### Requirement 6: Logging for Tag-Based Authentication

**User Story:** As a system administrator, I want the Auth_Service to log tag-based authentication decisions, so that I can troubleshoot access issues.

#### Acceptance Criteria

1. WHEN the Tag_Parser extracts Customer_Tags from a response, THE Auth_Service SHALL log the extracted tags at INFO level.
2. WHEN the Tag_Parser determines a Subscription_Status, THE Auth_Service SHALL log the email, derived status, and matched tag at INFO level.
3. IF the Tag_Parser encounters an unexpected tags structure, THEN THE Auth_Service SHALL log the structure details at WARNING level.
