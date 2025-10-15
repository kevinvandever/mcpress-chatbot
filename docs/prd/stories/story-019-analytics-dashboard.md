# Story: Advanced Analytics & Insights Dashboard

**Story ID**: STORY-019
**Epic**: EPIC-002 (Core Productivity Suite) - **MOVED FROM EPIC-004**
**Type**: New Feature
**Priority**: P0 (Critical) - **ELEVATED FOR MVP**
**Points**: 8
**Sprint**: 7-8 (Month 2)
**Status**: Ready for Development

## User Story

**As a** subscriber
**I want** to see analytics showing my productivity gains and learning progress
**So that** I can justify my $20/month investment and track my professional growth

## Context

Analytics are **critical for justifying the $20/month subscription price**, especially when competing against free alternatives like Codeium. By demonstrating measurable time savings, productivity improvements, and ROI, we transform the chatbot from a cost center into a proven investment.

This story was **moved from Phase 3 to Phase 1** based on David's feedback emphasizing "value justification for $20/month" as a critical concern.

## Business Justification

### Why This is MVP (Phase 1) vs Post-Launch (Phase 3)

**David's Concern:**
> "Premium pricing demands substantial ROI through time savings and exclusivity; current features risk seeming like an enhanced search engine rather than a transformative tool."

**Competitive Pressure:**
- Codeium is **FREE** with unlimited usage
- ChatGPT Plus is **$20/month** with general AI capabilities
- Users will ask: "Why pay $20 when alternatives exist?"

**Analytics Provides the Answer:**
- Shows **30+ minutes saved per session**
- Tracks **code quality improvements**
- Demonstrates **learning velocity**
- Proves **ROI within first month**

## Current State

### Existing System
- **No usage tracking** beyond basic logging
- **No productivity metrics** visible to users
- **No ROI demonstration** to justify pricing
- **No learning progress tracking**

### Gap Analysis
- Users don't know how much time they're saving
- No data to show chatbot value vs alternatives
- Can't demonstrate skill improvements
- Missing retention driver (users seeing value)

## Acceptance Criteria

### Core Analytics Features
- [ ] **Usage Dashboard** accessible from main navigation
- [ ] **Time Saved Calculator** - estimates hours saved per session
- [ ] **Activity Timeline** - shows daily/weekly/monthly usage patterns
- [ ] **Code Analysis Stats** - files analyzed, lines reviewed, errors caught
- [ ] **Learning Velocity** - topics mastered, progress over time
- [ ] **Query Insights** - most common questions, knowledge gaps identified
- [ ] **ROI Calculator** - shows dollar value of time saved

### Data Visualization
- [ ] **Charts**: Line charts for trends over time
- [ ] **Charts**: Bar charts for category breakdowns
- [ ] **Charts**: Pie charts for language/topic distribution
- [ ] **Progress Rings** - visual goal completion indicators
- [ ] **Comparison View** - current month vs previous month
- [ ] **Benchmark Data** - compare to average MC Press user

### Export & Reporting
- [ ] **PDF Export** - monthly analytics report
- [ ] **CSV Export** - raw data for external analysis
- [ ] **Email Reports** - automated monthly summary emails
- [ ] **Share Report** - shareable link for managers/teams

### Metrics Tracked

#### Productivity Metrics
- [ ] **Time Saved**: Minutes saved per session (calculated)
- [ ] **Sessions Count**: Total chat sessions
- [ ] **Questions Asked**: Total queries answered
- [ ] **Code Files Analyzed**: Files uploaded and reviewed
- [ ] **Code Generated**: Snippets/templates generated
- [ ] **Books Purchased**: Conversions from recommendations

#### Learning Metrics
- [ ] **Topics Explored**: Unique topics discussed
- [ ] **Knowledge Gaps**: Areas needing more learning
- [ ] **MC Press Content Used**: Articles/books referenced
- [ ] **Learning Path Progress**: If enrolled in learning paths
- [ ] **Skill Assessments**: Scores and improvements

#### Engagement Metrics
- [ ] **Active Days**: Days with at least one session
- [ ] **Average Session Length**: Minutes per session
- [ ] **Conversation Depth**: Average messages per conversation
- [ ] **Feature Usage**: Which features used most
- [ ] **Return Rate**: Percentage of days returning

## Technical Design

### Analytics Architecture

```
User Activity → Event Logger → Analytics Processor → Dashboard UI
                     ↓
              TimescaleDB (Time-series data)
                     ↓
              Metrics Calculator (Daily batch job)
                     ↓
              Dashboard API (Real-time queries)
```

### Database Schema

