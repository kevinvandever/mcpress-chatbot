# Story: VS Code Extension for MC Press Chatbot

**Story ID**: STORY-024
**Epic**: EPIC-003 (Collaboration & Learning Platform)
**Type**: New Feature
**Priority**: P1 (High) - **COMPETITIVE NECESSITY**
**Points**: 13
**Sprint**: 11-13 (Month 3-4)
**Status**: Ready for Development

## User Story

**As an** IBM i developer using VS Code
**I want** MC Press Chatbot integrated directly into my editor
**So that** I can get AI assistance without context switching

## Context

This is a **critical competitive gap**. GitHub Copilot, Cursor, and Tabnine all provide native IDE integration, while MC Press Chatbot is web-only. This story closes that gap by bringing specialized IBM i expertise directly into VS Code, the increasingly popular editor for RPG development (especially with Code for IBM i extension).

## Business Justification

### Competitive Landscape

| Competitor | IDE Integration | MC Press Advantage |
|------------|----------------|-------------------|
| **GitHub Copilot** | ✅ Native VS Code | ❌ Generic, no IBM i knowledge |
| **Cursor** | ✅ Built on VS Code | ❌ No RPG specialization |
| **Tabnine** | ✅ VS Code plugin | ❌ Autocomplete only, no chat |
| **MC Press Chatbot** | ❌ **WEB ONLY** | ✅ IBM i expertise |

**This Story:** ✅ Native VS Code + ✅ IBM i Expertise = **Unbeatable combination**

### User Pain Point

Current workflow:
1. Write code in VS Code
2. Switch to browser
3. Copy/paste code into chatbot
4. Get response
5. Switch back to VS Code
6. Apply changes

**With extension:**
1. Right-click code → "Analyze with MC Press"
2. Get response in sidebar
3. Apply changes with one click

### Market Opportunity

- **Code for IBM i**: 10,000+ installs (RPG extension for VS Code)
- **Growing adoption**: IBM i shops moving from RDi to VS Code
- **Integration advantage**: Capture users before they discover competitors

## Current State

### Existing System
- **Web App**: Next.js chatbot at mcpress-chatbot.com
- **API**: FastAPI backend with chat endpoints
- **Authentication**: Existing user auth system

### Gap Analysis
- No IDE presence whatsoever
- No code context sharing from editor
- No inline code actions
- Missing where developers spend their time

## Acceptance Criteria

### Core Extension Features
- [ ] **Chat Sidebar** - MC Press chatbot in VS Code sidebar
- [ ] **Context Menu** - Right-click code → "Ask MC Press"
- [ ] **Code Actions** - Quick fixes powered by MC Press AI
- [ ] **Inline Suggestions** - Hover tooltips with MC Press insights
- [ ] **File Upload** - Send current file for analysis
- [ ] **Authentication** - Login with MC Press account
- [ ] **Offline Indicator** - Show connection status

### Context-Aware Features
- [ ] **Current File Context** - Auto-include file in queries
- [ ] **Selection Context** - Send selected code automatically
- [ ] **Project Context** - Understand workspace structure
- [ ] **Language Detection** - Identify RPG/CL/SQL automatically
- [ ] **Error Context** - Parse VS Code problems panel
- [ ] **Git Context** - Include recent changes if relevant

### Code Application
- [ ] **Apply Changes** - One-click code replacement
- [ ] **Diff View** - Show before/after comparison
- [ ] **Partial Apply** - Select which suggestions to apply
- [ ] **Undo Support** - Easy rollback
- [ ] **Multi-file Changes** - Apply across multiple files

### User Experience
- [ ] **Search Commands** - Cmd+Shift+P → "MC Press: Ask Question"
- [ ] **Keyboard Shortcuts** - Customizable shortcuts
- [ ] **Status Bar** - Show usage stats (queries today, time saved)
- [ ] **Settings Panel** - Configure API key, preferences
- [ ] **Welcome Page** - Getting started guide
- [ ] **Code Snippets** - Insert MC Press templates

## Technical Design

