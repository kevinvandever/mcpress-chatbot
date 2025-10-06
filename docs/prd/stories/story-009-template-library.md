# Story: Code Template Library

**Story ID**: STORY-009
**Epic**: EPIC-002 (Core Productivity Suite)
**Type**: New Feature
**Priority**: P1 (High)
**Points**: 5
**Sprint**: 7-8
**Status**: Ready for Development

## User Story

**As a** developer
**I want** to save and reuse code templates
**So that** I can maintain consistency across projects and share knowledge with my team

## Context

A personal template library transforms one-time code generation into a reusable knowledge system. Developers can save successful generations, create custom templates, and build a personal or team library of patterns. This feature increases long-term platform value and encourages continued usage.

## Current State

### Existing System
- **Code Generation**: STORY-008 provides AI code generation
- **Built-in Templates**: 20+ templates in system
- **User System**: Authentication and user management exist
- **Database**: PostgreSQL for storage
- **Code Generations**: Stored in code_generations table

### Gap Analysis
- No way to save generated code as template
- No custom template creation
- No template organization/categorization
- No template search
- No sharing capabilities
- No version control for templates
- No import/export functionality

## Acceptance Criteria

### Core Library Features
- [ ] Save generated code as personal template
- [ ] Create custom templates from scratch
- [ ] Organize templates by category/tags
- [ ] Search and filter template library
- [ ] Edit existing templates
- [ ] Delete templates
- [ ] Duplicate/clone templates
- [ ] Version history for templates

### Sharing & Collaboration
- [ ] Mark templates as public/private
- [ ] Share templates with specific users
- [ ] Browse public template library
- [ ] Fork/copy public templates
- [ ] Rate and comment on public templates
- [ ] Report inappropriate templates

### Import/Export
- [ ] Export templates as JSON
- [ ] Export multiple templates as bundle
- [ ] Import templates from JSON
- [ ] Bulk import template library
- [ ] Validate imported templates

### Template Management
- [ ] Usage statistics per template
- [ ] Last used timestamp
- [ ] Success rate tracking
- [ ] Favorite/bookmark templates
- [ ] Archive unused templates
- [ ] Template preview

## Technical Design

### Template Data Model

```python
class UserTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: str
    category: TemplateCategory
    language: CodeLanguage
    format: str  # 'free' or 'fixed'
    parameters: List[TemplateParameter]
    code_template: str  # Template with placeholders
    tags: List[str] = []
    is_public: bool = False
    is_favorite: bool = False
    is_archived: bool = False
    version: int = 1
    parent_template_id: Optional[str] = None  # For forked templates
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    success_rate: float = 0.0
    mc_press_references: List[str] = []

class TemplateVersion(BaseModel):
    id: str
    template_id: str
    version: int
    code_template: str
    parameters: List[TemplateParameter]
    changes_description: str
    created_at: datetime
    created_by: str

class TemplateShare(BaseModel):
    id: str
    template_id: str
    shared_by: str
    shared_with: str  # User ID or 'public'
    permission: str  # 'view', 'fork', 'edit'
    created_at: datetime

class TemplateRating(BaseModel):
    id: str
    template_id: str
    user_id: str
    rating: int  # 1-5 stars
    comment: Optional[str]
    created_at: datetime
```

### Frontend Components

#### Template Library Page (`/templates`)

```typescript
interface TemplateLibraryState {
  templates: UserTemplate[]
  publicTemplates: UserTemplate[]
  view: 'grid' | 'list'
  filters: {
    category?: TemplateCategory
    language?: CodeLanguage
    tags?: string[]
    isPublic?: boolean
    isFavorite?: boolean
  }
  sort: {
    field: 'name' | 'created_at' | 'usage_count' | 'rating'
    direction: 'asc' | 'desc'
  }
  selectedTemplate?: UserTemplate
}
```

#### Components
- `TemplateLibraryBrowser` - Main library view
- `TemplateCard` - Template preview card
- `TemplateEditor` - Create/edit template form
- `TemplateParameterBuilder` - Build parameter definitions
- `TemplatePreview` - Preview template with sample data
- `TemplateShareDialog` - Sharing controls
- `TemplateImportExport` - Import/export UI
- `PublicTemplateGallery` - Browse public templates
- `TemplateVersionHistory` - View version history

### Template Service