```sql
-- Time-series events table (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS analytics_events (
    id BIGSERIAL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'chat', 'code_analysis', 'code_generation', 'book_view', etc.
    event_data JSONB NOT NULL,
    time_saved_minutes INTEGER DEFAULT 0,  -- Calculated time saved
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('analytics_events', 'timestamp');

-- Daily aggregated metrics
CREATE TABLE IF NOT EXISTS daily_metrics (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_queries INTEGER DEFAULT 0,
    total_time_saved_minutes INTEGER DEFAULT 0,
    code_files_analyzed INTEGER DEFAULT 0,
    code_snippets_generated INTEGER DEFAULT 0,
    books_purchased INTEGER DEFAULT 0,
    topics_explored TEXT[],
    avg_session_length_minutes FLOAT,
    active_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- User lifetime metrics (cached)
CREATE TABLE IF NOT EXISTS user_lifetime_metrics (
    user_id TEXT PRIMARY KEY,
    total_time_saved_hours FLOAT DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_queries INTEGER DEFAULT 0,
    total_code_files INTEGER DEFAULT 0,
    total_generations INTEGER DEFAULT 0,
    total_books_purchased INTEGER DEFAULT 0,
    topics_mastered TEXT[],
    skill_level TEXT DEFAULT 'beginner',
    member_since DATE,
    last_active_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Benchmark data (for comparison)
CREATE TABLE IF NOT EXISTS benchmark_metrics (
    id SERIAL PRIMARY KEY,
    period TEXT NOT NULL,  -- 'monthly', 'weekly'
    period_start DATE NOT NULL,
    avg_time_saved_hours FLOAT,
    avg_sessions INTEGER,
    avg_queries INTEGER,
    avg_files_analyzed INTEGER,
    total_users INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_user_time
ON analytics_events(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_events_type
ON analytics_events(event_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_user_date
ON daily_metrics(user_id, date DESC);
```

### Event Logging Service

```python
class AnalyticsEventLogger:
    """Log user events for analytics"""

    # Time savings estimates (in minutes)
    TIME_SAVINGS = {
        'chat_query': 5,           # vs manual search
        'code_analysis': 15,       # vs manual review
        'code_generation': 20,     # vs writing from scratch
        'file_upload': 10,         # vs copy/paste debugging
        'template_use': 15,        # vs coding manually
        'book_reference': 3,       # vs searching MC Press site
    }

    async def log_event(
        self,
        user_id: str,
        event_type: str,
        event_data: dict
    ):
        """Log analytics event with time savings calculation"""

        # Calculate time saved
        time_saved = self.TIME_SAVINGS.get(event_type, 0)

        # Adjust based on event complexity
        if event_type == 'code_analysis':
            lines_of_code = event_data.get('lines_of_code', 0)
            time_saved = min(60, 15 + (lines_of_code // 100) * 5)

        # Insert event
        await self.db.execute("""
            INSERT INTO analytics_events
            (user_id, event_type, event_data, time_saved_minutes, timestamp)
            VALUES ($1, $2, $3, $4, NOW())
        """, user_id, event_type, event_data, time_saved)

        # Update daily metrics (upsert)
        await self._update_daily_metrics(user_id, event_type, time_saved)
```

### Analytics Calculator Service

