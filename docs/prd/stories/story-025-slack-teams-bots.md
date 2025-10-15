# Story: Slack & Microsoft Teams Bot Integration

**Story ID**: STORY-025
**Epic**: EPIC-003 (Collaboration & Learning Platform)
**Type**: New Feature
**Priority**: P1 (High) - **ENTERPRISE REQUIREMENT**
**Points**: 8
**Sprint**: 13-14 (Month 4)
**Status**: Ready for Development

## User Story

**As a** team lead or developer
**I want** to access MC Press Chatbot from Slack/Teams
**So that** I can get IBM i help without leaving my team's communication platform

## Context

Enterprise adoption requires integration with collaboration platforms. Team Lead ($35/month) and Enterprise ($60/month) tiers need workspace features, and Slack/Teams integration is **table stakes** for selling to organizations. This enables:
- Team-based knowledge sharing
- Contextual help in work discussions
- Easier onboarding (no separate tool to learn)
- Network effects (teammates see value, sign up)

## Business Justification

### Enterprise Sales Requirement

**Tier 2 (Team Lead - $35/month) requires:**
- Team workspace ✅ Story-018
- Collaboration tools ✅ Story-018
- **Chat platform integration** ❌ **THIS STORY**

**Tier 3 (Enterprise - $60/month) requires:**
- All Tier 2 features
- Dedicated support
- API access ✅ Story-020
- **Slack/Teams bots** ❌ **THIS STORY**

### Competitive Positioning

| Feature | Stack Overflow for Teams | Notion AI | ChatGPT Team | MC Press (Planned) |
|---------|------------------------|-----------|--------------|-------------------|
| Slack Integration | ✅ | ✅ | ✅ | ✅ **THIS STORY** |
| Teams Integration | ✅ | ❌ | ❌ | ✅ **THIS STORY** |
| IBM i Expertise | ❌ | ❌ | ❌ | ✅ **UNIQUE** |

### User Workflow

**Current (Without Integration):**
1. IBM i question comes up in Slack discussion
2. Developer switches to browser
3. Opens MC Press Chatbot
4. Gets answer
5. Copies back to Slack

**With Integration:**
1. Type `/mcpress How do I handle DB2 locks?` in Slack
2. Bot responds instantly in thread
3. Team sees answer, learns from context
4. No context switching

## Current State

### Existing System
- **Web Chatbot**: Standalone Next.js app
- **VS Code Extension**: Story-024 (IDE integration)
- **API**: FastAPI backend with chat endpoints
- **Team Workspaces**: Story-018 (web-based team features)

### Gap Analysis
- No Slack presence
- No Teams presence
- No shared team conversations in chat platforms
- Can't reach users where they work

## Acceptance Criteria

### Slack Bot Features
- [ ] **Slash Commands**: `/mcpress <question>` to ask questions
- [ ] **App Mentions**: `@MC Press` to invoke bot in channels
- [ ] **Direct Messages**: Private 1:1 conversations with bot
- [ ] **Threaded Responses**: Bot replies in threads (not cluttering channels)
- [ ] **Rich Formatting**: Markdown, code blocks, syntax highlighting
- [ ] **Interactive Buttons**: "Ask Follow-up", "Save to Library", "Buy Book"
- [ ] **Code Sharing**: Upload RPG files for analysis
- [ ] **Channel Permissions**: Control which channels can use bot
- [ ] **Usage Tracking**: Team admin sees usage stats

### Microsoft Teams Features
- [ ] **Bot Commands**: `@MC Press <question>` in channels
- [ ] **Personal Chat**: 1:1 DMs with bot
- [ ] **Adaptive Cards**: Rich interactive responses
- [ ] **File Analysis**: Upload code files in Teams
- [ ] **Meeting Integration**: Access bot during Teams meetings
- [ ] **Tab App**: Dedicated MC Press tab in Teams
- [ ] **Activity Feed**: Notifications for new MC Press content

