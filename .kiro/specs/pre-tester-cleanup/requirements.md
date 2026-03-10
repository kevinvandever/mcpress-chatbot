# Requirements Document

## Introduction

The MC Press Chatbot is about to be shared with first testers. A comprehensive audit identified critical security vulnerabilities, dead code, file clutter, and configuration gaps that must be resolved before external users interact with the system. This spec covers the cleanup work needed to make the production environment safe and presentable for testers.

## Glossary

- **Backend**: The FastAPI Python application deployed on Railway, entry point `backend/main.py`
- **Frontend**: The Next.js TypeScript application deployed on Netlify under `frontend/`
- **Dangerous_Endpoint**: An API route that can destroy or overwrite production data without authentication
- **Debug_Endpoint**: An API route that exposes internal system information (database structure, environment variables, connection details)
- **Migration_Endpoint**: An API route created for one-time database migrations that have already been completed
- **Dead_File**: A file that is not imported, referenced, or executed by the running application
- **Root_Scripts**: Python and data files at the repository root level, not part of the deployed application
- **Gitignore**: The `.gitignore` configuration file controlling which files are excluded from version control

## Requirements

### Requirement 1: Remove Dangerous Data-Destructive Endpoints

**User Story:** As a product owner, I want data-destructive endpoints removed from production, so that testers cannot accidentally or maliciously wipe the database.

#### Acceptance Criteria

1. WHEN the Backend is deployed, THE Backend SHALL NOT expose a `POST /reset` endpoint
2. WHEN the Backend is deployed, THE Backend SHALL NOT expose a `POST /bulk-upload` endpoint that triggers uncontrolled subprocess execution
3. WHEN the Backend is deployed, THE Backend SHALL NOT expose a `POST /backup/restore` endpoint without authentication
4. WHEN a client sends a request to any removed endpoint path, THE Backend SHALL return a 404 status code

### Requirement 2: Remove Debug Endpoints

**User Story:** As a product owner, I want debug endpoints removed from production, so that internal system details are not leaked to testers or attackers.

#### Acceptance Criteria

1. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /diag/db-test` endpoint
2. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /test-books-table` endpoint
3. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /api/debug-enrichment-env` endpoint
4. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /api/debug-enrichment-connection` endpoint
5. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /api/debug-enrichment-test/{filename}` endpoint
6. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /api/debug-enrichment-sample-books` endpoint
7. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /upload-debug` endpoint
8. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `GET /upload-dashboard` endpoint

### Requirement 3: Remove Deprecated Migration Endpoints

**User Story:** As a product owner, I want completed migration endpoints removed, so that testers do not accidentally re-run database migrations.

#### Acceptance Criteria

1. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `POST /api/run-story4-migration` endpoint
2. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `POST /api/run-story12-migration` endpoint
3. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `POST /api/run-migration-simple` endpoint
4. WHEN the Backend is deployed, THE Backend SHALL NOT expose the `POST /api/OLD_run_story4_migration_DO_NOT_USE` endpoint

### Requirement 4: Remove Dead Backend Files

**User Story:** As a developer, I want unused backend file variants removed, so that the codebase is clear about which files are active and maintainable.

#### Acceptance Criteria

1. THE Backend directory SHALL contain only one `main.py` file (the active entry point), with all variant `main*.py` files removed
2. THE Backend directory SHALL contain only `admin_documents_fixed.py` as the active admin documents module, with all other `admin_documents*.py` variants removed
3. THE Backend directory SHALL contain only `pdf_processor_full.py` as the active PDF processor, with all other `pdf_processor*.py` variants and `.backup` files removed
4. THE Backend directory SHALL contain only `vector_store_postgres.py` as the active vector store, with all other `vector_store*.py` variants removed
5. WHEN a dead backend file is removed, THE remaining application code SHALL continue to function without import errors

### Requirement 5: Remove Backend One-Off Test Scripts

**User Story:** As a developer, I want one-off test scripts removed from the backend directory, so that the backend contains only production application code.

#### Acceptance Criteria

1. THE Backend directory SHALL NOT contain ad-hoc test scripts (files matching `test_*.py` that are not part of a test suite)
2. THE Backend directory SHALL NOT contain one-off diagnostic or debug scripts that are not imported by the application
3. THE Backend directory SHALL NOT contain standalone markdown documentation files that duplicate information in `docs/`
4. THE Backend directory SHALL NOT contain completed migration runner scripts (files matching `run_migration_*.py`, `data_migration_*.py`, `pre_migration_*.py`) for migrations that have already been applied
5. WHEN backend scripts are removed, THE Backend application imports and startup SHALL remain unaffected

### Requirement 6: Clean Up Root-Level Scripts and Data Files

**User Story:** As a developer, I want root-level ad-hoc scripts and data files removed, so that the repository is navigable and professional for new contributors.

#### Acceptance Criteria

1. THE repository root SHALL NOT contain ad-hoc Python check scripts (files matching `check_*.py`)
2. THE repository root SHALL NOT contain ad-hoc Python test scripts (files matching `test_*.py`) that are not part of a formal test framework
3. THE repository root SHALL NOT contain ad-hoc Python debug scripts (files matching `debug_*.py`)
4. THE repository root SHALL NOT contain ad-hoc Python fix or execute scripts (files matching `fix_*.py`, `execute_*.py`)
5. THE repository root SHALL NOT contain ad-hoc Python upload scripts (files matching `upload_*.py`)
6. THE repository root SHALL NOT contain one-off migration scripts, SQL files, shell scripts, or data files (`.json`, `.csv`, `.sql`, `.txt`, `.pages`, `.numbers`, `.xlsm`) that are not required by the application
7. THE repository root SHALL NOT contain orphaned markdown summary or guide files that are not referenced by `README.md` or `docs/`
8. WHEN root-level files are removed, THE Backend and Frontend applications SHALL remain fully functional

### Requirement 7: Clean Up Frontend Dead Files

**User Story:** As a developer, I want dead frontend files removed, so that the frontend directory contains only active application code and configuration.

#### Acceptance Criteria

1. THE Frontend directory SHALL NOT contain `app/page_original.tsx`
2. THE Frontend directory SHALL NOT contain test artifact files (`test-api.html`, `test-components.md`, `test-document-list.md`, `test-search-formatting.md`)
3. THE Frontend directory SHALL NOT contain example component files (`DocumentTypeSelector.example.tsx`, `MultiAuthorInput.example.tsx`)
4. THE Frontend directory SHALL NOT contain `vercel.json` (the application deploys on Netlify)
5. THE repository root SHALL NOT contain orphaned frontend files (`frontend_admin_documents_fixed.tsx`, `frontend_author_button_enhancement.tsx`)
6. WHEN frontend dead files are removed, THE Frontend application SHALL build and deploy without errors

### Requirement 8: Update .gitignore

**User Story:** As a developer, I want the `.gitignore` updated to prevent data files and tool artifacts from being committed, so that future clutter is prevented.

#### Acceptance Criteria

1. THE Gitignore SHALL include patterns for JSON data files (`*.json`) in the root directory, excluding `package.json` and `package-lock.json`
2. THE Gitignore SHALL include patterns for CSV files (`*.csv`)
3. THE Gitignore SHALL include patterns for SQL files (`*.sql`)
4. THE Gitignore SHALL include patterns for the `.hypothesis/` directory
5. THE Gitignore SHALL include patterns for Apple file formats (`*.numbers`, `*.pages`)
6. THE Gitignore SHALL include patterns for Excel macro files (`*.xlsm`)
7. THE Gitignore SHALL include patterns for plain text data files (`*.txt`) in the root directory, excluding `requirements.txt` and `runtime.txt`

### Requirement 9: Fix Post-Login Page Flash

**User Story:** As a tester, I want a smooth transition after login without seeing a flash of unloaded content, so that the app feels polished and professional.

#### Acceptance Criteria

1. WHEN a user successfully logs in and is redirected to the home page, THE Frontend SHALL NOT display a brief flash of the home page layout before the loading state appears
2. WHEN the home page is loading after a login redirect, THE Frontend SHALL display a full-screen loading indicator until the initial data fetch (`checkDocuments` and `fetchUserInfo`) has completed or the component is ready to render meaningful content
3. WHEN the home page transitions from loading to ready, THE transition SHALL be seamless with no visible layout shift or content flash

### Requirement 10: Remove Empty Spec Directory

**User Story:** As a developer, I want empty spec directories removed, so that the specs folder only contains active or completed feature specs.

#### Acceptance Criteria

1. THE `.kiro/specs/` directory SHALL NOT contain the empty `shopify-subscription-auth/` directory
2. WHEN the empty directory is removed, THE remaining spec directories SHALL be unaffected