### Extension Architecture

```
VS Code Extension (TypeScript)
    ↓
Extension Host (Node.js)
    ↓
MC Press API (FastAPI)
    ↓
Claude AI + Vector Store
```

### VS Code Extension Structure

```
mcpress-vscode/
├── src/
│   ├── extension.ts           # Main entry point
│   ├── chatPanel.ts           # Sidebar chat UI
│   ├── codeActions.ts         # Context menu actions
│   ├── apiClient.ts           # MC Press API client
│   ├── authProvider.ts        # Authentication
│   ├── codeAnalyzer.ts        # Code context extraction
│   ├── diffApplicator.ts      # Apply code changes
│   ├── statusBar.ts           # Status bar item
│   └── commands/
│       ├── askQuestion.ts
│       ├── analyzeCode.ts
│       ├── generateCode.ts
│       └── explainError.ts
├── media/
│   ├── icons/
│   └── styles/
├── package.json               # Extension manifest
├── tsconfig.json
└── README.md
```

### Extension Manifest (package.json)

```json
{
  "name": "mcpress-chatbot",
  "displayName": "MC Press Chatbot",
  "description": "AI-powered IBM i development assistant with MC Press expertise",
  "version": "1.0.0",
  "publisher": "mcpress",
  "engines": {
    "vscode": "^1.80.0"
  },
  "categories": [
    "Programming Languages",
    "Machine Learning",
    "Snippets"
  ],
  "keywords": [
    "IBM i",
    "RPG",
    "AS/400",
    "AI",
    "chatbot",
    "assistant"
  ],
  "activationEvents": [
    "onLanguage:rpgle",
    "onLanguage:sqlrpgle",
    "onLanguage:cl",
    "onCommand:mcpress.askQuestion"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "viewsContainers": {
      "activitybar": [
        {
          "id": "mcpress",
          "title": "MC Press",
          "icon": "media/mcpress-icon.svg"
        }
      ]
    },
    "views": {
      "mcpress": [
        {
          "type": "webview",
          "id": "mcpress.chatView",
          "name": "Chat"
        },
        {
          "id": "mcpress.historyView",
          "name": "History"
        }
      ]
    },
    "commands": [
      {
        "command": "mcpress.askQuestion",
        "title": "MC Press: Ask Question",
        "category": "MC Press"
      },
      {
        "command": "mcpress.analyzeCode",
        "title": "MC Press: Analyze Selected Code",
        "category": "MC Press"
      },
      {
        "command": "mcpress.generateCode",
        "title": "MC Press: Generate Code",
        "category": "MC Press"
      },
      {
        "command": "mcpress.explainError",
        "title": "MC Press: Explain Error",
        "category": "MC Press"
      },
      {
        "command": "mcpress.login",
        "title": "MC Press: Login",
        "category": "MC Press"
      }
    ],
    "menus": {
      "editor/context": [
        {
          "when": "editorHasSelection",
          "command": "mcpress.analyzeCode",
          "group": "mcpress@1"
        },
        {
          "when": "editorHasSelection",
          "command": "mcpress.askQuestion",
          "group": "mcpress@2"
        }
      ]
    },
    "keybindings": [
      {
        "command": "mcpress.askQuestion",
        "key": "ctrl+shift+m",
        "mac": "cmd+shift+m"
      },
      {
        "command": "mcpress.analyzeCode",
        "key": "ctrl+shift+a",
        "mac": "cmd+shift+a",
        "when": "editorHasSelection"
      }
    ],
    "configuration": {
      "title": "MC Press Chatbot",
      "properties": {
        "mcpress.apiKey": {
          "type": "string",
          "default": "",
          "description": "MC Press API Key"
        },
        "mcpress.apiEndpoint": {
          "type": "string",
          "default": "https://api.mcpress-chatbot.com",
          "description": "API Endpoint"
        },
        "mcpress.autoIncludeContext": {
          "type": "boolean",
          "default": true,
          "description": "Automatically include file context in queries"
        },
        "mcpress.maxContextLines": {
          "type": "number",
          "default": 500,
          "description": "Maximum lines of context to send"
        }
      }
    }
  },
  "dependencies": {
    "axios": "^1.6.0",
    "marked": "^11.0.0"
  },
  "devDependencies": {
    "@types/vscode": "^1.80.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0",
    "@vscode/test-electron": "^2.3.0"
  }
}
```

