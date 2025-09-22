# MC Press Chatbot - Product Requirements Document (PRD)

**Version:** 1.0  
**Date:** September 22, 2025  
**Stakeholders:** Kevin (Developer), David (Publisher/Business Owner)  
**Project Type:** Brownfield Enhancement

---

## Executive Summary

The MC Press Chatbot is evolving from a basic PDF search tool into a comprehensive AI-powered productivity platform for IBM i professionals. This PRD outlines the transformation roadmap, focusing on immediate technical debt resolution followed by high-value features that justify a tiered subscription model ($20-$60/month).

---

## Problem Statement

### Current Pain Points
1. **Limited Functionality**: Current system only provides basic chat over indexed PDFs
2. **Poor Content Management**: No admin interface for David to manage books/metadata
3. **Broken Features**: Search functionality not working, causing user confusion
4. **Missing Monetization**: No clear value proposition for subscription pricing
5. **Incomplete Data**: 110+ books awaiting upload with missing metadata

### Market Opportunity
- **Target Audience**: 50,000+ IBM i professionals worldwide
- **Unique Position**: Only AI assistant with exclusive MC Press content
- **Revenue Potential**: $20-60/month per user subscription model
- **Competitive Advantage**: Deep IBM i/RPG expertise unavailable elsewhere

---

## Vision & Goals

### Product Vision
Transform MC Press Chatbot into the definitive AI-powered productivity assistant for IBM i developers, providing code analysis, generation, learning paths, and seamless access to MC Press's comprehensive technical library.

### Business Goals
1. **Monthly Recurring Revenue**: Achieve $10k MRR within 6 months
2. **User Retention**: >80% monthly retention rate
3. **Content Monetization**: 10% conversion from chat to book purchases
4. **Market Leadership**: Become the standard AI tool for IBM i development

### User Goals
1. **Save Time**: Reduce debugging and research time by 50%
2. **Improve Code Quality**: Apply MC Press best practices automatically
3. **Continuous Learning**: Structured paths for skill development
4. **Instant Expertise**: Access to 30+ years of MC Press knowledge

---

## User Personas

### Primary Persona: "Senior IBM i Developer"
- **Name**: Sarah, 45, Senior Developer
- **Context**: 15+ years RPG experience, maintaining legacy systems
- **Needs**: Modernization guidance, quick problem solving, best practices
- **Pain Points**: Outdated documentation, time pressure, skill gaps in modern tech
- **Value Prop**: Instant access to solutions, code validation, modernization paths

### Secondary Persona: "IBM i Team Lead"
- **Name**: Marcus, 50, Development Manager
- **Context**: Manages team of 8, responsible for system modernization
- **Needs**: Team training, code standards, project templates
- **Pain Points**: Knowledge silos, inconsistent practices, training costs
- **Value Prop**: Team collaboration, standardized practices, skill development

### Tertiary Persona: "New IBM i Developer"
- **Name**: Alex, 28, Junior Developer
- **Context**: 2 years experience, learning IBM i from modern background
- **Needs**: Learning resources, code examples, mentorship
- **Pain Points**: Steep learning curve, limited resources, legacy complexity
- **Value Prop**: Structured learning, instant help, career development

---

## Functional Requirements

### Phase 0: Technical Debt & Foundation (Month 0)

#### FR-001: Remove Search Feature
- **Priority**: P0 (Critical)
- **Description**: Remove non-functional search UI and backend endpoints
- **Acceptance Criteria**:
  - Search bar removed from UI
  - Search endpoints disabled
  - Routes redirect to chat interface
  - No user-facing errors from removal

#### FR-002: Admin Dashboard
- **Priority**: P0 (Critical)
- **Description**: Create admin interface for content management
- **Acceptance Criteria**:
  - Secure admin authentication (OAuth + MFA)
  - Upload single/batch PDFs with progress indicators
  - Edit document metadata (author, purchase URL, description)
  - Bulk edit capabilities
  - Export/import metadata as CSV
  - Audit trail for all changes

### Phase 1: Core Productivity Features (Months 1-2)

#### FR-003: File Upload & Code Analysis
- **Priority**: P0 (Critical)
- **Description**: Allow users to upload and analyze their code files
- **Acceptance Criteria**:
  - Support RPG, SQLRPGLE, CL, SQL file types
  - AI-driven code review with MC Press best practices
  - Modernization suggestions with examples
  - Security analysis and vulnerability detection
  - Downloadable analysis report
  - Temporary file storage with auto-deletion

