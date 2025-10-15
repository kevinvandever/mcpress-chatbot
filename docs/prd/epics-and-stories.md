# MC Press Chatbot - Epics and User Stories

## Epic Structure Overview

Based on the PRD phases, we have 4 major epics with multiple stories each:

1. **EPIC-001**: Technical Foundation & Admin Tools (Phase 0)
2. **EPIC-002**: Core Productivity Suite (Phase 1) 
3. **EPIC-003**: Collaboration & Learning Platform (Phase 2)
4. **EPIC-004**: Enterprise & Scalability (Phase 3)

---

## EPIC-001: Technical Foundation & Admin Tools
**Priority**: P0 (Critical)  
**Timeline**: Month 0 (4 weeks)  
**Value**: Enables content management and removes broken features

### Stories

#### STORY-001: Remove Non-Functional Search Feature
**Points**: 3  
**Priority**: P0  
**As a** user  
**I want** the broken search feature removed  
**So that** I don't encounter errors and confusion  

**Acceptance Criteria:**
- [ ] Search bar removed from all UI pages
- [ ] Search API endpoints return 410 Gone or redirect
- [ ] All search routes redirect to chat interface
- [ ] No console errors related to search
- [ ] Update navigation to remove search references

**Technical Tasks:**
- Remove search component from frontend
- Disable search endpoints in backend
- Update routing configuration
- Clean up search-related dependencies
- Update documentation

---

#### STORY-002: Admin Authentication System
**Points**: 5  
**Priority**: P0  
**As an** admin (David)  
**I want** secure authentication to admin dashboard  
**So that** only authorized users can manage content  

**Acceptance Criteria:**
- [ ] OAuth integration (Google/GitHub)
- [ ] Multi-factor authentication enabled
- [ ] Session management with timeout
- [ ] Role-based access (admin/viewer)
- [ ] Audit log for login attempts

---

#### STORY-003: PDF Upload Interface
**Points**: 8  
**Priority**: P0  
**As an** admin  
**I want** to upload PDFs with metadata  
**So that** I can add new books to the chatbot  

**Acceptance Criteria:**
- [ ] Single file upload with drag-drop
- [ ] Batch upload (up to 20 files)
- [ ] Progress indicators for processing
- [ ] Metadata form (title, author, ISBN, purchase URL)
- [ ] Validation and error handling
- [ ] Success/failure notifications

---

#### STORY-004: Metadata Management System
**Points**: 5  
**Priority**: P0  
**As an** admin  
**I want** to edit document metadata  
**So that** books have accurate information  

**Acceptance Criteria:**
- [ ] List view of all documents with metadata
- [ ] Inline editing of metadata fields
- [ ] Bulk edit capabilities (select multiple)
- [ ] CSV export of all metadata
- [ ] CSV import for bulk updates
- [ ] Change history tracking

---

#### STORY-005: Document Processing Pipeline
**Points**: 8  
**Priority**: P0  
**As a** system  
**I want** to process uploaded PDFs automatically  
**So that** content is indexed and searchable  

**Acceptance Criteria:**
- [ ] PDF text extraction
- [ ] Vector embedding generation
- [ ] Database storage optimization
- [ ] Error recovery mechanisms
- [ ] Processing status webhooks

---

## EPIC-002: Core Productivity Suite
**Priority**: P0  
**Timeline**: Months 1-2 (8 weeks)  
**Value**: Core features that justify subscription pricing

### Stories

#### STORY-006: File Upload for Code Analysis
**Points**: 5  
**Priority**: P0  
**As a** developer  
**I want** to upload my RPG/CL files  
**So that** I can get AI-powered code review  

**Acceptance Criteria:**
- [ ] Support .rpg, .rpgle, .sqlrpgle, .cl, .sql files
- [ ] File size limit (10MB)
- [ ] Multiple file upload (up to 10)
- [ ] File validation and type checking
- [ ] Temporary storage with 24hr auto-deletion

---

#### STORY-007: AI Code Analysis Engine
**Points**: 13  
**Priority**: P0  
**As a** developer  
**I want** AI analysis of my code  
**So that** I can improve code quality  