### Main Extension Code (extension.ts)

```typescript
import * as vscode from 'vscode';
import { ChatPanelProvider } from './chatPanel';
import { ApiClient } from './apiClient';
import { AuthProvider } from './authProvider';
import { StatusBarManager } from './statusBar';

export async function activate(context: vscode.ExtensionContext) {
    console.log('MC Press Chatbot extension activated');

    // Initialize services
    const authProvider = new AuthProvider(context);
    const apiClient = new ApiClient(authProvider);
    const statusBar = new StatusBarManager();

    // Register chat panel
    const chatProvider = new ChatPanelProvider(context.extensionUri, apiClient);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('mcpress.chatView', chatProvider)
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('mcpress.askQuestion', async () => {
            const question = await vscode.window.showInputBox({
                prompt: 'Ask MC Press Chatbot',
                placeHolder: 'How do I read a database file in RPG?'
            });

            if (question) {
                const context = await getEditorContext();
                await chatProvider.sendMessage(question, context);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('mcpress.analyzeCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;

            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showWarningMessage('Please select code to analyze');
                return;
            }

            const language = editor.document.languageId;
            await chatProvider.sendMessage(
                'Analyze this code for best practices and improvements',
                {
                    code: selection,
                    language: language,
                    fileName: editor.document.fileName
                }
            );
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('mcpress.generateCode', async () => {
            const template = await vscode.window.showQuickPick([
                'Read Database File',
                'CRUD Operations',
                'REST API Consumer',
                'Error Handler',
                'CL Command'
            ], {
                placeHolder: 'Select a code template'
            });

            if (template) {
                await chatProvider.sendMessage(
                    `Generate ${template} code template`,
                    { template }
                );
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('mcpress.explainError', async () => {
            const diagnostics = vscode.languages.getDiagnostics();
            const editor = vscode.window.activeTextEditor;

            if (editor && diagnostics.length > 0) {
                const fileDiagnostics = diagnostics.find(
                    ([uri]) => uri.toString() === editor.document.uri.toString()
                );

                if (fileDiagnostics) {
                    const [, diags] = fileDiagnostics;
                    const errorMessages = diags.map(d => d.message).join('\n');

                    await chatProvider.sendMessage(
                        'Explain these errors and how to fix them',
                        {
                            errors: errorMessages,
                            code: editor.document.getText()
                        }
                    );
                }
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('mcpress.login', async () => {
            await authProvider.login();
        })
    );

    // Add status bar
    statusBar.show();
    context.subscriptions.push(statusBar);

    // Check authentication on startup
    if (!await authProvider.isAuthenticated()) {
        const login = await vscode.window.showInformationMessage(
            'Login to MC Press Chatbot to get started',
            'Login'
        );
        if (login) {
            await authProvider.login();
        }
    }
}

async function getEditorContext(): Promise<any> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return null;

    const config = vscode.workspace.getConfiguration('mcpress');
    const autoInclude = config.get<boolean>('autoIncludeContext', true);

    if (!autoInclude) return null;

    const document = editor.document;
    const maxLines = config.get<number>('maxContextLines', 500);
    const totalLines = document.lineCount;

    let contextText = document.getText();
    if (totalLines > maxLines) {
        // Include selection context + surrounding lines
        const selection = editor.selection;
        const startLine = Math.max(0, selection.start.line - 50);
        const endLine = Math.min(totalLines, selection.end.line + 50);
        const range = new vscode.Range(startLine, 0, endLine, 0);
        contextText = document.getText(range);
    }

    return {
        fileName: document.fileName,
        language: document.languageId,
        code: contextText,
        selection: editor.selection.isEmpty ? null : document.getText(editor.selection)
    };
}

export function deactivate() {
    console.log('MC Press Chatbot extension deactivated');
}
```

