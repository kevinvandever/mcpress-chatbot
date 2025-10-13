# MC Press Chatbot - AI Agent Onboarding Guide

**Project Owner**: Kevin Vandever
**Last Updated**: October 13, 2025
**Purpose**: Quick onboarding for AI agents joining development

---

## 📍 Quick Start Checklist

When starting a new session, read these files in order:

1. **This file** (`ONBOARDING.md`) - You're here! ✅
2. **Tech Stack** (`TECHNOLOGY_STACK.md`) - Architecture & constraints
3. **Agent Persona** (`.bmad-core/agents/dev.yaml`) - Your identity & commands
4. **Current Story** (`docs/prd/stories/story-XXX.md`) - What to build
5. **Work Order** (`docs/recommended-story-work-order.md`) - Story priorities

---

## 🎯 Project Overview

**What**: RAG-powered chatbot for MC Press technical books (IBM i, RPG, modernization)
**Users**: IBM i developers, system administrators
**Content**: 115 technical PDFs (227k+ document chunks with embeddings)

**Stack**:
- **Frontend**: React/TypeScript on Netlify
- **Backend**: FastAPI (Python) on Railway
- **Database**: PostgreSQL 16 + pgvector (384-dim embeddings)
- **AI**: OpenAI GPT-3.5-turbo + sentence-transformers

---

## 📂 Critical Files Reference