### Authentication & Access Control
- [ ] **Workspace Authentication**: Link Slack workspace to MC Press team account
- [ ] **User Authentication**: Individual users link MC Press accounts
- [ ] **Permission Levels**: Admin, member, guest roles
- [ ] **Usage Limits**: Enforce tier-based query limits (Tier 2: 100/day, Tier 3: unlimited)
- [ ] **Billing Integration**: Track usage per workspace for billing

### Team Features
- [ ] **Shared Conversations**: Team members see each other's queries (if in same channel)
- [ ] **Knowledge Base**: Save helpful answers to team library
- [ ] **Pinned Answers**: Pin important responses in channels
- [ ] **Search History**: Search past team queries
- [ ] **Analytics**: Team-level usage dashboard

### User Experience
- [ ] **Onboarding**: Setup guide when bot added to workspace
- [ ] **Help Command**: `/mcpress help` shows available commands
- [ ] **Status Indicators**: Show when bot is typing
- [ ] **Error Handling**: Friendly error messages with support links
- [ ] **Rate Limiting**: Graceful handling of rate limits
- [ ] **Offline Mode**: Message when service unavailable

## Technical Design

### Architecture Overview

```
Slack/Teams → Webhook → MC Press Bot Service → MC Press API → Claude AI
                              ↓
                     Team Workspace DB
                              ↓
                     Analytics & Billing
```

### Slack Integration

#### Slack App Manifest

```yaml
display_information:
  name: MC Press Chatbot
  description: AI-powered IBM i development assistant
  background_color: "#878DBC"  # MC Press blue

features:
  bot_user:
    display_name: MC Press
    always_online: true
  slash_commands:
    - command: /mcpress
      description: Ask MC Press Chatbot about IBM i development
      usage_hint: "[question]"
      should_escape: false
  app_home:
    home_tab_enabled: true
    messages_tab_enabled: true

oauth_config:
  scopes:
    bot:
      - channels:history
      - channels:read
      - chat:write
      - commands
      - files:read
      - files:write
      - im:history
      - im:read
      - im:write
      - users:read
      - team:read

settings:
  event_subscriptions:
    bot_events:
      - app_mention
      - message.im
      - file_shared
  interactivity:
    is_enabled: true
  org_deploy_enabled: true
  socket_mode_enabled: false
  token_rotation_enabled: true
```

#### Slack Bot Service (Python)

