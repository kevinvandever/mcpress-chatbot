# Project Structure

## Repository Layout

```
mcpress-chatbot/
├── backend/              # FastAPI backend application
├── frontend/             # Next.js frontend application
├── docs/                 # Project documentation
├── migration_scripts/    # Database migration utilities
├── scripts_backup/       # Deployment and utility scripts
└── [root scripts]        # Various utility and test scripts
```

## Backend Structure (`backend/`)

### Core Application Files
- `main.py` - FastAPI app entry point, API routes
- `config.py` - Environment configuration and constants
- `chat_handler.py` - Chat orchestration and OpenAI integration
- `vector_store_postgres.py` - PostgreSQL/pgvector integration
- `pdf_processor_full.py` - PDF extraction and chunking pipeline

### Feature Modules
- `auth.py`, `auth_routes.py` - Authentication system
- `author_routes.py`, `author_service.py` - Author management
- `document_author_routes.py`, `document_author_service.py` - Document-author relationships
- `conversation_routes.py`, `conversation_service.py` - Conversation history
- `export_routes.py`, `export_service.py` - Export functionality
- `processing_routes.py`, `processing_integration.py` - Document processing pipeline
- `code_upload_*.py` - Code file upload system

### Data Models
- `conversation_models.py` - Conversation data structures
- `processing_models.py` - Processing pipeline models
- `export_models.py` - Export data structures

### Utilities
- `category_mapper.py` - Book categorization logic
- `book_manager.py` - Document management
- `backup_manager.py` - Backup operations
- `markdown_generator.py`, `pdf_generator.py` - Export generators

### Database Migrations
- `migrations/` - SQL migration files
  - `001_processing_pipeline.sql` - Processing system
  - `002_code_upload_system.sql` - Code upload feature
  - `003_multi_author_support.sql` - Multi-author metadata
- `run_migration_*.py` - Migration execution scripts
- `data_migration_*.py` - Data migration logic

### Legacy/Variant Files
Multiple versions of processors exist (technical debt):
- `pdf_processor_*.py` - Various PDF processing implementations
- `vector_store_*.py` - Different vector store backends
- `admin_documents*.py` - Admin interface variants

## Frontend Structure (`frontend/`)

### Application Routes (`app/`)
```
app/
├── page.tsx                    # Home/chat page
├── layout.tsx                  # Root layout
├── globals.css                 # Global styles
├── admin/                      # Admin section
│   ├── dashboard/page.tsx      # Admin dashboard
│   ├── documents/page.tsx      # Document management
│   ├── upload/page.tsx         # Upload interface
│   └── login/page.tsx          # Admin login
├── history/page.tsx            # Conversation history
├── login/page.tsx              # User login
└── code-analysis/              # Code analysis features
    └── upload/page.tsx
```

### Components (`components/`)
- `ChatInterface.tsx` - Main chat UI component
- `CompactSources.tsx` - Source attribution display
- `FileUpload.tsx` - PDF upload interface
- `BatchUpload.tsx` - Bulk upload interface
- `DocumentList.tsx` - Document management list
- `ConversationList.tsx`, `ConversationCard.tsx` - History UI
- `ExportModal.tsx` - Export dialog
- `MetadataEditDialog.tsx` - Metadata editing
- `AuthorPromptDialog.tsx` - Author input dialog

### Design System (`components/design-system/`)
Reusable UI components with tests:
- `Button/` - Button component
- `Input/` - Input component
- `Card/` - Card component
- `Modal/` - Modal dialog
- `Alert/` - Alert component
- `Badge/` - Badge component
- `Loading/` - Loading states (Spinner, Skeleton, ProgressBar)

### Services (`services/`)
- `conversationService.ts` - Conversation API client
- `exportService.ts` - Export API client

### Configuration
- `config/api.ts` - API endpoint configuration
- `config/axios.ts` - Axios instance setup
- `next.config.js` - Next.js configuration
- `tailwind.config.ts` - Tailwind CSS configuration

## Documentation Structure (`docs/`)

### Architecture
- `architecture.md` - System architecture overview
- `architecture/` - Detailed architecture docs
  - `tech-stack.md` - Technology decisions
  - `source-tree.md` - Code organization
  - `coding-standards.md` - Code conventions

### Product Requirements
- `prd/` - Product requirements documents
  - `index.md` - PRD overview
  - `phase-*.md` - Implementation phases
  - `stories/` - User stories and features

### Development
- `dev/` - Development session notes
- `qa/` - QA test plans and assessments

## Root-Level Files

### Configuration
- `requirements.txt` - Python dependencies
- `package.json` - Node.js workspace configuration
- `docker-compose.yml` - Local development setup
- `.env.example` - Environment variable template

### Deployment
- `Procfile` - Railway deployment configuration
- `runtime.txt` - Python version specification
- `netlify.toml` - Netlify deployment settings

### Utility Scripts
Many utility scripts exist at root level (technical debt):
- `check_*.py` - Database and system checks
- `upload_*.py` - Various upload utilities
- `migrate_*.py` - Migration scripts
- `test_*.py` - Test scripts

## Naming Conventions

### Python Files
- Snake_case: `pdf_processor_full.py`
- Descriptive names: `conversation_service.py`
- Test prefix: `test_*.py`

### TypeScript/React Files
- PascalCase for components: `ChatInterface.tsx`
- camelCase for utilities: `conversationService.ts`
- Kebab-case for routes: `code-analysis/upload/`

### Database
- Snake_case tables: `documents`, `conversation_messages`
- Plural table names: `documents`, `authors`
- Singular model names: `Document`, `Author`

## Import Patterns

### Backend
```python
# Railway deployment (preferred)
from backend.chat_handler import ChatHandler
from backend.vector_store_postgres import PostgresVectorStore

# Local development (also works)
from chat_handler import ChatHandler
```

### Frontend
```typescript
// Absolute imports from root
import { ChatInterface } from '@/components/ChatInterface'
import { conversationService } from '@/services/conversationService'
```

## Key Directories to Avoid Modifying

- `__pycache__/` - Python bytecode cache
- `.pytest_cache/` - Pytest cache
- `.git/` - Git repository data
- `node_modules/` - Node.js dependencies (not in repo)
- `frontend/dist/` - Build output (not in repo)
