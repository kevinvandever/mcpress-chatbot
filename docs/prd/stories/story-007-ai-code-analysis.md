# Story: AI Code Analysis Engine

**Story ID**: STORY-007
**Epic**: EPIC-002 (Core Productivity Suite)
**Type**: New Feature
**Priority**: P0 (Critical)
**Points**: 13
**Sprint**: 5-6
**Status**: Ready for Development

## User Story

**As a** developer
**I want** AI-powered analysis of my IBM i code
**So that** I can improve code quality, security, and modernization

## Context

This is the core value-add feature of Phase 1. By leveraging Claude AI with MC Press knowledge base context, we provide developers with expert-level code review that would typically require consulting or senior developer time. This feature directly justifies subscription pricing.

## Current State

### Existing System
- **Chat Interface**: Q&A with MC Press content (chat_handler.py)
- **Vector Store**: PostgreSQL with pgvector embeddings
- **AI Model**: Claude via Anthropic API
- **Knowledge Base**: 110+ MC Press books embedded
- **Code Upload**: STORY-006 provides file upload capability

### Gap Analysis
- No code analysis capabilities
- No structured analysis framework
- No MC Press best practices validation
- No security vulnerability detection
- No modernization suggestions
- No report generation

## Acceptance Criteria

### Core Analysis Features
- [ ] Best practices validation against MC Press standards
- [ ] Security vulnerability detection (SQL injection, buffer overflow, etc.)
- [ ] Performance optimization suggestions
- [ ] Modernization recommendations (fixed-format → free-format, etc.)
- [ ] MC Press coding standards compliance check
- [ ] Code complexity metrics and warnings

### Report Generation
- [ ] Detailed analysis report with findings
- [ ] Severity-based categorization (Critical, High, Medium, Low, Info)
- [ ] Code snippets showing issues with line numbers
- [ ] Specific improvement suggestions with examples
- [ ] MC Press book references for learning
- [ ] Executive summary for non-technical stakeholders
- [ ] Export report as PDF/Markdown

### User Experience
- [ ] Analysis progress indicators
- [ ] Real-time analysis updates
- [ ] Interactive findings (click to see details)
- [ ] Code comparison (before/after suggestions)
- [ ] Apply suggestions with one click (future enhancement)
- [ ] Share analysis results

## Technical Design

### Analysis Architecture

```
Code Files → Code Analyzer → AI Engine → Report Generator → User Interface
               ↓                ↓              ↓
         Syntax Parser    Vector Search   Formatted Report
         Pattern Match    RAG Context     Downloadable PDF
         Metrics Calc     Claude API      Interactive UI
```

### Code Analysis Service

```python
class CodeAnalysisService:
    """Main service for AI-powered code analysis"""

    def __init__(self, vector_store, claude_client, mc_press_standards):
        self.vector_store = vector_store
        self.claude = claude_client
        self.standards = mc_press_standards

    async def analyze_code(
        self,
        files: List[CodeFile],
        analysis_type: AnalysisType = AnalysisType.COMPREHENSIVE
    ) -> AnalysisReport:
        """Main analysis entry point"""

        # 1. Parse code and extract metrics
        parsed_files = await self._parse_code_files(files)

        # 2. Run static analysis
        static_findings = await self._run_static_analysis(parsed_files)

        # 3. Get relevant MC Press context
        context = await self._get_mc_press_context(parsed_files)

        # 4. Run AI analysis with context
        ai_findings = await self._run_ai_analysis(
            parsed_files, context, static_findings
        )

        # 5. Generate comprehensive report
        report = await self._generate_report(
            files, static_findings, ai_findings, context
        )

        return report
```

### Analysis Types

```python
class AnalysisType(Enum):
    QUICK = "quick"              # Basic checks only (30 seconds)
    STANDARD = "standard"        # Standard analysis (2 minutes)
    COMPREHENSIVE = "comprehensive"  # Deep analysis (5 minutes)
    SECURITY = "security"        # Security-focused
    MODERNIZATION = "modernization"  # Modernization focus
    PERFORMANCE = "performance"  # Performance focus

class FindingSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class FindingCategory(Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"
    MODERNIZATION = "modernization"
    COMPLEXITY = "complexity"
    STYLE = "style"
    BUG = "bug"
```