```python
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

# Initialize Slack app
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# Slash command handler
@slack_app.command("/mcpress")
async def handle_mcpress_command(ack, command, client):
    await ack()  # Acknowledge immediately

    user_id = command["user_id"]
    channel_id = command["channel_id"]
    team_id = command["team_id"]
    text = command["text"]

    # Check if workspace is authorized
    workspace = await get_workspace(team_id)
    if not workspace:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="❌ This workspace hasn't been authorized. Admin needs to link MC Press account."
        )
        return

    # Check user's MC Press account
    user = await get_or_create_user(user_id, team_id)

    # Check rate limits
    if not await check_rate_limit(workspace, user):
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="⚠️ Daily query limit reached. Upgrade to Enterprise for unlimited queries."
        )
        return

    # Show typing indicator
    await client.chat_postMessage(
        channel=channel_id,
        text=f"<@{user_id}> asked: {text}\n_Thinking..._"
    )

    # Query MC Press API
    try:
        response = await mcpress_api.chat(
            user_id=user.mcpress_id,
            message=text,
            context={
                'source': 'slack',
                'workspace': team_id,
                'channel': channel_id
            }
        )

        # Format response with blocks
        blocks = format_slack_response(response)

        # Post response in thread
        await client.chat_postMessage(
            channel=channel_id,
            text=response['message'],
            blocks=blocks,
            thread_ts=command.get('thread_ts')
        )

        # Log analytics
        await log_slack_event(workspace, user, 'slash_command', text)

    except Exception as e:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"❌ Error: {str(e)}\nPlease try again or contact support."
        )

# App mention handler
@slack_app.event("app_mention")
async def handle_app_mention(event, client):
    channel_id = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    text = event["text"].replace(f"<@{slack_app.bot_id}>", "").strip()

    # Similar logic to slash command
    # Post response in thread
    await client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=f"Processing your question: {text}"
    )

    # ... query and respond

# DM handler
@slack_app.event("message")
async def handle_message_events(event, client):
    # Handle direct messages
    if event.get("channel_type") == "im":
        user_id = event["user"]
        text = event["text"]

        # Query MC Press
        response = await mcpress_api.chat(
            user_id=user_id,
            message=text,
            context={'source': 'slack_dm'}
        )

        await client.chat_postMessage(
            channel=event["channel"],
            text=response['message'],
            blocks=format_slack_response(response)
        )

# Interactive button handler
@slack_app.action("ask_followup")
async def handle_followup(ack, action, client):
    await ack()
    # Handle follow-up question
    # ...

# File upload handler
@slack_app.event("file_shared")
async def handle_file_shared(event, client):
    file_id = event["file_id"]
    user_id = event["user_id"]

    # Download file
    file_info = await client.files_info(file=file_id)
    file_content = await download_slack_file(file_info)

    # Analyze with MC Press
    response = await mcpress_api.analyze_code(
        code=file_content,
        filename=file_info["name"]
    )

    # Post analysis
    await client.chat_postMessage(
        channel=event["channel"],
        text=f"📊 Code Analysis for {file_info['name']}",
        blocks=format_code_analysis(response)
    )

def format_slack_response(response: dict) -> list:
    """Format MC Press response as Slack blocks"""

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": response['message']
            }
        }
    ]

    # Add code block if present
    if response.get('code'):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{response.get('language', '')}\n{response['code']}\n```"
            }
        })

    # Add book references
    if response.get('book_references'):
        books = response['book_references']
        book_text = "\n".join([f"• <{b['url']}|{b['title']}>" for b in books])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📚 Recommended Reading:*\n{book_text}"
            }
        })

    # Add interactive buttons
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Ask Follow-up"},
                "action_id": "ask_followup",
                "value": response['conversation_id']
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Save to Library"},
                "action_id": "save_library",
                "value": response['message_id']
            }
        ]
    })

    return blocks
```

### Microsoft Teams Integration

#### Teams Bot Service (Node.js/TypeScript)

```typescript
import { TeamsActivityHandler, TurnContext, CardFactory } from 'botbuilder';

export class MCPressBot extends TeamsActivityHandler {
    constructor() {
        super();

        // Handle messages
        this.onMessage(async (context, next) => {
            const text = context.activity.text.trim();

            // Query MC Press API
            const response = await this.queryMCPress(context, text);

            // Send response as Adaptive Card
            const card = this.createResponseCard(response);
            await context.sendActivity({ attachments: [card] });

            await next();
        });

        // Handle file uploads
        this.onTeamsFileConsent(async (context, next) => {
            const fileContent = await this.downloadFile(context);
            const analysis = await this.analyzecode(fileContent);

            await context.sendActivity(this.createAnalysisCard(analysis));
            await next();
        });
    }

    private createResponseCard(response: any) {
        return CardFactory.adaptiveCard({
            type: 'AdaptiveCard',
            version: '1.4',
            body: [
                {
                    type: 'TextBlock',
                    text: response.message,
                    wrap: true
                },
                {
                    type: 'Container',
                    items: response.code ? [{
                        type: 'TextBlock',
                        text: '```\n' + response.code + '\n```',
                        fontType: 'Monospace',
                        wrap: true
                    }] : []
                },
                {
                    type: 'FactSet',
                    facts: response.book_references?.map(book => ({
                        title: '📚',
                        value: book.title
                    })) || []
                }
            ],
            actions: [
                {
                    type: 'Action.Submit',
                    title: 'Ask Follow-up',
                    data: { action: 'followup', conversationId: response.conversation_id }
                },
                {
                    type: 'Action.OpenUrl',
                    title: 'View in MC Press',
                    url: `https://mcpress-chatbot.com/conversations/${response.conversation_id}`
                }
            ]
        });
    }

