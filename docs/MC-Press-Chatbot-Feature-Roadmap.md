# MC Press Chatbot - Feature Roadmap Documentation

**Created**: September 22, 2025  
**Author**: Tara (Business Analyst)  
**Sources**: David's Research Document + Additional Strategic Analysis

---

## Executive Summary

This document synthesizes David's comprehensive feature research with technical implementation strategies and additional recommendations. Features are clearly marked as either **[DAVID'S REQUIREMENT]** or **[ADDITIONAL SUGGESTION]** to maintain clarity on the source of each idea.

---

## Brand Guidelines & Visual Design

### MC Press Trade Dress Colors **[DAVID'S REQUIREMENT]**

The chatbot interface must align with MC Press Online and MC Press Bookstore branding using these official colors:

- **Blue**: #878DBC (Primary - headers, primary buttons, links)
- **Green**: #A1A88B (Success states, confirmations, available status)
- **Orange**: #EF9537 (CTAs, highlights, "Buy Now" buttons)
- **Red**: #990000 (Errors, warnings, critical alerts)
- **Gray**: #A3A2A2 (Secondary text, borders, disabled states)

**Implementation Notes:**
- Create CSS variables for consistent usage
- Ensure WCAG AA compliance for contrast ratios
- Use Blue as primary brand color in navigation
- Orange for purchase/conversion actions
- Maintain consistency with mcpressonline.com

---

## David's Core Vision & Requirements

### Business Goals (From David's Research)
- **Target Market**: IBM i professionals, RPG developers, system administrators
- **Value Proposition**: Specialized AI assistant that saves time, improves code quality, and provides instant access to MC Press expertise
- **Monetization**: Tiered subscription model ($20/$35/$60 per month)
- **Differentiator**: Deep IBM i/AS400 expertise unavailable in general AI tools

### Critical Success Factors (From David's Research)
1. Content quality and regular updates
2. Fast performance and intuitive UX
3. Clear ROI demonstration through productivity metrics
4. Robust security and data handling
5. Strong integration with MC Press e-commerce

---

## Feature Roadmap with Implementation Details

### Pre-Phase 1: Technical Debt & Foundation
*Focus: Clean up existing issues and build admin foundation*

#### 0.1 Remove Current Search Feature **[KEVIN'S REQUIREMENT]**

**Rationale:**
- Current search is not working as designed
- Doesn't add significant value beyond chat functionality
- Causes confusion with chat-based retrieval
- Maintenance overhead without clear benefit

**Implementation:**
- Remove search bar from UI
- Disable search endpoints in backend
- Redirect search-related routes to chat
- Focus entirely on conversational AI interaction

---

#### 0.2 Admin Dashboard **[KEVIN'S REQUIREMENT - Critical]**

**Specification:**
- Admin interface for content management
- Two primary functions:
  1. Upload new PDFs/articles (individual or batch)
  2. Edit document metadata (author, purchase links, descriptions)

**Technical Implementation Details:**
- **Authentication**: Admin-only OAuth with MFA
- **Upload Interface**:
  - Drag-and-drop for PDFs
  - Batch upload with progress indicators
  - Automatic text extraction and embedding generation
  - Preview before finalizing
- **Metadata Editor**:
  - DataGrid view of all documents
  - Inline editing for:
    - Author name
    - MC Store purchase URL
    - Book description
    - Categories/tags
    - Publication date
    - ISBN
  - Bulk edit capabilities
  - Search/filter documents
- **Backend Processing**:
  - Queue system for batch uploads (Celery/Redis)
  - Background embedding generation
  - Validation of purchase URLs
  - Duplicate detection
- **Database Updates**:
  - Audit trail for all changes
  - Rollback capability
  - Export/import metadata as CSV

**UI Mockup Structure**:
```
Admin Dashboard
├── Upload Section
│   ├── Single Upload
│   ├── Batch Upload
│   └── Upload History
├── Document Management
│   ├── Document List (DataGrid)
│   ├── Bulk Actions
│   └── Metadata Templates
└── Analytics
    ├── Upload Stats
    ├── Missing Metadata Report
    └── Content Coverage
```