```python
class TemplateLibraryService:
    """Manage user template library"""

    async def save_generation_as_template(
        self,
        user_id: str,
        generation_id: str,
        template_name: str,
        description: str,
        category: TemplateCategory,
        tags: List[str] = []
    ) -> UserTemplate:
        """Save a code generation as a reusable template"""

        # Get the generation
        generation = await self._get_generation(generation_id)

        # Extract parameters from generation
        parameters = self._extract_parameters(generation)

        # Convert code to template format (with placeholders)
        code_template = self._parameterize_code(
            generation.code,
            generation.parameters
        )

        # Create template
        template = UserTemplate(
            user_id=user_id,
            name=template_name,
            description=description,
            category=category,
            language=generation.language,
            format=generation.format,
            parameters=parameters,
            code_template=code_template,
            tags=tags,
            mc_press_references=generation.mc_press_references
        )

        # Save to database
        await self._save_template(template)

        return template

    async def create_custom_template(
        self,
        user_id: str,
        template_data: Dict[str, Any]
    ) -> UserTemplate:
        """Create a custom template from scratch"""

        # Validate template data
        self._validate_template_data(template_data)

        # Create template
        template = UserTemplate(
            user_id=user_id,
            **template_data
        )

        # Save to database
        await self._save_template(template)

        return template

    async def update_template(
        self,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> UserTemplate:
        """Update existing template with versioning"""

        # Get current template
        template = await self._get_template(template_id, user_id)

        # Create version snapshot
        await self._create_version_snapshot(template)

        # Apply updates
        for key, value in updates.items():
            setattr(template, key, value)

        template.version += 1
        template.updated_at = datetime.utcnow()

        # Save updated template
        await self._save_template(template)

        return template

    def _parameterize_code(
        self,
        code: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Convert concrete code to parameterized template"""

        template_code = code

        # Replace parameter values with placeholders
        for param_name, param_value in parameters.items():
            # Create placeholder
            placeholder = f"{{{{ {param_name} }}}}"

            # Replace value with placeholder
            template_code = template_code.replace(
                str(param_value),
                placeholder
            )

        return template_code

    def _extract_parameters(
        self,
        generation: GeneratedCode
    ) -> List[TemplateParameter]:
        """Extract parameter definitions from generation"""

        parameters = []

        for name, value in generation.parameters.items():
            param_type = self._infer_parameter_type(value)

            parameter = TemplateParameter(
                name=name,
                type=param_type,
                label=self._format_label(name),
                description=f"Parameter: {name}",
                required=True,
                default=value if param_type != 'text' else None
            )

            parameters.append(parameter)

        return parameters

    async def share_template(
        self,
        template_id: str,
        user_id: str,
        share_with: str,  # User ID or 'public'
        permission: str = 'view'
    ) -> TemplateShare:
        """Share template with user or make public"""

        template = await self._get_template(template_id, user_id)

        share = TemplateShare(
            id=str(uuid.uuid4()),
            template_id=template_id,
            shared_by=user_id,
            shared_with=share_with,
            permission=permission,
            created_at=datetime.utcnow()
        )

        # If sharing publicly, mark template as public
        if share_with == 'public':
            template.is_public = True
            await self._save_template(template)

        await self._save_share(share)

        return share

    async def fork_template(
        self,
        template_id: str,
        user_id: str,
        new_name: str
    ) -> UserTemplate:
        """Fork a public or shared template"""

        # Get original template
        original = await self._get_template_for_fork(template_id, user_id)

        # Create forked copy
        forked = UserTemplate(
            user_id=user_id,
            name=new_name,
            description=f"Forked from: {original.name}",
            category=original.category,
            language=original.language,
            format=original.format,
            parameters=original.parameters.copy(),
            code_template=original.code_template,
            tags=original.tags.copy(),
            parent_template_id=template_id,
            is_public=False
        )

        await self._save_template(forked)

        return forked

    async def import_templates(
        self,
        user_id: str,
        template_data: List[Dict[str, Any]]
    ) -> List[UserTemplate]:
        """Import templates from JSON"""

        imported_templates = []

        for data in template_data:
            # Validate template structure
            self._validate_template_data(data)

            # Create template
            template = UserTemplate(
                user_id=user_id,
                **data
            )

            # Save to database
            await self._save_template(template)
            imported_templates.append(template)

        return imported_templates

    async def export_templates(
        self,
        user_id: str,
        template_ids: Optional[List[str]] = None
    ) -> str:
        """Export templates as JSON"""

        # Get templates
        if template_ids:
            templates = await self._get_templates_by_ids(
                template_ids, user_id
            )
        else:
            templates = await self._get_all_user_templates(user_id)

        # Convert to JSON
        export_data = [
            template.dict(exclude={'id', 'user_id', 'created_at', 'updated_at'})
            for template in templates
        ]

        return json.dumps(export_data, indent=2)
```