```python
class AnalyticsCalculator:
    """Calculate and aggregate analytics metrics"""

    async def calculate_user_analytics(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> dict:
        """Calculate analytics for date range"""

        # Get daily metrics
        daily_data = await self.db.fetch("""
            SELECT * FROM daily_metrics
            WHERE user_id = $1
            AND date BETWEEN $2 AND $3
            ORDER BY date DESC
        """, user_id, start_date, end_date)

        # Get lifetime metrics
        lifetime = await self.db.fetchrow("""
            SELECT * FROM user_lifetime_metrics
            WHERE user_id = $1
        """, user_id)

        # Get benchmark comparison
        benchmarks = await self._get_benchmark_data(start_date, end_date)

        return {
            'time_period': {
                'start': start_date,
                'end': end_date,
                'total_time_saved_hours': sum(d['total_time_saved_minutes'] for d in daily_data) / 60,
                'total_sessions': sum(d['total_sessions'] for d in daily_data),
                'total_queries': sum(d['total_queries'] for d in daily_data),
                'code_files_analyzed': sum(d['code_files_analyzed'] for d in daily_data),
                'code_generated': sum(d['code_snippets_generated'] for d in daily_data),
                'books_purchased': sum(d['books_purchased'] for d in daily_data),
                'avg_session_length': sum(d['avg_session_length_minutes'] for d in daily_data) / len(daily_data) if daily_data else 0,
                'active_days': len(daily_data),
                'topics_explored': self._unique_topics(daily_data),
            },
            'lifetime': {
                'total_time_saved_hours': lifetime['total_time_saved_hours'],
                'member_since': lifetime['member_since'],
                'days_active': (date.today() - lifetime['member_since']).days,
                'total_sessions': lifetime['total_sessions'],
                'skill_level': lifetime['skill_level'],
                'topics_mastered': lifetime['topics_mastered'],
            },
            'roi': self._calculate_roi(daily_data, lifetime),
            'benchmarks': benchmarks,
            'trends': self._calculate_trends(daily_data),
            'knowledge_gaps': await self._identify_knowledge_gaps(user_id),
        }

    def _calculate_roi(self, daily_data: list, lifetime: dict) -> dict:
        """Calculate ROI metrics"""

        subscription_cost_monthly = 20
        hourly_rate = 75  # Estimated developer hourly rate

        # Monthly time saved
        monthly_hours_saved = sum(d['total_time_saved_minutes'] for d in daily_data) / 60
        monthly_value = monthly_hours_saved * hourly_rate
        monthly_roi = ((monthly_value - subscription_cost_monthly) / subscription_cost_monthly) * 100

        # Lifetime
        lifetime_hours_saved = lifetime['total_time_saved_hours']
        days_as_member = (date.today() - lifetime['member_since']).days
        total_paid = (days_as_member / 30) * subscription_cost_monthly
        lifetime_value = lifetime_hours_saved * hourly_rate
        lifetime_roi = ((lifetime_value - total_paid) / total_paid) * 100 if total_paid > 0 else 0

        return {
            'monthly': {
                'hours_saved': monthly_hours_saved,
                'value_generated': monthly_value,
                'cost': subscription_cost_monthly,
                'net_value': monthly_value - subscription_cost_monthly,
                'roi_percentage': monthly_roi,
                'break_even_hours': subscription_cost_monthly / hourly_rate,
            },
            'lifetime': {
                'hours_saved': lifetime_hours_saved,
                'value_generated': lifetime_value,
                'total_cost': total_paid,
                'net_value': lifetime_value - total_paid,
                'roi_percentage': lifetime_roi,
            }
        }

    async def _identify_knowledge_gaps(self, user_id: str) -> list:
        """Identify topics user hasn't explored yet"""

        # Get user's explored topics
        user_topics = await self.db.fetchval("""
            SELECT ARRAY_AGG(DISTINCT topic)
            FROM analytics_events
            WHERE user_id = $1 AND event_data->>'topic' IS NOT NULL
        """, user_id)

        # Get all available topics from MC Press content
        all_topics = await self.db.fetchval("""
            SELECT ARRAY_AGG(DISTINCT category)
            FROM documents
        """)

        # Find gaps
        gaps = [t for t in all_topics if t not in (user_topics or [])]

        return gaps[:10]  # Top 10 gaps
```

### Frontend Components

```typescript
// Dashboard page
interface AnalyticsDashboard {
  timePeriod: {
    start: Date
    end: Date
    totalTimeSavedHours: number
    totalSessions: number
    totalQueries: number
    codeFilesAnalyzed: number
    codeGenerated: number
    booksPurchased: number
    avgSessionLength: number
    activeDays: number
    topicsExplored: string[]
  }
  lifetime: {
    totalTimeSavedHours: number
    memberSince: Date
    daysActive: number
    totalSessions: number
    skillLevel: string
    topicsMastered: string[]
  }
  roi: {
    monthly: ROIMetrics
    lifetime: ROIMetrics
  }
  benchmarks: BenchmarkData
  trends: TrendData
  knowledgeGaps: string[]
}

interface ROIMetrics {
  hoursSaved: number
  valueGenerated: number
  cost: number
  netValue: number
  roiPercentage: number
  breakEvenHours?: number
}
```

### API Endpoints

```python
GET    /api/analytics/dashboard           # Main dashboard data
GET    /api/analytics/daily?start=&end=   # Daily metrics
GET    /api/analytics/lifetime            # Lifetime metrics
GET    /api/analytics/roi                 # ROI calculation
GET    /api/analytics/trends              # Trend analysis
GET    /api/analytics/benchmarks          # Comparison data
GET    /api/analytics/gaps                # Knowledge gaps
POST   /api/analytics/export/pdf          # Export PDF report
POST   /api/analytics/export/csv          # Export CSV data
POST   /api/analytics/email-report        # Request email report
```

## Implementation Tasks