**Acceptance Criteria:**
- [ ] Best practices validation
- [ ] Security vulnerability detection
- [ ] Performance optimization suggestions
- [ ] Modernization recommendations
- [ ] MC Press standards compliance check
- [ ] Detailed analysis report generation

---

#### STORY-008: Code Generation Interface
**Points**: 8  
**Priority**: P0  
**As a** developer  
**I want** to generate IBM i code snippets  
**So that** I can accelerate development  

**Acceptance Criteria:**
- [ ] Template selection UI
- [ ] Parameter input forms
- [ ] Real-time code preview
- [ ] Syntax highlighting
- [ ] Copy-to-clipboard functionality
- [ ] Download as file option

---

#### STORY-009: Code Template Library
**Points**: 5  
**Priority**: P1  
**As a** developer  
**I want** to save and reuse code templates  
**So that** I can maintain consistency  

**Acceptance Criteria:**
- [ ] Personal template library
- [ ] Template categorization
- [ ] Search and filter templates
- [ ] Template sharing (public/private)
- [ ] Version control for templates
- [ ] Import/export templates

---

#### STORY-010: E-commerce Integration
**Points**: 8  
**Priority**: P1  
**As a** user  
**I want** to purchase recommended books  
**So that** I can deepen my knowledge  

**Acceptance Criteria:**
- [ ] "Buy Now" CTAs in chat responses
- [ ] Real-time pricing display
- [ ] Bundle recommendations
- [ ] Discount code application
- [ ] Shopping cart persistence
- [ ] Purchase tracking

---

#### STORY-011: Conversation History
**Points**: 5  
**Priority**: P1  
**As a** user  
**I want** to access my chat history  
**So that** I can reference previous solutions  

**Acceptance Criteria:**
- [ ] Persistent conversation storage
- [ ] Search within history
- [ ] Filter by date/topic
- [ ] Pagination for long histories
- [ ] Delete conversations
- [ ] Archive old conversations

---

#### STORY-012: Conversation Export
**Points**: 3
**Priority**: P1
**As a** user
**I want** to export conversations
**So that** I can share knowledge with my team

**Acceptance Criteria:**
- [ ] Export to PDF format
- [ ] Export to Markdown
- [ ] Include code highlighting
- [ ] Custom title and metadata
- [ ] Bulk export options

---

#### STORY-019: Analytics Dashboard ⚡ **MOVED FROM EPIC-004**
**Points**: 8
**Priority**: P0 (Critical) - **ELEVATED FOR MVP**
**As a** subscriber
**I want** to see analytics showing my productivity gains and learning progress
**So that** I can justify my $20/month investment and track my professional growth

**Acceptance Criteria:**
- [ ] Usage dashboard accessible from main navigation
- [ ] Time saved calculator (estimates hours saved per session)
- [ ] Activity timeline (daily/weekly/monthly usage patterns)
- [ ] Code analysis stats (files analyzed, lines reviewed, errors caught)
- [ ] Learning velocity (topics mastered, progress over time)
- [ ] Query insights (most common questions, knowledge gaps)
- [ ] ROI calculator (shows dollar value of time saved)
- [ ] PDF/CSV export for reports
- [ ] Benchmark comparison to average users
- [ ] Email monthly summary reports

**Why Moved to MVP:**
- **Critical for pricing justification**: Must prove ROI vs free alternatives (Codeium)
- **David's concern**: "Value justification for $20/month" requires demonstrable metrics
- **Competitive pressure**: Users need to see concrete value immediately
- **Retention driver**: Analytics showing value reduces churn

**Full Story**: See `docs/prd/stories/story-019-analytics-dashboard.md`

---

## EPIC-003: Collaboration & Learning Platform
**Priority**: P1  
**Timeline**: Months 3-4 (8 weeks)  
**Value**: Team features and skill development

### Stories

#### STORY-013: Project Organization System
**Points**: 8  
**Priority**: P1  
**As a** developer  
**I want** to organize chats by project  
**So that** I can manage multiple initiatives  

**Acceptance Criteria:**
- [ ] Create/edit/delete projects
- [ ] Assign conversations to projects
- [ ] Project metadata and descriptions
- [ ] Project-level search
- [ ] Project activity timeline
- [ ] Project archival

