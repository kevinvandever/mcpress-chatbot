# Story: Code Generation Interface

**Story ID**: STORY-008
**Epic**: EPIC-002 (Core Productivity Suite)
**Type**: New Feature
**Priority**: P0 (Critical)
**Points**: 8
**Sprint**: 6-7
**Status**: Ready for Development

## User Story

**As a** developer
**I want** to generate IBM i code snippets using AI
**So that** I can accelerate development with best-practice code

## Context

Code generation is a major productivity accelerator. By combining Claude AI with MC Press knowledge base, we can generate production-ready IBM i code that follows industry best practices. This feature transforms the chatbot from a learning tool into a development assistant.

## Current State

### Existing System
- **Chat Interface**: Text-based Q&A
- **AI Model**: Claude via Anthropic API
- **Knowledge Base**: MC Press books with code examples
- **Vector Store**: PostgreSQL with pgvector
- **Code Analysis**: STORY-007 provides code understanding

### Gap Analysis
- No structured code generation interface
- No template library
- No parameter input forms
- No syntax validation
- No code preview/editing
- No copy/download functionality
- No generation history

## Acceptance Criteria

### Core Generation Features
- [ ] Template selection UI (categorized templates)
- [ ] Parameter input forms (dynamic based on template)
- [ ] Real-time code preview with syntax highlighting
- [ ] Multiple language support (RPG, RPGLE, SQLRPGLE, CL, SQL)
- [ ] Format selection (fixed-format vs free-format RPG)
- [ ] MC Press best practices applied automatically
- [ ] Error handling patterns included
- [ ] Comments and documentation generated

### User Experience
- [ ] Copy-to-clipboard with one click
- [ ] Download as file (with proper extension)
- [ ] Edit generated code inline
- [ ] Regenerate with different parameters
- [ ] Save to template library (STORY-009)
- [ ] Share generated code
- [ ] Generation history (last 20 generations)

### Code Quality
- [ ] Syntax validation before display
- [ ] Compile-ready code (no syntax errors)
- [ ] Proper indentation and formatting
- [ ] Meaningful variable names
- [ ] Comprehensive comments
- [ ] Error handling included

## Technical Design

### Code Generation Flow

```
Select Template → Enter Parameters → Generate Code → Preview/Edit → Copy/Download/Save
                                          ↓
                                    Claude AI + RAG
                                          ↓
                                    MC Press Context
```

### Frontend Components

#### Code Generation Page (`/code-generation`)

```typescript
interface CodeTemplate {
  id: string
  name: string
  description: string
  category: TemplateCategory
  language: CodeLanguage
  parameters: TemplateParameter[]
  example: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  mc_press_reference?: string
}

interface TemplateParameter {
  name: string
  type: 'text' | 'number' | 'select' | 'boolean' | 'multiline'
  label: string
  description: string
  required: boolean
  default?: any
  options?: string[]  // For select type
  validation?: {
    pattern?: string
    min?: number
    max?: number
    message?: string
  }
}

interface GeneratedCode {
  id: string
  template_id: string
  language: CodeLanguage
  format: 'fixed' | 'free'
  code: string
  parameters: Record<string, any>
  created_at: Date
  mc_press_references: string[]
}

enum CodeLanguage {
  RPG = 'rpg',
  RPGLE = 'rpgle',
  SQLRPGLE = 'sqlrpgle',
  CL = 'cl',
  SQL = 'sql'
}

enum TemplateCategory {
  FILE_IO = 'file_io',
  DATABASE = 'database',
  API = 'api',
  UTILITY = 'utility',
  ERROR_HANDLING = 'error_handling',
  MODERNIZATION = 'modernization',
  WEB_SERVICES = 'web_services',
  DATA_STRUCTURES = 'data_structures'
}
```

#### Components
- `TemplateSelector` - Browse and search templates
- `ParameterForm` - Dynamic form based on template
- `CodePreview` - Syntax-highlighted preview with editing
- `CodeActions` - Copy, download, save, share buttons
- `GenerationHistory` - List of recent generations
- `TemplateCategoryBrowser` - Category-based navigation

### Template Library