    private async queryMCPress(context: TurnContext, message: string) {
        const userId = context.activity.from.id;
        const teamId = context.activity.conversation.id;

        const response = await axios.post('https://api.mcpress-chatbot.com/api/chat', {
            message,
            context: {
                source: 'teams',
                workspace: teamId,
                user: userId
            }
        }, {
            headers: {
                'Authorization': `Bearer ${await this.getTeamToken(teamId)}`
            }
        });

        return response.data;
    }
}
```

### Database Schema

```sql
-- Workspace registrations
CREATE TABLE IF NOT EXISTS chat_platform_workspaces (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,  -- 'slack' or 'teams'
    workspace_id TEXT NOT NULL,  -- Slack team ID or Teams tenant ID
    workspace_name TEXT,
    mcpress_team_id TEXT NOT NULL,  -- References team workspace from Story-018
    tier TEXT NOT NULL,  -- 'team_lead' or 'enterprise'
    query_limit_daily INTEGER,  -- NULL for unlimited (enterprise)
    bot_token_encrypted TEXT NOT NULL,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    installed_by TEXT,
    active BOOLEAN DEFAULT TRUE,
    UNIQUE(platform, workspace_id)
);

-- User mappings
CREATE TABLE IF NOT EXISTS chat_platform_users (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,
    platform_user_id TEXT NOT NULL,
    workspace_id INTEGER NOT NULL,
    mcpress_user_id TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_user_id, workspace_id),
    FOREIGN KEY (workspace_id) REFERENCES chat_platform_workspaces(id) ON DELETE CASCADE
);

-- Usage tracking
CREATE TABLE IF NOT EXISTS chat_platform_usage (
    id BIGSERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    query_type TEXT NOT NULL,  -- 'slash_command', 'mention', 'dm', 'file_upload'
    query_text TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (workspace_id) REFERENCES chat_platform_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES chat_platform_users(id) ON DELETE CASCADE
);