### Code Parsers

```python
class RPGParser:
    """Parse RPG/RPGLE/SQLRPGLE code"""
    def parse(self, code: str) -> ParsedCode
    def extract_procedures(self, code: str) -> List[Procedure]
    def extract_sql_statements(self, code: str) -> List[SQLStatement]
    def detect_format(self, code: str) -> FormatType  # Fixed vs Free
    def calculate_complexity(self, code: str) -> int

class CLParser:
    """Parse CL/CLLE code"""
    def parse(self, code: str) -> ParsedCode
    def extract_commands(self, code: str) -> List[Command]
    def detect_deprecated_commands(self, code: str) -> List[str]
    def validate_syntax(self, code: str) -> List[SyntaxError]

class SQLParser:
    """Parse SQL code"""
    def parse(self, code: str) -> ParsedCode
    def extract_queries(self, code: str) -> List[Query]
    def detect_injection_risks(self, code: str) -> List[SecurityFinding]
    def optimize_queries(self, code: str) -> List[Optimization]
```

### Static Analysis Checks

```python
class StaticAnalyzer:
    """Run static code analysis"""

    async def analyze(self, parsed_code: ParsedCode) -> List[Finding]:
        findings = []

        # Security checks
        findings.extend(await self._check_sql_injection(parsed_code))
        findings.extend(await self._check_buffer_overflow(parsed_code))
        findings.extend(await self._check_hardcoded_credentials(parsed_code))

        # Performance checks
        findings.extend(await self._check_inefficient_loops(parsed_code))
        findings.extend(await self._check_unnecessary_io(parsed_code))
        findings.extend(await self._check_memory_leaks(parsed_code))

        # Best practices
        findings.extend(await self._check_naming_conventions(parsed_code))
        findings.extend(await self._check_error_handling(parsed_code))
        findings.extend(await self._check_documentation(parsed_code))

        # Complexity
        findings.extend(await self._check_cyclomatic_complexity(parsed_code))
        findings.extend(await self._check_procedure_length(parsed_code))

        return findings
```

### AI Analysis with RAG

```python
class AIAnalyzer:
    """AI-powered analysis using Claude with RAG"""

    async def analyze_with_context(
        self,
        parsed_code: ParsedCode,
        static_findings: List[Finding],
        mc_press_context: str
    ) -> List[Finding]:
        """Run AI analysis with MC Press knowledge base context"""

        prompt = self._build_analysis_prompt(
            parsed_code, static_findings, mc_press_context
        )

        response = await self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,
            temperature=0.3,
            system=self._get_code_analysis_system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse Claude's response into structured findings
        findings = self._parse_ai_response(response.content[0].text)

        return findings

    def _build_analysis_prompt(self, code, findings, context) -> str:
        return f"""
Analyze this IBM i code using MC Press best practices.

CODE:
{code.content}

STATIC ANALYSIS FINDINGS:
{json.dumps([f.dict() for f in findings], indent=2)}

MC PRESS KNOWLEDGE BASE CONTEXT:
{context}

Provide analysis in the following areas:
1. Security vulnerabilities
2. Performance optimizations
3. Modernization opportunities
4. Best practice violations
5. Code complexity issues

For each finding, provide:
- Severity (critical/high/medium/low/info)
- Category
- Description
- Line numbers affected
- Specific recommendation with code example
- Relevant MC Press book references

Format response as JSON array of findings.
"""

    def _get_code_analysis_system_prompt(self) -> str:
        return """You are an expert IBM i developer and code reviewer with deep knowledge of:
- RPG (RPG IV, ILE RPG, free-format RPG)
- SQL (embedded SQL, DB2 for i)
- CL (Control Language)
- MC Press coding standards and best practices
- IBM i security and performance optimization
- Modernization strategies for legacy code

Analyze code thoroughly, provide actionable recommendations, and reference specific MC Press books when relevant.
Be specific with line numbers and code examples.
Prioritize security and critical issues.
"""
```