### Backend Tasks
- [ ] Set up TimescaleDB extension for time-series data
- [ ] Create analytics_events hypertable
- [ ] Create daily_metrics aggregation table
- [ ] Create user_lifetime_metrics cache table
- [ ] Implement AnalyticsEventLogger service
- [ ] Create event logging middleware
- [ ] Build AnalyticsCalculator service
- [ ] Implement ROI calculation logic
- [ ] Create daily batch job for metrics aggregation
- [ ] Build knowledge gap identifier
- [ ] Create analytics API endpoints
- [ ] Implement PDF export (WeasyPrint)
- [ ] Build CSV export functionality
- [ ] Create email report service (SendGrid)
- [ ] Add benchmark data calculator

### Frontend Tasks
- [ ] Create `/analytics` dashboard page
- [ ] Build overview statistics cards
- [ ] Implement ROI calculator display
- [ ] Create time saved visualization (line chart)
- [ ] Build activity timeline (bar chart)
- [ ] Create topic distribution (pie chart)
- [ ] Add progress rings for goals
- [ ] Implement date range selector
- [ ] Build comparison view (current vs previous)
- [ ] Create export buttons (PDF/CSV)
- [ ] Add benchmark comparison display
- [ ] Build knowledge gaps widget
- [ ] Create trends visualization
- [ ] Implement email report request UI
- [ ] Add sharing functionality

### Database Tasks
- [ ] Install TimescaleDB extension
- [ ] Create analytics_events table
- [ ] Convert to hypertable
- [ ] Create daily_metrics table
- [ ] Create user_lifetime_metrics table
- [ ] Create benchmark_metrics table
- [ ] Add indexes
- [ ] Create migration script
- [ ] Set up retention policies (keep 1 year of events)

### Integration Tasks
- [ ] Integrate event logging into chat service
- [ ] Add tracking to code analysis service
- [ ] Add tracking to code generation service
- [ ] Add tracking to book purchase flow
- [ ] Wire frontend to analytics API
- [ ] Test PDF export
- [ ] Test CSV export
- [ ] Test email delivery

## Testing Requirements

### Unit Tests
- [ ] Event logging accuracy
- [ ] Time savings calculations
- [ ] ROI calculations
- [ ] Metrics aggregation
- [ ] Knowledge gap identification
- [ ] Trend calculations

### Integration Tests
- [ ] End-to-end event flow
- [ ] Daily aggregation job
- [ ] API endpoint responses
- [ ] PDF generation
- [ ] CSV export format
- [ ] Email delivery

### E2E Tests
- [ ] View dashboard
- [ ] Change date range
- [ ] Export to PDF
- [ ] Export to CSV
- [ ] Request email report
- [ ] View benchmarks
- [ ] See knowledge gaps

## Success Metrics

- **Dashboard Usage**: 70%+ users view dashboard monthly
- **ROI Visibility**: Average $150+ net value shown per user
- **PDF Exports**: 30%+ users export monthly report
- **Email Reports**: 40%+ opt-in to monthly emails
- **Benchmark Engagement**: 50%+ users compare to benchmarks
- **Retention Impact**: 15% higher retention among active dashboard users

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] TimescaleDB optimized for queries
- [ ] Dashboard loads in <2 seconds
- [ ] PDF exports work correctly
- [ ] Email reports deliver successfully
- [ ] ROI calculations validated
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- TimescaleDB extension for PostgreSQL
- Chart library (Chart.js or Recharts)
- PDF generation library (WeasyPrint)
- Email service (SendGrid)
- Existing event tracking infrastructure

## Risks

- **Risk**: Time savings calculations seem inflated
  - **Mitigation**: Conservative estimates, user feedback, adjustment mechanism

- **Risk**: Users don't see enough value to justify $20
  - **Mitigation**: Highlight ROI prominently, show comparisons, testimonials

- **Risk**: Analytics queries slow down database
  - **Mitigation**: TimescaleDB optimization, caching, pre-aggregation

- **Risk**: Users don't engage with analytics
  - **Mitigation**: Prominent placement, email reminders, gamification

## Future Enhancements

- Team analytics (aggregate team performance)
- Goal setting (set time savings targets)
- Achievements and badges
- Social proof (anonymous user comparisons)
- Predictive analytics (forecast savings)
- Integration with time tracking tools
- Custom report builder
- API access for analytics data

---

## Notes

**Critical for Launch**: This story is essential for MVP because it directly addresses David's concern about "value justification for $20/month." Without analytics, users can't see their ROI, making churn likely when competing with free alternatives.

**Positioning**: Analytics should be front and center in marketing materials - "See exactly how much time you're saving every month" - differentiating from competitors who don't provide usage insights.