```python
# Pre-built templates
BUILTIN_TEMPLATES = {
    "rpg_file_read": {
        "name": "Read Database File (RPG)",
        "description": "Read records from a database file with proper error handling",
        "category": "file_io",
        "language": "rpgle",
        "parameters": [
            {
                "name": "file_name",
                "type": "text",
                "label": "File Name",
                "required": True,
                "validation": {"pattern": "^[A-Z][A-Z0-9]{0,9}$"}
            },
            {
                "name": "library",
                "type": "text",
                "label": "Library",
                "default": "*LIBL"
            },
            {
                "name": "format",
                "type": "select",
                "label": "Code Format",
                "options": ["free", "fixed"],
                "default": "free"
            },
            {
                "name": "error_handling",
                "type": "boolean",
                "label": "Include Error Handling",
                "default": True
            }
        ],
        "mc_press_reference": "Modern RPG IV Language (Ch 8: File I/O)"
    },
    "sql_crud": {
        "name": "CRUD Operations (Embedded SQL)",
        "description": "Generate Create, Read, Update, Delete operations",
        "category": "database",
        "language": "sqlrpgle",
        "parameters": [
            {
                "name": "table_name",
                "type": "text",
                "label": "Table Name",
                "required": True
            },
            {
                "name": "operations",
                "type": "multiselect",
                "label": "Operations",
                "options": ["create", "read", "update", "delete"],
                "default": ["create", "read", "update", "delete"]
            },
            {
                "name": "include_transactions",
                "type": "boolean",
                "label": "Use Transactions",
                "default": True
            }
        ]
    },
    "cl_command": {
        "name": "CL Command Processor",
        "description": "Create a CL command processing program",
        "category": "utility",
        "language": "cl",
        "parameters": [
            {
                "name": "command_name",
                "type": "text",
                "label": "Command Name",
                "required": True
            },
            {
                "name": "parameters_count",
                "type": "number",
                "label": "Number of Parameters",
                "min": 1,
                "max": 10,
                "default": 3
            }
        ]
    },
    "rest_api_consumer": {
        "name": "REST API Consumer",
        "description": "Call REST APIs from RPG",
        "category": "web_services",
        "language": "rpgle",
        "parameters": [
            {
                "name": "api_url",
                "type": "text",
                "label": "API URL",
                "required": True
            },
            {
                "name": "method",
                "type": "select",
                "label": "HTTP Method",
                "options": ["GET", "POST", "PUT", "DELETE"],
                "default": "GET"
            },
            {
                "name": "auth_type",
                "type": "select",
                "label": "Authentication",
                "options": ["none", "basic", "bearer"],
                "default": "none"
            }
        ],
        "mc_press_reference": "Web Development with RPG (Ch 5: REST APIs)"
    }
}
```

### Code Generation Service