---

#### STORY-014: Task Management Integration
**Points**: 5  
**Priority**: P1  
**As a** team lead  
**I want** to track tasks from conversations  
**So that** I can manage team workload  

**Acceptance Criteria:**
- [ ] Create tasks from chat
- [ ] Task assignment to team members
- [ ] Due date and priority settings
- [ ] Jira integration API
- [ ] Trello integration API
- [ ] Task completion tracking

---

#### STORY-015: Learning Path Engine
**Points**: 13  
**Priority**: P1  
**As a** developer  
**I want** personalized learning paths  
**So that** I can systematically improve skills  

**Acceptance Criteria:**
- [ ] Skill assessment questionnaire
- [ ] Personalized curriculum generation
- [ ] Progress tracking dashboard
- [ ] Milestone achievements
- [ ] Recommended MC Press books
- [ ] Time estimates for completion

---

#### STORY-016: Interactive Exercises
**Points**: 8  
**Priority**: P1  
**As a** learner  
**I want** hands-on coding exercises  
**So that** I can practice new concepts  

**Acceptance Criteria:**
- [ ] Exercise problem statements
- [ ] Online code editor
- [ ] Test case validation
- [ ] Hints and solutions
- [ ] Progress saving
- [ ] Difficulty progression

---

#### STORY-017: Voice Interface Implementation
**Points**: 8  
**Priority**: P2  
**As a** user  
**I want** to interact via voice  
**So that** I can query hands-free  

**Acceptance Criteria:**
- [ ] Speech-to-text integration
- [ ] Text-to-speech for responses
- [ ] Wake word detection
- [ ] Technical term recognition
- [ ] Voice command shortcuts
- [ ] Accessibility compliance

---

#### STORY-018: Team Workspace
**Points**: 8
**Priority**: P2
**As a** team
**I want** shared workspace
**So that** we can collaborate effectively

**Acceptance Criteria:**
- [ ] Create team workspaces
- [ ] Invite team members
- [ ] Role-based permissions
- [ ] Shared conversations
- [ ] Team knowledge base
- [ ] Activity feed

---

#### STORY-024: VS Code Extension 🆕 **COMPETITIVE NECESSITY**
**Points**: 13
**Priority**: P1 (High)
**As an** IBM i developer using VS Code
**I want** MC Press Chatbot integrated directly into my editor
**So that** I can get AI assistance without context switching

**Acceptance Criteria:**
- [ ] Chat sidebar in VS Code
- [ ] Right-click context menu "Ask MC Press"
- [ ] Code actions for quick fixes
- [ ] Inline suggestions and hover tooltips
- [ ] File upload for analysis
- [ ] Authentication with MC Press account
- [ ] Apply code changes with one click
- [ ] Diff view for before/after comparison
- [ ] Command palette integration (Cmd+Shift+P)
- [ ] Keyboard shortcuts (customizable)
- [ ] Status bar showing usage stats
- [ ] VS Code Marketplace publication

**Why Critical:**
- **Closes competitive gap**: Copilot, Cursor, Tabnine all have IDE integration
- **Where developers work**: Native editor integration vs context switching to web
- **Code for IBM i synergy**: 10,000+ installs, growing VS Code adoption in IBM i space

**Full Story**: See `docs/prd/stories/story-024-vscode-extension.md`

---

#### STORY-025: Slack & Microsoft Teams Bot Integration 🆕 **ENTERPRISE REQUIREMENT**
**Points**: 8
**Priority**: P1 (High)
**As a** team lead or developer
**I want** to access MC Press Chatbot from Slack/Teams
**So that** I can get IBM i help without leaving my team's communication platform

**Acceptance Criteria:**
- [ ] Slack slash commands (`/mcpress <question>`)
- [ ] Slack app mentions (`@MC Press`)
- [ ] Slack DMs (private conversations)
- [ ] Slack threaded responses
- [ ] Teams bot with Adaptive Cards
- [ ] Teams personal chat (1:1 DMs)
- [ ] File upload/analysis in both platforms
- [ ] Workspace authentication & linking
- [ ] Team usage tracking & analytics
- [ ] Rate limiting per tier (Team: 100/day, Enterprise: unlimited)
- [ ] Shared team knowledge base
- [ ] Interactive buttons (Ask Follow-up, Save, Buy Book)