-- Daily usage aggregates (for rate limiting)
CREATE TABLE IF NOT EXISTS workspace_daily_usage (
    workspace_id INTEGER NOT NULL,
    date DATE NOT NULL,
    total_queries INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    PRIMARY KEY (workspace_id, date),
    FOREIGN KEY (workspace_id) REFERENCES chat_platform_workspaces(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_workspace_platform
ON chat_platform_workspaces(platform, workspace_id);

CREATE INDEX IF NOT EXISTS idx_usage_workspace_time
ON chat_platform_usage(workspace_id, timestamp DESC);
```

## Implementation Tasks

### Slack Integration
- [ ] Create Slack app in Slack App Directory
- [ ] Implement slash command handler
- [ ] Build app mention handler
- [ ] Create DM handler
- [ ] Implement file upload handler
- [ ] Build interactive buttons
- [ ] Create Slack block formatting
- [ ] Add OAuth flow for workspace installation
- [ ] Implement rate limiting
- [ ] Build admin dashboard for workspace settings

### Teams Integration
- [ ] Register bot in Azure Bot Service
- [ ] Implement Teams bot handler (Node.js)
- [ ] Create Adaptive Card templates
- [ ] Build file upload handler
- [ ] Implement Teams meeting integration
- [ ] Create Teams tab app
- [ ] Add OAuth for tenant authentication
- [ ] Build activity feed notifications

### Backend Services
- [ ] Create bot service API endpoints
- [ ] Implement workspace authentication
- [ ] Build user mapping system
- [ ] Create rate limiting service
- [ ] Implement usage tracking
- [ ] Build billing integration
- [ ] Create admin APIs for workspace management
- [ ] Add analytics endpoints

### Database & Infrastructure
- [ ] Create database tables
- [ ] Set up encrypted token storage
- [ ] Implement webhook endpoints
- [ ] Configure load balancing for webhooks
- [ ] Set up monitoring and alerts
- [ ] Create backup/disaster recovery

### Admin Dashboard
- [ ] Workspace management UI
- [ ] User mapping interface
- [ ] Usage statistics dashboard
- [ ] Rate limit configuration
- [ ] Billing overview
- [ ] Support tools

### Documentation
- [ ] Installation guide for Slack
- [ ] Installation guide for Teams
- [ ] Admin setup documentation
- [ ] User guide (slash commands, mentions)
- [ ] Troubleshooting guide
- [ ] API documentation

## Testing Requirements

### Unit Tests
- [ ] Slash command parsing
- [ ] Message formatting
- [ ] Rate limit checks
- [ ] User authentication
- [ ] Workspace validation

### Integration Tests
- [ ] End-to-end Slack flow
- [ ] End-to-end Teams flow
- [ ] OAuth flows
- [ ] Webhook handling
- [ ] File uploads

### E2E Tests
- [ ] Install bot to Slack workspace
- [ ] Use slash command
- [ ] Mention bot in channel
- [ ] Send DM to bot
- [ ] Upload file for analysis
- [ ] Click interactive buttons
- [ ] Test rate limits
- [ ] Uninstall and reinstall

### Load Testing
- [ ] Multiple workspaces (100+)
- [ ] Concurrent queries (50+)
- [ ] Large file uploads
- [ ] Sustained usage over time

## Success Metrics

- **Workspace Installs**: 50+ Slack/Teams workspaces in 6 months
- **Active Workspaces**: 70%+ workspaces active monthly
- **Queries per Workspace**: 200+ queries/workspace/month
- **User Adoption**: 40%+ workspace members use bot monthly
- **Tier Upgrades**: 20% of installs upgrade from Team Lead to Enterprise
- **User Satisfaction**: 4+ stars in bot directories

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Slack app published to Slack App Directory
- [ ] Teams bot published to Microsoft AppSource
- [ ] Documentation complete
- [ ] Admin dashboard deployed
- [ ] Rate limiting working correctly
- [ ] Billing integration functional
- [ ] Code reviewed and approved
- [ ] UAT completed with beta workspaces
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- Slack Bolt SDK (Python)
- Microsoft Bot Framework SDK (Node.js)
- Azure Bot Service account
- Existing MC Press API (chat, code analysis)
- Team Workspace system (Story-018)
- Analytics system (Story-019)

## Risks

- **Risk**: Slack/Teams API changes break integration
  - **Mitigation**: Version pinning, comprehensive tests, monitoring

- **Risk**: Low adoption by workspaces
  - **Mitigation**: Strong onboarding, clear value prop, free trial

- **Risk**: Rate limiting too restrictive/permissive
  - **Mitigation**: Adjustable limits, analytics-driven tuning

- **Risk**: Security vulnerabilities in webhook handling
  - **Mitigation**: Request signing validation, security audits

## Future Enhancements

- Discord bot integration
- Google Chat integration
- Workplace from Meta integration
- Mattermost integration
- Custom bot commands per workspace
- Advanced analytics (channel-level insights)
- Bot customization (workspace-specific responses)

---

## Notes

**Enterprise Sales Enabler**: This story is critical for selling Team Lead and Enterprise tiers. Without Slack/Teams integration, we can't compete for enterprise deals where collaboration platform integration is expected.

**Network Effects**: Bot visibility in Slack channels creates organic discovery - teammates see value, ask to join, driving viral growth within organizations.

**Pricing Strategy**: Consider offering first 30 days free for new workspace installs to drive adoption.