```python
class CodeGenerationService:
    """AI-powered code generation with MC Press context"""

    def __init__(self, claude_client, vector_store, template_library):
        self.claude = claude_client
        self.vector_store = vector_store
        self.templates = template_library

    async def generate_code(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        format: str = "free"
    ) -> GeneratedCode:
        """Generate code from template and parameters"""

        # 1. Get template
        template = self.templates.get(template_id)

        # 2. Validate parameters
        self._validate_parameters(template, parameters)

        # 3. Get relevant MC Press context
        context = await self._get_generation_context(template, parameters)

        # 4. Build generation prompt
        prompt = self._build_generation_prompt(
            template, parameters, format, context
        )

        # 5. Generate code with Claude
        generated_code = await self._call_claude_for_generation(prompt)

        # 6. Validate and format generated code
        validated_code = await self._validate_and_format(
            generated_code, template.language, format
        )

        # 7. Store generation
        generation = await self._store_generation(
            template_id, parameters, validated_code, context
        )

        return generation

    def _build_generation_prompt(
        self,
        template: CodeTemplate,
        parameters: Dict[str, Any],
        format: str,
        context: str
    ) -> str:
        """Build Claude prompt for code generation"""

        return f"""Generate IBM i {template.language.upper()} code based on this specification:

TEMPLATE: {template.name}
DESCRIPTION: {template.description}
FORMAT: {'Free-format' if format == 'free' else 'Fixed-format'}

PARAMETERS:
{json.dumps(parameters, indent=2)}

MC PRESS KNOWLEDGE BASE CONTEXT:
{context}

REQUIREMENTS:
1. Generate production-ready, compile-ready code
2. Follow MC Press best practices
3. Include comprehensive error handling
4. Add meaningful comments and documentation
5. Use clear, descriptive variable names
6. Include proper file declarations and definitions
7. Format code with proper indentation
8. Add header comment block with description

IMPORTANT:
- Code must be syntactically correct
- Include all necessary declarations
- Add error handling for edge cases
- Follow {format}-format conventions
- Reference MC Press standards where applicable

Generate ONLY the code, no explanations outside code comments.
"""

    async def _call_claude_for_generation(self, prompt: str) -> str:
        """Call Claude API for code generation"""

        response = await self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.2,  # Lower temp for code generation
            system=self._get_code_generation_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def _get_code_generation_system_prompt(self) -> str:
        return """You are an expert IBM i developer specializing in:
- RPG IV (ILE RPG, free-format and fixed-format)
- Embedded SQL (SQLRPGLE)
- Control Language (CL)
- Modern IBM i development practices
- MC Press coding standards

Generate clean, production-ready code that:
- Compiles without errors
- Follows best practices
- Includes proper error handling
- Is well-documented
- Uses modern techniques
- References MC Press standards

Always generate complete, working code with all necessary declarations and proper formatting.
"""

    async def _validate_and_format(
        self,
        code: str,
        language: str,
        format: str
    ) -> str:
        """Validate and format generated code"""

        # Extract code from markdown if present
        code = self._extract_code_from_markdown(code)

        # Format code based on language
        if language in ['rpg', 'rpgle', 'sqlrpgle']:
            code = self._format_rpg_code(code, format)
        elif language == 'cl':
            code = self._format_cl_code(code)
        elif language == 'sql':
            code = self._format_sql_code(code)

        # Validate syntax (basic checks)
        self._validate_syntax(code, language)

        return code

    async def _get_generation_context(
        self,
        template: CodeTemplate,
        parameters: Dict[str, Any]
    ) -> str:
        """Get relevant MC Press context for generation"""

        # Build search query from template and parameters
        query = f"{template.description} {template.language} best practices"

        # Add parameter-specific context
        for key, value in parameters.items():
            if isinstance(value, str):
                query += f" {value}"

        # Search vector store
        chunks = await self.vector_store.similarity_search(query, k=5)

        # Build context string
        context = "\n\n".join([chunk.page_content for chunk in chunks])

        return context
```

### Syntax Validation

```python
class CodeValidator:
    """Validate generated code syntax"""

    def validate_rpg(self, code: str, format: str) -> List[ValidationError]:
        """Validate RPG code"""
        errors = []

        if format == 'free':
            # Check for proper dcl-pi/end-pi
            if 'dcl-pi' in code.lower() and 'end-pi' not in code.lower():
                errors.append(ValidationError("Missing end-pi"))

            # Check for dcl-proc/end-proc
            if 'dcl-proc' in code.lower() and 'end-proc' not in code.lower():
                errors.append(ValidationError("Missing end-proc"))

        elif format == 'fixed':
            # Validate column positions
            # H specs in columns 6-80
            # D specs in columns 6-80
            # etc.
            pass

        return errors

    def validate_cl(self, code: str) -> List[ValidationError]:
        """Validate CL code"""
        errors = []

        # Check for PGM/ENDPGM
        if 'PGM' in code.upper() and 'ENDPGM' not in code.upper():
            errors.append(ValidationError("Missing ENDPGM"))

        # Check for unclosed MONMSG
        # etc.

        return errors

    def validate_sql(self, code: str) -> List[ValidationError]:
        """Validate SQL code"""
        # Basic SQL syntax validation
        pass
```

### Database Schema

```sql
-- Code generations
CREATE TABLE IF NOT EXISTS code_generations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    language TEXT NOT NULL,
    format TEXT NOT NULL,
    parameters JSONB NOT NULL,
    generated_code TEXT NOT NULL,
    mc_press_references TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    downloaded BOOLEAN DEFAULT FALSE,
    saved_to_library BOOLEAN DEFAULT FALSE
);

-- Generation feedback
CREATE TABLE IF NOT EXISTS generation_feedback (
    id SERIAL PRIMARY KEY,
    generation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    issue_type TEXT,  -- 'syntax_error', 'logic_error', 'style', 'other'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generation_id) REFERENCES code_generations(id) ON DELETE CASCADE
);

-- Usage metrics
CREATE TABLE IF NOT EXISTS generation_metrics (
    id SERIAL PRIMARY KEY,
    template_id TEXT NOT NULL,
    total_generations INTEGER DEFAULT 0,
    successful_generations INTEGER DEFAULT 0,
    avg_rating FLOAT,
    last_generated_at TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_generations_user
ON code_generations(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_generations_template
ON code_generations(template_id, created_at);

CREATE INDEX IF NOT EXISTS idx_feedback_generation
ON generation_feedback(generation_id);
```