### Chat Panel (Webview)

```typescript
export class ChatPanelProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _apiClient: ApiClient
    ) {}

    public resolveWebviewView(webviewView: vscode.WebviewView) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage':
                    await this.handleMessage(data.message, data.context);
                    break;
                case 'applyCode':
                    await this.applyCodeToEditor(data.code);
                    break;
            }
        });
    }

    public async sendMessage(message: string, context?: any) {
        if (!this._view) return;

        // Show message in chat
        this._view.webview.postMessage({
            type: 'userMessage',
            message: message
        });

        // Call API
        try {
            const response = await this._apiClient.chat(message, context);

            this._view.webview.postMessage({
                type: 'assistantMessage',
                message: response.message,
                code: response.code,
                references: response.references
            });
        } catch (error) {
            vscode.window.showErrorMessage(`MC Press Error: ${error.message}`);
        }
    }

    private async applyCodeToEditor(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const selection = editor.selection;
        await editor.edit(editBuilder => {
            if (selection.isEmpty) {
                // Insert at cursor
                editBuilder.insert(selection.start, code);
            } else {
                // Replace selection
                editBuilder.replace(selection, code);
            }
        });

        vscode.window.showInformationMessage('Code applied successfully');
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        // Return HTML for chat interface
        // Similar to existing web chatbot UI
        return `<!DOCTYPE html>
        <html>
        <head>
            <style>
                /* Chat UI styles */
            </style>
        </head>
        <body>
            <div id="chat-container">
                <div id="messages"></div>
                <div id="input-area">
                    <input type="text" id="message-input" placeholder="Ask MC Press..." />
                    <button id="send-btn">Send</button>
                </div>
            </div>
            <script>
                const vscode = acquireVsCodeApi();
                // Chat UI logic
            </script>
        </body>
        </html>`;
    }
}
```

### API Client

```typescript
export class ApiClient {
    private baseUrl: string;
    private apiKey: string;

    constructor(private authProvider: AuthProvider) {
        const config = vscode.workspace.getConfiguration('mcpress');
        this.baseUrl = config.get<string>('apiEndpoint', 'https://api.mcpress-chatbot.com');
    }

    async chat(message: string, context?: any): Promise<ChatResponse> {
        const token = await this.authProvider.getToken();

        const response = await axios.post(`${this.baseUrl}/api/chat`, {
            message,
            context,
            source: 'vscode-extension'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        return response.data;
    }

    async analyzeCode(code: string, language: string): Promise<AnalysisResponse> {
        const token = await this.authProvider.getToken();

        const response = await axios.post(`${this.baseUrl}/api/code-analysis`, {
            code,
            language,
            source: 'vscode-extension'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        return response.data;
    }
}
```

## Backend Changes Required

### New API Endpoints

```python
# Add to existing FastAPI backend

@router.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest,
    user: User = Depends(get_current_user)
):
    """Handle chat from web or VS Code extension"""

    # Track source
    source = request.source  # 'web' or 'vscode-extension'

    # Log analytics event
    await analytics.log_event(
        user_id=user.id,
        event_type='chat_query',
        event_data={
            'source': source,
            'has_context': request.context is not None
        }
    )

    # Process chat normally
    response = await chat_service.process_message(
        user_id=user.id,
        message=request.message,
        context=request.context
    )

    return response

# Extension-specific endpoint
@router.get("/api/extension/status")
async def extension_status(user: User = Depends(get_current_user)):
    """Get user's extension usage stats"""

    stats = await db.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE event_data->>'source' = 'vscode-extension') as extension_queries,
            COUNT(*) FILTER (WHERE event_data->>'source' = 'web') as web_queries
        FROM analytics_events
        WHERE user_id = $1
        AND timestamp > NOW() - INTERVAL '30 days'
    """, user.id)

    return {
        'extension_queries': stats['extension_queries'],
        'web_queries': stats['web_queries'],
        'primary_source': 'extension' if stats['extension_queries'] > stats['web_queries'] else 'web'
    }
```