### MC Press Context Retrieval

```python
class MCPressContextRetriever:
    """Retrieve relevant MC Press content for code analysis"""

    async def get_context_for_code(
        self,
        parsed_code: ParsedCode,
        max_chunks: int = 10
    ) -> str:
        """Get relevant MC Press book context"""

        # Build search queries based on code patterns
        queries = self._generate_queries_from_code(parsed_code)

        # Search vector store for relevant content
        relevant_chunks = []
        for query in queries:
            chunks = await self.vector_store.similarity_search(
                query, k=max_chunks
            )
            relevant_chunks.extend(chunks)

        # Deduplicate and rank by relevance
        ranked_chunks = self._rank_and_deduplicate(relevant_chunks)

        # Build context string
        context = self._build_context_string(ranked_chunks[:max_chunks])

        return context

    def _generate_queries_from_code(self, code: ParsedCode) -> List[str]:
        """Generate search queries based on code patterns"""
        queries = []

        # Detect code patterns and generate queries
        if code.has_embedded_sql:
            queries.append("embedded SQL best practices RPG")
            queries.append("SQL injection prevention IBM i")

        if code.is_fixed_format:
            queries.append("modernize fixed format RPG to free format")

        if code.has_file_operations:
            queries.append("file operations best practices RPG")

        # Add queries based on detected issues
        for finding in code.static_findings:
            if finding.category == FindingCategory.SECURITY:
                queries.append(f"security {finding.pattern} IBM i")

        return queries
```

### Report Generation

```python
class AnalysisReportGenerator:
    """Generate comprehensive analysis reports"""

    def generate_report(
        self,
        files: List[CodeFile],
        findings: List[Finding],
        metrics: CodeMetrics,
        context: MCPressContext
    ) -> AnalysisReport:
        """Generate comprehensive analysis report"""

        # Group findings by severity and category
        grouped_findings = self._group_findings(findings)

        # Generate executive summary
        summary = self._generate_summary(findings, metrics)

        # Create detailed findings sections
        details = self._generate_details(grouped_findings)

        # Add MC Press recommendations
        recommendations = self._generate_recommendations(
            findings, context
        )

        # Create report object
        report = AnalysisReport(
            id=str(uuid.uuid4()),
            files=files,
            summary=summary,
            findings=findings,
            grouped_findings=grouped_findings,
            metrics=metrics,
            recommendations=recommendations,
            mc_press_references=context.book_references,
            created_at=datetime.utcnow()
        )

        return report

    def export_to_pdf(self, report: AnalysisReport) -> bytes:
        """Export report to PDF"""
        # Use reportlab or weasyprint
        pass

    def export_to_markdown(self, report: AnalysisReport) -> str:
        """Export report to Markdown"""
        pass
```

### Database Schema

```sql
-- Code analysis jobs
CREATE TABLE IF NOT EXISTS code_analyses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    total_files INTEGER,
    total_findings INTEGER,
    critical_findings INTEGER,
    high_findings INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis findings
CREATE TABLE IF NOT EXISTS analysis_findings (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    code_snippet TEXT,
    recommendation TEXT,
    mc_press_reference TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES code_analyses(id) ON DELETE CASCADE
);

-- Analysis reports
CREATE TABLE IF NOT EXISTS analysis_reports (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    report_type TEXT NOT NULL, -- 'pdf', 'markdown', 'json'
    content BYTEA NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES code_analyses(id) ON DELETE CASCADE
);

-- Code metrics
CREATE TABLE IF NOT EXISTS code_metrics (
    id SERIAL PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    lines_of_code INTEGER,
    cyclomatic_complexity INTEGER,
    maintainability_index FLOAT,
    comment_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES code_analyses(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_analyses_user
ON code_analyses(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_findings_analysis
ON analysis_findings(analysis_id, severity);

CREATE INDEX IF NOT EXISTS idx_findings_severity
ON analysis_findings(severity, category);
```

### API Endpoints