### Template Search & Discovery

```python
class TemplateSearchService:
    """Search and discover templates"""

    async def search_templates(
        self,
        user_id: str,
        query: str,
        filters: Dict[str, Any] = {},
        include_public: bool = True
    ) -> List[UserTemplate]:
        """Search user and public templates"""

        # Build search query
        search_conditions = []

        # User's templates
        search_conditions.append(f"user_id = '{user_id}'")

        # Public templates
        if include_public:
            search_conditions.append("is_public = true")

        # Text search
        if query:
            search_conditions.append(f"""
                (name ILIKE '%{query}%'
                OR description ILIKE '%{query}%'
                OR '{query}' = ANY(tags))
            """)

        # Category filter
        if filters.get('category'):
            search_conditions.append(
                f"category = '{filters['category']}'"
            )

        # Language filter
        if filters.get('language'):
            search_conditions.append(
                f"language = '{filters['language']}'"
            )

        # Tags filter
        if filters.get('tags'):
            tags_condition = " OR ".join([
                f"'{tag}' = ANY(tags)" for tag in filters['tags']
            ])
            search_conditions.append(f"({tags_condition})")

        # Favorites only
        if filters.get('is_favorite'):
            search_conditions.append("is_favorite = true")

        # Execute search
        templates = await self._execute_search(search_conditions)

        return templates

    async def get_trending_templates(
        self,
        limit: int = 20
    ) -> List[UserTemplate]:
        """Get trending public templates"""

        # Templates with high usage in last 30 days
        query = """
            SELECT * FROM user_templates
            WHERE is_public = true
            AND last_used_at > NOW() - INTERVAL '30 days'
            ORDER BY usage_count DESC, success_rate DESC
            LIMIT %s
        """

        templates = await self._execute_query(query, limit)

        return templates

    async def get_recommended_templates(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[UserTemplate]:
        """Get personalized template recommendations"""

        # Get user's template usage patterns
        user_categories = await self._get_user_category_preferences(user_id)
        user_languages = await self._get_user_language_preferences(user_id)

        # Find public templates matching preferences
        query = """
            SELECT * FROM user_templates
            WHERE is_public = true
            AND user_id != %s
            AND (category = ANY(%s) OR language = ANY(%s))
            ORDER BY success_rate DESC, usage_count DESC
            LIMIT %s
        """

        templates = await self._execute_query(
            query, user_id, user_categories, user_languages, limit
        )

        return templates
```

### Database Schema

```sql
-- User templates
CREATE TABLE IF NOT EXISTS user_templates (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT NOT NULL,
    format TEXT NOT NULL,
    parameters JSONB NOT NULL,
    code_template TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    is_public BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    parent_template_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    mc_press_references TEXT[] DEFAULT '{}'
);

-- Template versions
CREATE TABLE IF NOT EXISTS template_versions (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    code_template TEXT NOT NULL,
    parameters JSONB NOT NULL,
    changes_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    FOREIGN KEY (template_id) REFERENCES user_templates(id) ON DELETE CASCADE
);

-- Template sharing
CREATE TABLE IF NOT EXISTS template_shares (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    shared_by TEXT NOT NULL,
    shared_with TEXT NOT NULL,
    permission TEXT DEFAULT 'view',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES user_templates(id) ON DELETE CASCADE
);

-- Template ratings
CREATE TABLE IF NOT EXISTS template_ratings (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES user_templates(id) ON DELETE CASCADE,
    UNIQUE(template_id, user_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_templates_user
ON user_templates(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_templates_public
ON user_templates(is_public, category, language) WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_templates_tags
ON user_templates USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_templates_search
ON user_templates USING GIN(to_tsvector('english', name || ' ' || description));

CREATE INDEX IF NOT EXISTS idx_template_versions
ON template_versions(template_id, version);

CREATE INDEX IF NOT EXISTS idx_template_shares
ON template_shares(template_id, shared_with);

CREATE INDEX IF NOT EXISTS idx_template_ratings
ON template_ratings(template_id);
```