**[ADDITIONAL SUGGESTION]**: Add automated metadata extraction from PDF metadata/first pages to reduce manual entry

---

### Phase 1: MVP Launch (Months 1-2)
*Focus: Core productivity tools that justify $20/month subscription*

#### 1. File Upload & Analysis **[DAVID'S REQUIREMENT - #1 Priority]**

**David's Specification:**
- Upload code files (RPG, SQLRPG, CL, SQL, TXT, PDF, DOC)
- AI-driven review and optimization suggestions
- Documentation generation
- Best practices from MC Press content
- Debugging and modernization ideas
- Secure, temporary storage

**Technical Implementation Details:**
- **Backend**: FastAPI endpoint with file type validation
- **Storage**: Temporary S3 bucket with 24-hour auto-deletion
- **Processing**: 
  - PyMuPDF for PDF extraction
  - Custom parsers for RPG/CL/SQL syntax
  - Code analysis using tree-sitter for IBM i languages
- **Security**: 
  - Files encrypted at rest
  - Unique session tokens
  - No permanent storage without explicit user consent
- **Output**: Structured JSON with findings, downloadable report PDF

**[ADDITIONAL SUGGESTION]**: Add diff view showing before/after for modernization suggestions

---

#### 2. Code Generation & Templates **[DAVID'S REQUIREMENT - #2 Priority]**

**David's Specification:**
- Generate IBM i code snippets (RPG, SQL, CL, COBOL)
- Validate syntax against standards
- Editable blocks with syntax highlighting
- Error checking and modern practice suggestions

**Technical Implementation Details:**
- **Template Engine**: Jinja2 for customizable templates
- **Syntax Validation**: 
  - IBM i specific linters
  - Integration with RPGLE language server