#### FR-004: Code Generation & Templates
- **Priority**: P0 (Critical)
- **Description**: Generate IBM i code with best practices
- **Acceptance Criteria**:
  - Generate RPG, SQL, CL, COBOL snippets
  - Syntax validation against IBM i standards
  - Customizable templates
  - Inline editing with syntax highlighting
  - Save templates to user library
  - Export generated code

#### FR-005: Enhanced E-commerce Integration
- **Priority**: P1 (High)
- **Description**: Seamless book purchasing within chat
- **Acceptance Criteria**:
  - "Buy Now" buttons in relevant responses
  - Real-time pricing from MC Store API
  - Bundle recommendations
  - Subscriber discount application
  - Purchase tracking analytics

#### FR-006: Conversation Management
- **Priority**: P1 (High)
- **Description**: Organize and export chat history
- **Acceptance Criteria**:
  - Searchable conversation history
  - Bookmark important responses
  - Add notes to conversations
  - Export to PDF/Markdown
  - Project-based organization

### Phase 2: Collaboration & Learning (Months 3-4)

#### FR-007: Project Management System
- **Priority**: P1 (High)
- **Description**: Organize work by projects and tasks
- **Acceptance Criteria**:
  - Create project folders
  - Tag conversations to projects
  - Generate project documentation
  - Task tracking with reminders
  - Integration with Jira/Trello
  - Team sharing capabilities

#### FR-008: Learning Paths
- **Priority**: P1 (High)
- **Description**: Structured learning curricula
- **Acceptance Criteria**:
  - Skill assessment questionnaires
  - Personalized learning recommendations
  - Progress tracking with milestones
  - Interactive quizzes
  - MC Press completion certificates
  - Hands-on exercises

#### FR-009: Voice Interface
- **Priority**: P2 (Medium)
- **Description**: Voice-enabled interaction
- **Acceptance Criteria**:
  - Speech-to-text for queries
  - Text-to-speech for responses
  - Technical jargon recognition
  - Code dictation support
  - Mobile voice commands

#### FR-010: Team Collaboration
- **Priority**: P2 (Medium)
- **Description**: Enable team knowledge sharing
- **Acceptance Criteria**:
  - Shared workspaces
  - Role-based access control
  - Collaborative annotations
  - Team knowledge base
  - Discussion threads

### Phase 3: Enterprise & Scale (Months 5-6)

#### FR-011: Analytics Dashboard
- **Priority**: P2 (Medium)
- **Description**: Usage and ROI metrics
- **Acceptance Criteria**:
  - Time saved calculations
  - Knowledge gap analysis
  - Query pattern insights
  - Team productivity metrics
  - Custom report generation

#### FR-012: API Access
- **Priority**: P2 (Medium)
- **Description**: Programmatic access to chatbot
- **Acceptance Criteria**:
  - RESTful API endpoints
  - Authentication via API keys
  - Rate limiting
  - Usage tracking
  - Webhook support

#### FR-013: Mobile Application
- **Priority**: P3 (Low)
- **Description**: Native mobile experience
- **Acceptance Criteria**:
  - iOS/Android apps
  - Offline mode with sync
  - Voice-first interface
  - Push notifications
  - Cross-device continuity

---

## Non-Functional Requirements

### Performance
- **NFR-001**: Chat response time < 3 seconds first token
- **NFR-002**: PDF upload processing < 10 seconds per file
- **NFR-003**: Search results < 500ms
- **NFR-004**: 99.9% uptime SLA

### Security
- **NFR-005**: SOC 2 Type II compliance roadmap
- **NFR-006**: Encryption at rest and in transit
- **NFR-007**: MFA for admin access
- **NFR-008**: Regular security audits
- **NFR-009**: GDPR compliance for EU users

### Scalability
- **NFR-010**: Support 1,000 concurrent users
- **NFR-011**: Handle 1M+ documents
- **NFR-012**: Auto-scaling infrastructure
- **NFR-013**: CDN for global performance

### Usability
- **NFR-014**: Mobile-responsive design
- **NFR-015**: WCAG AA accessibility compliance
- **NFR-016**: MC Press brand guidelines adherence
- **NFR-017**: Intuitive onboarding flow

---

## Design Requirements

### Brand Guidelines
- **Primary Blue**: #878DBC (headers, primary buttons)
- **Success Green**: #A1A88B (confirmations, available)
- **CTA Orange**: #EF9537 (Buy Now, highlights)
- **Error Red**: #990000 (warnings, errors)
- **Secondary Gray**: #A3A2A2 (borders, disabled)