## Implementation Tasks

### Extension Development
- [ ] Set up VS Code extension project (TypeScript)
- [ ] Implement chat webview panel
- [ ] Build API client with authentication
- [ ] Create context menu commands
- [ ] Implement code actions provider
- [ ] Build status bar integration
- [ ] Add keyboard shortcuts
- [ ] Create settings page
- [ ] Implement code diff applicator
- [ ] Build welcome/onboarding view
- [ ] Add error handling
- [ ] Create extension icon and branding

### Backend Integration
- [ ] Add 'source' tracking to analytics
- [ ] Create extension-specific endpoints
- [ ] Implement extension usage stats
- [ ] Add rate limiting for extension
- [ ] Test authentication flow
- [ ] Document API for extension use

### Publishing
- [ ] Create VS Code Marketplace account
- [ ] Prepare extension README
- [ ] Create demo screenshots/GIFs
- [ ] Write changelog
- [ ] Package extension (.vsix)
- [ ] Submit to marketplace
- [ ] Set up CI/CD for updates

### Documentation
- [ ] Installation guide
- [ ] Getting started tutorial
- [ ] Keyboard shortcuts reference
- [ ] Troubleshooting guide
- [ ] API documentation

## Testing Requirements

### Unit Tests
- [ ] API client tests
- [ ] Context extraction tests
- [ ] Code applicator tests
- [ ] Authentication flow tests

### Integration Tests
- [ ] End-to-end chat flow
- [ ] Code analysis flow
- [ ] Code generation flow
- [ ] Multi-file operations

### E2E Tests (Extension)
- [ ] Install and activate extension
- [ ] Login with MC Press account
- [ ] Send chat message
- [ ] Analyze selected code
- [ ] Generate code template
- [ ] Apply code changes
- [ ] Check status bar updates

### Manual Testing
- [ ] Test with Code for IBM i extension
- [ ] Verify RPG syntax highlighting compatibility
- [ ] Test with large files
- [ ] Test offline behavior
- [ ] Verify keyboard shortcuts

## Success Metrics

- **Extension Installs**: 500+ in first 3 months
- **Active Users**: 60%+ monthly active rate
- **Usage vs Web**: 30%+ of queries from extension within 6 months
- **Retention**: 80%+ of installers stay active
- **Reviews**: 4+ stars average rating
- **Conversion**: 25%+ of free users upgrade after installing extension

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Extension published to VS Code Marketplace
- [ ] Backend API supports extension
- [ ] Documentation complete
- [ ] Demo video created
- [ ] Marketing materials ready
- [ ] Code reviewed and approved
- [ ] UAT completed with beta users
- [ ] Analytics tracking confirmed

## Dependencies

- VS Code Extension API
- Existing MC Press backend API
- Authentication system
- Analytics infrastructure

## Risks

- **Risk**: Extension doesn't meet performance expectations
  - **Mitigation**: Optimize API calls, implement caching, async operations

- **Risk**: Low adoption from RDi users
  - **Mitigation**: Also build RDi Eclipse plugin (future story), market to Code for IBM i users first

- **Risk**: Extension approval delayed by VS Code marketplace
  - **Mitigation**: Follow all guidelines, prepare early, have contingency

- **Risk**: Users prefer web interface
  - **Mitigation**: Make extension complementary, not replacement, sync conversations

## Future Enhancements

- Eclipse/RDi plugin (Story-027)
- Inline code completions (like Copilot)
- Multi-file refactoring
- Test generation
- Code review automation
- Git integration (PR comments)
- Team chat sync

---

## Notes

**Competitive Necessity**: This story directly addresses the #1 competitive gap identified in the competitor analysis. Without IDE integration, MC Press risks losing users to Copilot/Cursor despite superior IBM i knowledge.

**Go-to-Market**: Announce extension launch to Code for IBM i community, position as "Copilot for IBM i developers"