### API Endpoints

```python
# Template CRUD
POST   /api/templates                   # Create template
GET    /api/templates                   # List user's templates
GET    /api/templates/{id}              # Get template details
PUT    /api/templates/{id}              # Update template
DELETE /api/templates/{id}              # Delete template
POST   /api/templates/{id}/favorite     # Toggle favorite
POST   /api/templates/{id}/archive      # Archive template

# Template from generation
POST   /api/templates/from-generation   # Save generation as template

# Sharing
POST   /api/templates/{id}/share        # Share template
GET    /api/templates/public            # Browse public templates
GET    /api/templates/shared-with-me    # Templates shared with user
POST   /api/templates/{id}/fork         # Fork a template

# Discovery
GET    /api/templates/search            # Search templates
GET    /api/templates/trending          # Trending templates
GET    /api/templates/recommended       # Personalized recommendations

# Import/Export
POST   /api/templates/import            # Import templates
POST   /api/templates/export            # Export templates

# Ratings
POST   /api/templates/{id}/rate         # Rate template
GET    /api/templates/{id}/ratings      # Get template ratings

# Versions
GET    /api/templates/{id}/versions     # Get version history
POST   /api/templates/{id}/restore      # Restore version
```

## Implementation Tasks

### Backend Tasks
- [ ] Create template library service
- [ ] Implement template CRUD operations
- [ ] Build template versioning system
- [ ] Create sharing functionality
- [ ] Implement search and discovery
- [ ] Build import/export functionality
- [ ] Add rating system
- [ ] Create template API endpoints
- [ ] Implement template validation
- [ ] Add usage tracking

### Frontend Tasks
- [ ] Create `/templates` library page
- [ ] Build template browser component
- [ ] Implement template editor
- [ ] Create parameter builder UI
- [ ] Add sharing controls
- [ ] Build public template gallery
- [ ] Implement search/filter UI
- [ ] Create import/export interface
- [ ] Add version history viewer
- [ ] Build template preview

### Database Tasks
- [ ] Create user_templates table
- [ ] Create template_versions table
- [ ] Create template_shares table
- [ ] Create template_ratings table
- [ ] Add full-text search indexes
- [ ] Create migration script

### Integration Tasks
- [ ] Integrate with STORY-008 (code generation)
- [ ] Connect template library to generation flow
- [ ] Test template import/export
- [ ] Validate sharing functionality
- [ ] Test version control

## Testing Requirements

### Unit Tests
- [ ] Template CRUD operations
- [ ] Template parameterization
- [ ] Version management
- [ ] Sharing logic
- [ ] Search functionality

### Integration Tests
- [ ] Save generation as template
- [ ] Create and use custom template
- [ ] Share and fork templates
- [ ] Import/export templates
- [ ] Template versioning

### E2E Tests
- [ ] Create template from generation
- [ ] Build custom template from scratch
- [ ] Share template publicly
- [ ] Fork public template
- [ ] Export and re-import templates
- [ ] Search and use template

## Success Metrics

- **Template Creation Rate**: 30% of users create templates
- **Template Reuse Rate**: 50% of templates used 2+ times
- **Public Template Engagement**: 20% of templates made public
- **Fork Rate**: 15% of public templates forked
- **Average Rating**: 4+ stars for public templates
- **Import/Export Usage**: 10% of users export templates

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- STORY-008 (Code Generation Interface) - Must be completed first
- User authentication system
- PostgreSQL database

## Risks

- **Risk**: Complex template parameterization
  - **Mitigation**: Start simple, iterate based on feedback

- **Risk**: Public templates with errors
  - **Mitigation**: Rating system, reporting, moderation

- **Risk**: Template library becomes cluttered
  - **Mitigation**: Search, archiving, favorites, tags

## Future Enhancements

- Template marketplace (paid templates)
- AI-assisted template creation
- Template analytics dashboard
- Team template libraries
- Template categories curation
- Template bundles/collections
- Auto-update templates with best practices

---

## Notes

This feature creates a flywheel effect - the more templates users create and share, the more valuable the platform becomes.