### API Endpoints

```python
GET    /api/code-gen/templates          # List all templates
GET    /api/code-gen/templates/{id}     # Get template details
POST   /api/code-gen/generate           # Generate code
GET    /api/code-gen/history            # User's generation history
GET    /api/code-gen/generation/{id}    # Get specific generation
POST   /api/code-gen/feedback           # Submit feedback
GET    /api/code-gen/categories         # List template categories
POST   /api/code-gen/validate           # Validate generated code
```

## Implementation Tasks

### Backend Tasks
- [ ] Create template library system
- [ ] Implement code generation service
- [ ] Build Claude integration for generation
- [ ] Create syntax validators (RPG, CL, SQL)
- [ ] Implement code formatting utilities
- [ ] Build RAG context retrieval for generation
- [ ] Create generation API endpoints
- [ ] Add generation history tracking
- [ ] Implement feedback system
- [ ] Add usage metrics
- [ ] Create 20+ built-in templates

### Frontend Tasks
- [ ] Create `/code-generation` page
- [ ] Build template browser component
- [ ] Implement dynamic parameter forms
- [ ] Create code preview with syntax highlighting
- [ ] Add copy-to-clipboard functionality
- [ ] Build download-as-file feature
- [ ] Create inline code editor
- [ ] Implement generation history UI
- [ ] Add template search and filtering
- [ ] Create share generation feature
- [ ] Build feedback submission UI

### Database Tasks
- [ ] Create code_generations table
- [ ] Create generation_feedback table
- [ ] Create generation_metrics table
- [ ] Add indexes
- [ ] Create migration script

### Integration Tasks
- [ ] Integrate with Claude API
- [ ] Connect to vector store for RAG
- [ ] Wire frontend to backend
- [ ] Test end-to-end generation flow
- [ ] Validate syntax checking

## Testing Requirements

### Unit Tests
- [ ] Template validation
- [ ] Parameter validation
- [ ] Code formatting (RPG, CL, SQL)
- [ ] Syntax validation
- [ ] Context retrieval

### Integration Tests
- [ ] Complete generation flow
- [ ] Claude API integration
- [ ] RAG context retrieval
- [ ] Multi-language generation
- [ ] History persistence

### E2E Tests
- [ ] Select template and generate code
- [ ] Edit parameters and regenerate
- [ ] Copy generated code
- [ ] Download as file
- [ ] Submit feedback
- [ ] View generation history

### Quality Tests
- [ ] Generated code compiles successfully
- [ ] Code follows MC Press standards
- [ ] Error handling is comprehensive
- [ ] Comments are meaningful
- [ ] Syntax is valid

## Success Metrics

- **Generation Success Rate**: >95%
- **Code Compile Rate**: >90% (generated code compiles)
- **User Satisfaction**: 4+ stars average rating
- **Generation Speed**: <5 seconds
- **Template Usage**: 100+ generations per week
- **Repeat Usage**: 60%+ users generate multiple times

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] 20+ templates created and tested
- [ ] Generated code validated by IBM i developers
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- Anthropic Claude API
- Existing vector store with MC Press content
- Syntax highlighting library (Prism.js or similar)
- PostgreSQL database

## Risks

- **Risk**: Generated code has syntax errors
  - **Mitigation**: Multi-layer validation, user testing, feedback loop

- **Risk**: Claude API costs too high
  - **Mitigation**: Token optimization, caching, rate limiting

- **Risk**: Templates don't cover common use cases
  - **Mitigation**: User feedback, usage analytics, continuous template expansion

## Future Enhancements

- User-created custom templates
- Template marketplace
- IDE plugin integration
- Git integration
- Automated testing of generated code
- Version control for generations
- Team template sharing

---

## Notes

Focus on quality over quantity for initial templates. Better to have 20 excellent templates than 100 mediocre ones.