- **Code Editor**: Monaco editor (VS Code's editor) embedded
- **Storage**: User template library in PostgreSQL
- **Personalization**: Learn from user's code style preferences

**[ADDITIONAL SUGGESTION]**: Version control for generated templates with Git integration

---

#### 3. Enhanced Book Integration **[DAVID'S REQUIREMENT - E-commerce focus]**

**David's Specification:**
- Seamless "Buy" links within responses
- Direct purchases without leaving chat
- Bundle recommendations based on queries
- Subscriber discounts

**Technical Implementation Details:**
- **MC Store API**: REST integration for real-time pricing/availability
- **Response Enhancement**: Inject purchase CTAs contextually
- **Analytics**: Track conversion from suggestion to purchase
- **Bundling Algorithm**: Collaborative filtering based on purchase patterns

**[ADDITIONAL SUGGESTION]**: "Try before you buy" - show relevant excerpts before purchase

---

#### 4. Conversation History & Basic Organization **[DAVID'S REQUIREMENT - #4 Priority subset]**

**David's Specification:**
- Searchable conversation history
- Bookmarks and notes
- Export capabilities (PDF/CSV)

**Technical Implementation Details:**
- **Database**: PostgreSQL with full-text search on conversations
- **Export Engine**: 
  - WeasyPrint for PDF generation
  - Pandas for CSV/Excel export
- **Search**: Elasticsearch for semantic search across history

---

### Phase 2: Growth Features (Months 3-4)
*Focus: Team collaboration and structured learning*

#### 5. Project Management & Task Organization **[DAVID'S REQUIREMENT - #3 Priority]**

**David's Specification:**
- Organize by projects with folders
- Tag threads and generate summaries
- Track progress with reminders
- Export to Jira/Trello
- AI-assisted prioritization

**Technical Implementation Details:**
- **Project Structure**: PostgreSQL hierarchical data model
- **Integration APIs**: 
  - Jira REST API
  - Trello webhooks
  - Slack/Teams connectors
- **AI Features**: 
  - GPT-4 for summarization
  - Priority scoring based on deadline/complexity

**[ADDITIONAL SUGGESTION]**: Gantt chart visualization for project timelines

---

#### 6. Learning Paths & Interactive Tutorials **[DAVID'S REQUIREMENT - #5 Priority]**

**David's Specification:**
- Personalized curricula via skill assessments
- Quizzes and progressive recommendations
- Progress tracking and certificates
- Guided exercises in simulated environments

**Technical Implementation Details:**
- **Assessment Engine**: Adaptive testing algorithm
- **Simulation Environment**: 
  - Containerized IBM i sandbox
  - Web-based terminal emulator
- **Certificate Generation**: Blockchain-verifiable credentials
- **Progress Tracking**: xAPI/SCORM compliance for LMS integration

**[ADDITIONAL SUGGESTION]**: Peer learning groups and study buddy matching

---

#### 7. Voice Interface **[DAVID'S REQUIREMENT - #6 Priority]**

**David's Specification:**
- Speech-to-text and text-to-speech
- Technical jargon recognition
- Hands-free operation
- Voice-to-book summaries

**Technical Implementation Details:**
- **STT/TTS**: 
  - Whisper API for speech recognition
  - ElevenLabs for natural voice synthesis
- **Custom Vocabulary**: IBM i terminology training dataset
- **Mobile SDK**: React Native for iOS/Android voice features

---

#### 8. Collaboration Tools **[DAVID'S REQUIREMENT - #7 Priority]**

**David's Specification:**
- Share conversations and insights
- Team knowledge bases
- Role-based access
- Community integration

**Technical Implementation Details:**
- **Real-time Sync**: WebSockets for collaborative sessions
- **Permissions**: OAuth2 with RBAC (Role-Based Access Control)
- **Community Features**: 
  - Upvoting system
  - Expert badge system
  - Bounty for answers

**[ADDITIONAL SUGGESTION]**: Screen sharing for pair programming sessions

---

### Phase 3: Enterprise Scale (Months 5-6)
*Focus: Analytics, extensibility, and enterprise features*

#### 9. Advanced Analytics & Insights **[DAVID'S REQUIREMENT - #10 Priority]**

**David's Specification:**
- Usage dashboard with knowledge gaps
- Learning velocity tracking
- Productivity metrics (time saved)
- ROI demonstration

**Technical Implementation Details:**
- **Analytics Stack**: 
  - Metabase for dashboards
  - PostgreSQL TimescaleDB for time-series data
- **Metrics Calculated**:
  - Lines of code reviewed/generated
  - Errors prevented estimation
  - Learning path completion rates
- **Reporting**: Automated monthly ROI reports

**[ADDITIONAL SUGGESTION]**: Benchmark against industry standards

---

#### 10. Smart Notifications & Real-time Updates **[DAVID'S REQUIREMENT - #9 Priority]**

**David's Specification:**
- Proactive alerts for new content
- Topic match notifications
- Automatic content ingestion from MC Press

**Technical Implementation Details:**
- **Notification Service**: 
  - Push notifications via FCM/APNS
  - Email digests via SendGrid
- **Content Pipeline**: 
  - RSS/API monitoring
  - Automatic PDF processing queue
  - Incremental vector database updates

---

#### 11. Integration Capabilities **[DAVID'S REQUIREMENT - #8 Priority]**

**David's Specification:**
- IDE integration (VS Code)
- Slack/Teams integration
- Calendar and CRM connections
- MC Store API

**Technical Implementation Details:**
- **IDE Plugins**:
  - VS Code extension marketplace
  - Eclipse plugin for RDi
- **Chat Integrations**: 
  - Slack app with slash commands
  - Teams bot framework
- **API Gateway**: Kong or AWS API Gateway for rate limiting

**[ADDITIONAL SUGGESTION]**: Jenkins/GitLab CI integration for automated code reviews

---

#### 12. Offline Mode & Mobile App **[DAVID'S REQUIREMENT - #11 Priority]**

**David's Specification:**
- Download content for offline access
- Sync upon reconnection
- Mobile-optimized interface

**Technical Implementation Details:**
- **Mobile Stack**: React Native with SQLite local storage
- **Sync Protocol**: CouchDB/PouchDB for conflict-free sync
- **Offline Content**: Compressed, encrypted local cache

---

## Additional Strategic Suggestions

### [ADDITIONAL SUGGESTION] Features Not in David's List

1. **Knowledge Graph Visualization**
   - Interactive graph showing relationships between concepts
   - Visual learning path navigation
   - Connection discovery between books/articles

2. **AI Code Review Pipeline**
   - GitHub/GitLab webhook integration
   - Automated PR comments with MC Press best practices
   - Security vulnerability scanning

3. **Virtual Study Groups**
   - Scheduled learning sessions with other subscribers
   - Shared whiteboards and code spaces
   - Expert-led office hours

4. **Gamification System**
   - Points for learning milestones
   - Leaderboards (optional/private)
   - Achievement badges tied to MC Press certifications

5. **Custom AI Training**
   - Enterprise tier: Train on company's specific codebase
   - Custom terminology and standards
   - Private model deployment option

---

## Pricing Tiers (From David's Research)

### Tier 1: Individual Professional ($20/month)
- Core chat functionality
- Limited file upload (10 files/day)
- Basic projects (5 active)
- Voice interaction (500 minutes/month)
- Mobile access
- History & notifications

### Tier 2: Team Lead ($35/month)
- Everything in Tier 1
- Unlimited file uploads
- Advanced projects & collaboration
- Custom templates
- All integrations
- Priority support
- Voice (unlimited)

### Tier 3: Enterprise ($60/month)
- Everything in Tier 2
- Full analytics suite
- Custom training data
- API access (10k calls/month)
- Dedicated support
- SLA guarantee
- White-label options

**[ADDITIONAL SUGGESTION]**: Academic tier ($10/month) for students with .edu email

---

## Implementation Timeline

### Month 0 (Pre-Launch Cleanup)
- Remove search feature (1 week)
- Build admin dashboard (2 weeks)
- Metadata cleanup for existing 110+ documents (1 week)

### Month 1
- File Upload & Analysis (backend)
- Code Generation (basic templates)
- History/Export features

### Month 2
- Enhanced MC Store integration
- File Upload UI polish
- Beta launch to 100 users

### Month 3
- Project Management
- Voice Interface (beta)
- Team workspaces

### Month 4
- Learning Paths
- Collaboration tools
- Mobile app (beta)

### Month 5
- Analytics Dashboard
- API Gateway
- Smart Notifications

### Month 6
- Full mobile app launch
- Enterprise features
- Scale to 1000+ users

---

## Success Metrics

### From David's Research:
- User retention rate > 80%
- Average session > 15 minutes
- File uploads per user > 5/week
- Book purchase conversion > 10%

### [ADDITIONAL SUGGESTION] Metrics:
- Code quality improvement score
- Time-to-resolution tracking
- Community engagement rate
- Certification completion rate

---

## Risk Mitigation

### From David's Concerns:
- **Content Quality**: Monthly audits and updates
- **Performance**: Caching and CDN implementation
- **Security**: SOC 2 compliance roadmap
- **Value Perception**: Clear ROI calculator and case studies

### [ADDITIONAL SUGGESTION] Mitigations:
- **Technical Debt**: 20% time allocation for refactoring
- **Scaling Issues**: Kubernetes deployment from day 1
- **Competition**: Patent unique IBM i workflows
- **Churn**: Exit interview automation and win-back campaigns

---

## Next Steps

1. **Immediate Actions (Week 1)**:
   - Remove search functionality from UI and backend
   - Design admin dashboard wireframes
   - Audit current document metadata gaps

2. **Validate with David**: Ensure alignment with business vision
3. **Technical Feasibility**: Spike critical features (file upload, code gen)
4. **User Research**: Survey 50 MC Press customers on feature priorities
5. **MVP Development**: 8-week sprint for Phase 1 features
6. **Beta Program**: Launch with 100 power users from MC Press community

---

## Appendix: Competitive Analysis Summary

Based on David's research, key competitors lack:
- IBM i/RPG specific knowledge
- Direct integration with technical books
- Code validation for legacy languages
- Enterprise IBM i security standards
- MC Press content exclusivity

This positions MC Press Chatbot as the definitive AI assistant for IBM i professionals.

---

*Document Version: 1.0*  
*Last Updated: September 22, 2025*  
*Next Review: After David's feedback*