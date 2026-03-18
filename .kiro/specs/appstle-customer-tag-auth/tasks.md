# Implementation Plan: Appstle Customer Tag Authentication

## Overview

Replace the contract-status-based subscription verification in `backend/subscription_auth.py` with a customer-tag-based approach. Add `TagConfig` dataclass, tag extraction, status derivation, and environment variable configuration. Remove the old `_parse_subscription_response` and `_extract_contracts` methods. Update `.env.example` with new env vars. Write property-based and unit tests.

## Tasks

- [x] 1. Add TagConfig and load_tag_config to subscription_auth.py
  - [x] 1.1 Add `TagConfig` frozen dataclass with `active_patterns`, `paused_patterns`, `inactive_patterns` fields and default values
    - Add `from dataclasses import dataclass, field` import
    - Place `TagConfig` after the existing model definitions
    - _Requirements: 3.1, 3.2_

  - [x] 1.2 Add `load_tag_config()` function that reads `SUBSCRIPTION_TAG_ACTIVE`, `SUBSCRIPTION_TAG_PAUSED`, `SUBSCRIPTION_TAG_INACTIVE` from environment
    - Parse comma-separated values, strip whitespace, lowercase all patterns
    - Fall back to defaults when env var is unset or contains only whitespace
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 1.3 Write property test for environment variable config round-trip
    - **Property 4: Environment variable config round-trip**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [x] 2. Add tag extraction and status derivation functions
  - [x] 2.1 Add `_extract_customer_tags(customer: dict) -> list[str]` method to `SubscriptionAuthService`
    - Check `customerTags` then `tags` fields
    - Handle list-of-strings and list-of-dicts (with `name`/`value`/`tag` keys)
    - Return empty list on missing, empty, or malformed data; log warning on unexpected structure
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ]* 2.2 Write property test for tag extraction
    - **Property 1: Tag extraction preserves all tags**
    - **Validates: Requirements 1.1, 1.2, 1.4**

  - [x] 2.3 Add `_derive_status_from_tags(tags: list[str], config: TagConfig) -> str` as a module-level pure function
    - Case-insensitive matching: lowercase all tags before comparison
    - Priority order: active > paused > inactive > not_found
    - _Requirements: 1.3, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.4 Write property test for case-insensitive tag matching
    - **Property 2: Case-insensitive tag matching**
    - **Validates: Requirements 1.3**

  - [ ]* 2.5 Write property test for status derivation priority
    - **Property 3: Status derivation priority**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

- [x] 3. Checkpoint - Verify core functions
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Replace parsing logic and wire everything together
  - [x] 4.1 Add `_parse_tags_response(data, email) -> AppstleSubscriptionResponse` method to `SubscriptionAuthService`
    - Reuse existing customer-list normalization logic (list, paginated dict, single-customer dict)
    - For each customer, call `_extract_customer_tags` then `_derive_status_from_tags`
    - Map derived status to `AppstleSubscriptionResponse`: active→(True, "ACTIVE"), paused→(False, "PAUSED"), inactive→(False, "CANCELLED"), not_found→(False, None)
    - Log extracted tags and derived status at INFO level
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.1, 6.2_

  - [ ]* 4.2 Write property test for status-to-response mapping
    - **Property 5: Status-to-response mapping**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

  - [x] 4.3 Update `SubscriptionAuthService.__init__` to load tag config
    - Add `self.tag_config = load_tag_config()` after existing config
    - Log loaded tag patterns at INFO level
    - _Requirements: 3.1, 6.1_

  - [x] 4.4 Update `verify_subscription` to call `_parse_tags_response` instead of `_parse_subscription_response`
    - Replace `self._parse_subscription_response(data, email)` with `self._parse_tags_response(data, email)`
    - _Requirements: 4.1_

  - [x] 4.5 Remove `_parse_subscription_response` and `_extract_contracts` methods
    - Delete both methods from `SubscriptionAuthService`
    - _Requirements: 4.1_

- [x] 5. Update environment configuration
  - [x] 5.1 Add new environment variables to `.env.example`
    - Add `SUBSCRIPTION_TAG_ACTIVE`, `SUBSCRIPTION_TAG_PAUSED`, `SUBSCRIPTION_TAG_INACTIVE` with example values and comments
    - _Requirements: 3.1_

- [ ] 6. Write unit tests
  - [ ]* 6.1 Write unit tests in `backend/test_tag_auth_unit.py`
    - Test tag extraction from real-shaped Appstle API response
    - Test default config values when no env vars are set
    - Test customer with both `customerTags` and `tags` fields (first one wins)
    - Test empty string tags in the list are preserved correctly
    - Test malformed tags structure logs warning and returns empty list
    - Test `_parse_tags_response` with various API response shapes
    - Test login flow with mocked Appstle API returning tagged customer
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.2, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The only production code file being modified is `backend/subscription_auth.py`
- The routes file (`subscription_auth_routes.py`) does NOT need changes
- Property tests use Hypothesis and go in `backend/test_tag_auth_properties.py`
- Unit tests go in `backend/test_tag_auth_unit.py`
- All testing must be deployed to Railway staging before verification per project workflow