### UI/UX Principles
1. **Clarity**: Clear visual hierarchy and purpose
2. **Efficiency**: Minimize clicks to value
3. **Consistency**: Uniform patterns across features
4. **Feedback**: Clear system status and progress
5. **Accessibility**: Keyboard navigation, screen readers

---

## Technical Constraints

### Current Infrastructure
- Railway hosting platform
- Supabase PostgreSQL database
- 500MB storage limit (free tier)
- Node.js 18.x, Python 3.11+

### Integration Requirements
- OpenAI GPT-4 API
- MC Store REST API (future)
- OAuth providers (Google/GitHub)
- Payment processors (Stripe)

### Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Success Metrics

### Key Performance Indicators (KPIs)
1. **User Acquisition**: 500 users in first 3 months
2. **Conversion Rate**: 20% free trial to paid
3. **Monthly Churn**: <5%
4. **Average Revenue Per User**: $35/month
5. **Customer Satisfaction**: >4.5/5 rating

### Usage Metrics
- Daily Active Users (DAU)
- Average session duration > 15 minutes
- Files analyzed per user > 5/week
- Code snippets generated > 10/week
- Book purchases attributed > $10k/month

---

## Pricing Strategy

### Tier Structure

#### Individual Professional ($20/month)
- Core chat functionality
- 10 file uploads/day
- 5 active projects
- 500 voice minutes/month
- Basic history & export

#### Team Lead ($35/month)
- Everything in Individual
- Unlimited file uploads
- Unlimited projects
- Team collaboration (5 seats)
- Priority support
- Advanced analytics

#### Enterprise ($60/month)
- Everything in Team Lead
- Unlimited team seats
- Custom AI training
- API access (10k calls/month)
- SLA guarantee
- White-label options

### Promotional Strategy
- 30-day free trial
- Annual discount (20% off)
- MC Press customer discount (10%)
- Student pricing ($10/month)

---

## Risk Analysis

### Technical Risks
- **Risk**: OpenAI API changes/outages
- **Mitigation**: Implement fallback models, caching

### Business Risks
- **Risk**: Low subscription conversion
- **Mitigation**: Iterative feature testing, user feedback

### Security Risks
- **Risk**: Data breach of uploaded code
- **Mitigation**: Encryption, temporary storage, audit logs

### Market Risks
- **Risk**: Competitor with IBM partnership
- **Mitigation**: Exclusive MC Press content, first-mover advantage

---

## Timeline & Milestones

### Month 0 (Pre-Launch Cleanup)
- Week 1: Remove search feature
- Week 2-3: Build admin dashboard
- Week 4: Metadata cleanup for 110+ documents

### Month 1-2 (MVP Launch)
- File upload & analysis
- Code generation
- E-commerce integration
- Beta launch (100 users)

### Month 3-4 (Growth Features)
- Project management
- Learning paths
- Voice interface
- Public launch

### Month 5-6 (Enterprise Scale)
- Analytics dashboard
- API access
- Mobile apps
- Scale to 1000+ users

---

## Dependencies

### External Dependencies
- OpenAI API availability
- MC Store API development
- Railway platform stability
- Supabase scaling

### Internal Dependencies
- David's content curation
- Marketing campaign readiness
- Support documentation
- Training materials

---

## Open Questions

1. Should we implement our own payment processing or use MC Store's?
2. What level of offline functionality is required for mobile?
3. How much historical chat data should we retain?
4. Should enterprise customers get on-premise deployment options?
5. What integrations are highest priority for enterprise?

---

## Approval & Sign-off

### Stakeholder Approval
- [ ] Kevin (Technical Lead) - Date: ________
- [ ] David (Business Owner) - Date: ________
- [ ] MC Press Team - Date: ________

### Document History
- v1.0 - Initial PRD creation - September 22, 2025

---

## Appendix

### A. Competitive Analysis
- GitHub Copilot: General purpose, no IBM i expertise
- IBM watsonx: Expensive, complex, not RPG-focused
- General AI tools: Lack MC Press content and context

### B. User Research Insights
Based on David's research document and MC Press community feedback

### C. Technical Specifications
See `docs/architecture.md` for detailed technical architecture

### D. Mockups & Wireframes
To be created during design phase

---

*This PRD is a living document and will be updated as requirements evolve and stakeholder feedback is incorporated.*