```python
POST   /api/code/analyze                # Start code analysis
GET    /api/code/analysis/{id}          # Get analysis status
GET    /api/code/analysis/{id}/findings # Get analysis findings
GET    /api/code/analysis/{id}/report   # Get analysis report
POST   /api/code/analysis/{id}/export   # Export report (PDF/MD)
GET    /api/code/analyses               # List user's analyses
DELETE /api/code/analysis/{id}          # Delete analysis
```

## Implementation Tasks

### Backend Tasks
- [ ] Create code parser infrastructure (RPG, CL, SQL)
- [ ] Implement static analysis engine
- [ ] Build AI analysis service with Claude
- [ ] Create MC Press context retrieval system
- [ ] Implement RAG for code analysis
- [ ] Build report generation system
- [ ] Add PDF/Markdown export
- [ ] Create analysis job queue
- [ ] Implement async analysis processing
- [ ] Add comprehensive logging
- [ ] Create analysis API endpoints
- [ ] Build metrics calculation engine

### Frontend Tasks
- [ ] Create `/code-analysis/analyze` page
- [ ] Build analysis progress UI
- [ ] Create findings display component
- [ ] Implement interactive report viewer
- [ ] Add code comparison view (before/after)
- [ ] Build severity-based filtering
- [ ] Create export functionality UI
- [ ] Add share analysis feature
- [ ] Implement finding details modal
- [ ] Create analysis history page
- [ ] Add syntax highlighting for findings

### Database Tasks
- [ ] Create analysis tables
- [ ] Add findings and reports tables
- [ ] Create metrics table
- [ ] Add necessary indexes
- [ ] Create migration script

### Integration Tasks
- [ ] Integrate with STORY-006 (file upload)
- [ ] Connect to existing vector store
- [ ] Wire Claude API for analysis
- [ ] Test RAG context retrieval
- [ ] Validate report generation

## Testing Requirements

### Unit Tests
- [ ] Code parsers (RPG, CL, SQL)
- [ ] Static analysis rules
- [ ] Finding severity calculation
- [ ] Report generation logic
- [ ] PDF/Markdown export

### Integration Tests
- [ ] End-to-end analysis flow
- [ ] RAG context retrieval
- [ ] Claude API integration
- [ ] Multi-file analysis
- [ ] Report persistence

### E2E Tests
- [ ] Upload and analyze single file
- [ ] Analyze multiple files
- [ ] View findings by severity
- [ ] Export report as PDF
- [ ] Share analysis results
- [ ] View analysis history

### Quality Tests
- [ ] Analysis accuracy (manual validation)
- [ ] Security finding detection rate
- [ ] False positive rate
- [ ] MC Press context relevance
- [ ] Report completeness

## Success Metrics

- **Analysis Accuracy**: >90% valid findings
- **False Positive Rate**: <10%
- **Analysis Speed**: <2 minutes for standard analysis
- **Critical Finding Detection**: 100% of known vulnerabilities
- **User Satisfaction**: 4+ stars on analysis quality
- **MC Press Context Relevance**: >80% relevant references

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code reviewed and approved
- [ ] Security review completed
- [ ] Performance tested with large files
- [ ] Analysis accuracy validated
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed by IBM i developers
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- STORY-006 (File Upload) - Must be completed first
- Anthropic Claude API access
- Existing vector store with MC Press content
- PostgreSQL database

## Risks

- **Risk**: Claude API costs too high
  - **Mitigation**: Token optimization, caching, tiered pricing

- **Risk**: Analysis takes too long
  - **Mitigation**: Async processing, progress updates, analysis type options

- **Risk**: False positives frustrate users
  - **Mitigation**: Confidence scoring, user feedback loop, ML refinement

- **Risk**: MC Press context not relevant
  - **Mitigation**: Improve RAG queries, manual context curation

## Future Enhancements

- Apply suggested fixes automatically
- Compare code against industry benchmarks
- Team-wide analysis dashboards
- Custom analysis rules per organization
- Integration with source control (Git)
- Continuous analysis (CI/CD integration)
- Machine learning to improve detection

---

## Notes

This is the flagship feature of Phase 1. Quality and accuracy are critical. Consider beta testing with select IBM i developers before full release.