**Why Critical:**
- **Enterprise sales requirement**: Team Lead ($35) & Enterprise ($60) tiers need this
- **Table stakes**: Competitors (Stack Overflow, Notion AI, ChatGPT Team) have chat integration
- **Network effects**: Team visibility drives viral adoption within organizations

**Full Story**: See `docs/prd/stories/story-025-slack-teams-bots.md`

---

## EPIC-004: Enterprise & Scalability
**Priority**: P2
**Timeline**: Months 5-6 (8 weeks)
**Value**: Enterprise features and platform scaling

**Note**: Story-019 (Analytics Dashboard) was moved to EPIC-002 (MVP/Phase 1) due to critical importance for pricing justification.

### Stories

#### STORY-020: API Development
**Points**: 13  
**Priority**: P2  
**As a** developer  
**I want** API access  
**So that** I can integrate with our tools  

**Acceptance Criteria:**
- [ ] RESTful API design
- [ ] API key management
- [ ] Rate limiting (tier-based)
- [ ] Request/response logging
- [ ] API documentation
- [ ] SDKs for popular languages

---

#### STORY-021: Mobile App - iOS
**Points**: 21  
**Priority**: P3  
**As a** mobile user  
**I want** native iOS app  
**So that** I can access on the go  

**Acceptance Criteria:**
- [ ] Native iOS application
- [ ] Touch-optimized interface
- [ ] Offline mode with sync
- [ ] Biometric authentication
- [ ] Push notifications
- [ ] App Store deployment

---

#### STORY-022: Mobile App - Android
**Points**: 21  
**Priority**: P3  
**As a** mobile user  
**I want** native Android app  
**So that** I can access on any device  

**Acceptance Criteria:**
- [ ] Native Android application
- [ ] Material Design compliance
- [ ] Offline mode with sync
- [ ] Biometric authentication
- [ ] Push notifications
- [ ] Google Play deployment

---

## Story Point Summary

### By Epic (UPDATED)
- **EPIC-001** (Technical Foundation): 29 points (Stories 001-005)
- **EPIC-002** (Core Productivity): **60 points** (Stories 006-012, 019) ⬆️ +8 from Story-019
- **EPIC-003** (Collaboration & Learning): **79 points** (Stories 013-018, 024-025) ⬆️ +21 from new stories
- **EPIC-004** (Enterprise & Scale): **55 points** (Stories 020-022) ⬇️ -8 from moving Story-019

**Total Story Points**: 223 points (25 stories)

### By Priority (UPDATED)
- **P0 (Critical)**: **65 points** (Stories 001-008, 019) ⬆️ +8 from elevating Story-019
- **P1 (High)**: **95 points** (Stories 009-016, 024-025) ⬆️ +21 from new stories
- **P2 (Medium)**: **21 points** (Stories 017-018, 020) ⬇️ -8 from Story-019 elevation
- **P3 (Low)**: 42 points (Stories 021-022)

### Velocity Planning (UPDATED)
Assuming 2-week sprints with 20-25 points velocity:
- **Phase 0** (EPIC-001): 2 sprints (4 weeks) - 29 points
- **Phase 1** (EPIC-002): 3 sprints (6 weeks) - 60 points ⬆️ Added Analytics
- **Phase 2** (EPIC-003): 4 sprints (8 weeks) - 79 points ⬆️ Added VS Code + Slack/Teams
- **Phase 3** (EPIC-004): 3 sprints (6 weeks) - 55 points

**Total Timeline**: 22-26 weeks (5.5-6.5 months)

---

## Next Steps

1. **Immediate Actions** (Week 1):
   - Start STORY-001 (Remove search)
   - Design admin dashboard UI
   - Set up OAuth providers

2. **Technical Preparation**:
   - Upgrade storage tier on Railway
   - Set up development environment
   - Create CI/CD pipelines

3. **Stakeholder Alignment**:
   - Review and prioritize stories with David
   - Define MVP scope for beta launch
   - Plan marketing for feature releases