### Configuration & Architecture
| File | Purpose | Why Critical |
|------|---------|--------------|
| `TECHNOLOGY_STACK.md` | Full tech stack, architecture, constraints | **READ FIRST** - Prevents breaking production |
| `backend/config.py` | Search thresholds, OpenAI settings | Contains tuned values (don't change blindly) |
| `backend/requirements.txt` | Python dependencies | Update when adding new packages |

### Agent Configuration
| File | Purpose |
|------|---------|
| `.bmad-core/agents/dev.yaml` | Dexter (Dev Agent) full definition |
| `.bmad-core/core-config.yaml` | Project-level BMad config |
| `.bmad-core/tasks/*.md` | Reusable task workflows |
| `.bmad-core/checklists/*.md` | Story completion checklists |

### Product Requirements
| File | Purpose |
|------|---------|
| `docs/prd/epics-and-stories.md` | All 25 stories outlined |
| `docs/prd/stories/story-*.md` | Individual story specifications |
| `docs/recommended-story-work-order.md` | **Optimal build sequence** |

### Key Backend Files
| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app entry point |
| `backend/chat_handler.py` | RAG logic + OpenAI integration |
| `backend/vector_store_postgres.py` | pgvector database operations |
| `backend/pdf_processor_full.py` | PDF extraction + chunking |

---

## 🚨 Critical Constraints (DON'T BREAK THESE)

### 1. Search Thresholds
```python
# backend/config.py
"relevance_threshold": 0.55  # NEVER go above 0.65
```
**Why**: Higher threshold = fewer results (not better quality)
**Tuned for**: 227k document corpus with cosine distance

### 2. Database Schema
```sql
-- DO NOT modify existing tables:
documents       # 227k+ chunks with embeddings
books           # Metadata (Story-004)

-- Safe to add new tables for new features
```

### 3. pgvector Configuration
```python
# MUST use pgvector native operations
# DO NOT add artificial LIMIT 5000
# DO NOT use Python-based similarity calculation
```

### 4. OpenAI Configuration
```python
# Current Railway environment variables:
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.5
OPENAI_MAX_TOKENS=3000

# These can be changed via Railway dashboard without code changes
```

### 5. Brand Colors (Frontend)
```css
--mc-press-navy: #000080;   /* Primary */
--mc-press-coral: #FF6B35;  /* Accent */
```

---

## 📊 Current Project State

### Completed Stories (Ready for Test/Review)
- ✅ **Story-001**: Remove non-functional search
- ✅ **Story-002**: Admin authentication system
- ✅ **Story-003**: PDF upload interface
- ✅ **Story-004**: Metadata management system
- ✅ **Story-005**: Document processing pipeline (feature branch)

### Next Stories (Recommended Order)
- 📋 **Story-006**: File upload for code analysis
- 📋 **Story-007**: AI code analysis engine
- 📋 **Story-008**: Code generation interface
- 📋 **Story-009**: Code template library

See `docs/recommended-story-work-order.md` for full sequence.

### Active Branches
```bash
main                                      # Production (stable)
feature/story-005-doc-processing-pipeline # Story-005 (ready for merge)
```

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────┐
│   Frontend (Netlify)                    │
│   React + TypeScript + Vite             │
│   https://mcpress-chatbot.netlify.app   │
└──────────────┬──────────────────────────┘
               │ HTTPS/REST
               ▼
┌─────────────────────────────────────────┐
│   Backend (Railway)                     │
│   FastAPI + Python 3.11                 │
│   https://mcpress-chatbot-*.railway.app │
│                                         │
│   Endpoints:                            │
│   • /chat - RAG chatbot                │
│   • /upload - PDF processing           │
│   • /documents - List/manage docs      │
│   • /admin/* - Admin operations        │
│   • /api/process/* - Story-005 (new)   │
└──────────────┬──────────────────────────┘
               │ asyncpg
               ▼
┌─────────────────────────────────────────┐
│   Database (Railway PostgreSQL)         │
│   PostgreSQL 16 + pgvector              │
│                                         │
│   Tables:                               │
│   • documents (227k chunks + vectors)   │
│   • books (metadata)                    │
│   • processing_jobs (Story-005)         │
│   • processing_events (Story-005)       │
│   • storage_metrics (Story-005)         │
└─────────────────────────────────────────┘
```

---

## 🎭 Agent Personas

### Dexter 💻 (Full Stack Developer)
**File**: `.bmad-core/agents/dev.yaml`
**Activate**: `/BMad:agents:dev`
**Role**: Code implementation, debugging, testing
**Commands**:
- `*develop-story` - Execute story tasks
- `*run-tests` - Execute linting and tests
- `*explain` - Teaching mode (detailed explanations)
- `*exit` - Exit persona

**Key Rules**:
- ONLY update story Dev Agent Record sections
- Follow develop-story workflow exactly
- Run tests before marking tasks complete
- HALT on blocking issues (ambiguity, dependencies, failures)

---

## 🚀 Common Tasks

### Start New Story Development

```bash
# 1. Read story file
cat docs/prd/stories/story-XXX-{name}.md

# 2. Create feature branch
git checkout -b feature/story-XXX-{short-name}

# 3. Read tech stack constraints
cat TECHNOLOGY_STACK.md

# 4. Implement following story tasks
# 5. Test thoroughly
# 6. Commit with Dexter signature
```

### Commit Message Format

```
type: Brief description

Detailed explanation of changes.

💻 Developed by Dexter (Full Stack Developer Agent)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `deps`

### Test Search Functionality

```bash
# Local test
python3 test_fixes_local.py

# Production test
python3 test_pgvector_chatbot.py
```

### Deploy Changes

**Frontend** (automatic):
```bash
git push origin main  # Netlify auto-deploys in 2-3 min
```

**Backend** (automatic):
```bash
git push origin main  # Railway auto-deploys in ~10 min
```

### Check Deployment Health

```bash
# Backend health
curl https://mcpress-chatbot-production.up.railway.app/health

# Story-005 processing health (if deployed)
curl https://mcpress-chatbot-production.up.railway.app/api/process/health
```

---

## 🐛 Troubleshooting Quick Reference

### Issue: Search returns too few results
**Fix**: Check threshold in `backend/config.py` - should be `0.55`, NOT higher

### Issue: "pgvector not available"
**Fix**: Verify DATABASE_URL points to Railway PostgreSQL with pgvector extension

### Issue: Story file confusion
**Check**: Are you reading from `docs/prd/stories/` (correct) or old location?

### Issue: Tests failing
**Check**:
1. Virtual environment activated?
2. Dependencies installed? (`pip install -r backend/requirements.txt`)
3. DATABASE_URL set? (for integration tests)

---

## 📝 Story Development Workflow

When Kevin asks you to work on a story:

### Phase 1: Research (5 min)
1. Read story file completely
2. Check dependencies (other stories must be complete)
3. Review existing codebase for similar patterns
4. Identify files that need changes

### Phase 2: Plan (5 min)
5. Use TodoWrite to list all tasks
6. Break down complex tasks into subtasks
7. Identify potential blockers

### Phase 3: Implement (varies)
8. Create feature branch
9. Implement tasks sequentially
10. Mark todos as in_progress/completed
11. Write tests for each feature

### Phase 4: Validate (10 min)
12. Run all tests
13. Test end-to-end flow manually
14. Check for regressions
15. Verify story acceptance criteria

### Phase 5: Document & Commit (5 min)
16. Update story file (Dev Agent Record only)
17. Commit with descriptive messages
18. Update README/docs if needed
19. Set story status to "Ready for Review"

---

## 🔒 Security & Secrets

**NEVER commit**:
- `.env` files
- API keys (OpenAI, etc.)
- Database passwords
- Railway tokens

**Safe to commit**:
- `.env.example` (template with placeholders)
- Public URLs
- Configuration templates

---

## 📚 Additional Resources

### External Links
- **Railway Dashboard**: https://railway.app
- **Netlify Dashboard**: https://app.netlify.com
- **OpenAI API**: https://platform.openai.com
- **pgvector Docs**: https://github.com/pgvector/pgvector

### Internal Documentation
- `TECHNOLOGY_STACK.md` - Complete technical reference
- `backend/STORY_005_README.md` - Story-005 deployment guide
- `backend/STORY_005_INTEGRATION.md` - Integration instructions
- Migration guides: `MIGRATION_*.md` (historical reference)

---

## 🎯 Success Metrics

When you complete a story:

- [ ] All acceptance criteria met
- [ ] Tests passing (unit, integration, E2E)
- [ ] No regressions in existing functionality
- [ ] Code follows existing patterns
- [ ] Documentation updated
- [ ] Commits are clean and descriptive
- [ ] Story file Dev Agent Record updated
- [ ] Status set to "Ready for Review"

---

## 💡 Pro Tips for AI Agents

1. **Always read TECHNOLOGY_STACK.md first** - Prevents breaking production configs
2. **Use feature branches** - Keeps main stable, enables easy rollback
3. **TodoWrite is your friend** - Track progress, never forget subtasks
4. **Test before marking complete** - Don't be lazy, run ALL tests
5. **Stay in character** - You're Dexter 💻, not generic Claude
6. **Ask when unclear** - Better to clarify than guess wrong
7. **Commit frequently** - Small commits = easier debugging
8. **Read existing code first** - Match patterns, don't reinvent

---

## 🆘 When You're Stuck

1. **Check story file** - Does it have Dev Notes with hints?
2. **Search codebase** - `grep -r "similar_function" backend/`
3. **Read related stories** - Pattern might be in Story-003 or Story-004
4. **Check git history** - `git log --grep="relevant term"`
5. **Ask Kevin** - He knows the business context best

---

## 📞 Contact

**Project Owner**: Kevin Vandever
**Project Path**: `/Users/kevinvandever/kev-dev/mcpress-chatbot`
**GitHub**: https://github.com/kevinvandever/mcpress-chatbot

---

**Welcome aboard, Agent! Ready to build something great.** 🚀

**Remember**: You're **Dexter 💻**, the Full Stack Developer Agent. Stay in character, follow the workflows, test thoroughly, and we'll ship great code together!

---

**Document Version**: 1.0
**Last Updated**: October 13, 2025
**Maintained By**: Dexter & Kevin
