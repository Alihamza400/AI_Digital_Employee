# AI Digital Employee

[![CI](https://github.com/Alihamza400/AI_Digital_Employee/actions/workflows/ci.yml/badge.svg)](https://github.com/Alihamza400/AI_Digital_Employee/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![OpenCode](https://img.shields.io/badge/powered%20by-opencode-7C3AED)](https://opencode.ai)

> Autonomous digital employee — monitors email, WhatsApp, and LinkedIn, reasons with AI, and executes actions with human approval.

---

## ✨ Overview

A modular, file-based autonomous agent system that follows the **Perception → Reasoning → Action** pattern:

```
📬 Inbox/ → 👀 Watchers → 🧠 Needs_Action/ → 🤖 AI Reasoning → 📋 Pending_Approval/ → ✅ Human OK → ⚡ Execution → ✅ Done
```

| Layer | Technology | Role |
|---|---|---|
| **Perception** | 6 watchers (File, Gmail, WhatsApp, LinkedIn, AI, Approval) | Detect incoming work from every channel |
| **Reasoning** | [opencode](https://opencode.ai) subagent (`@ai-employee`) | Reads context, writes plans, requests approval |
| **Action** | MCP Server (9 tools) | Executes approved actions (email, WhatsApp, LinkedIn, search, invoice, file ops) |
| **Memory** | Obsidian-compatible vault | File-based: logs, plans, briefings, dashboard |

---

## 🚀 Quick Start

```bash
# 1. Clone & install
uv sync

# 2. Configure secrets
cp .env.example .env
# Fill in Gmail, Calendar, opencode credentials

# 3. Fire it up
uv run python main.py

# 🎉 The AI employee is now running
```

---

## 🏗️ Architecture

### Watchers (Perception Layer)

| Watcher | Source | Method |
|---|---|---|
| `FileSystemWatcher` | Local file drops | watchdog |
| `GmailWatcher` | Gmail inbox | Gmail API (OAuth 2.0) |
| `WhatsAppWatcher` | WhatsApp messages | Playwright browser automation |
| `LinkedInWatcher` | LinkedIn notifications | Playwright + Jinja2 templates |
| `AIReasoningWatcher` | New action files | Spawns `opencode run` subprocess |
| `ApprovalWatcher` | Approved/Rejected dirs | Triggers MCP execution |

All extend `BaseWatcher` ABC with `check_for_updates()` + `create_action_file()`.

### AI Reasoning (Brain)

The `@ai-employee` opencode subagent (`.opencode/agents/ai-employee.md`):

1. Reads action file from `Needs_Action/`
2. Reads `Company_Handbook.md`, `Business_Goals.md`, `Dashboard.md`
3. Writes a plan to `Plans/PLAN_<id>.md`
4. Creates approval JSON in `Pending_Approval/`
5. Moves processed file to `Needs_Action/Done/`

### MCP Server (Action Layer)

| Tool | Description |
|---|---|
| `SEND_EMAIL` | Send via Gmail API |
| `CREATE_DRAFT` | Save as draft |
| `SEND_WHATSAPP` | Playwright WhatsApp Web |
| `POST_LINKEDIN` | LinkedIn post |
| `CREATE_DRAFT_LINKEDIN` | LinkedIn draft |
| `FILE_OPERATION` | Create/delete files |
| `WEB_SEARCH` | DuckDuckGo via Playwright |
| `CREATE_TASK` | Write task file |
| `CREATE_INVOICE` | Generate PDF invoice |
| `SCHEDULE_MEETING` | Google Calendar event |

### Approval Workflow

```
AI writes APPROVAL_<type>_<id>.json → Pending_Approval/
                                        ↓
                              You approve via:
                                • HTTP :8080 (web UI)
                                • approve.py list|approve|reject
                                        ↓
                              Approved/ → MCP Server → executes
```

---

## 🔧 Configuration

All secrets live in `.env` — never committed:

```env
# Gmail
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxx
GMAIL_REFRESH_TOKEN=xxx

# Google Calendar (separate OAuth client)
CALENDAR_CLIENT_ID=xxx.apps.googleusercontent.com
CALENDAR_CLIENT_SECRET=xxx
CALENDAR_REFRESH_TOKEN=xxx

# opencode LLM credentials
# Run: opencode providers login
```

Secrets are reconstructed into credential objects **in memory** at runtime — no files on disk.

---

## 🐳 Docker

```bash
# Build & run
docker compose up --build -d

# Check logs
docker compose logs -f

# Authenticate opencode inside container
docker exec -it hackathon0 opencode providers login
```

- Persistent vault volume for state
- Browser sessions persist across restarts
- `.env` injected at runtime (not in image)

---

## 🛡️ Security

- **No secrets in the repo** — `.env`, `*credentials*.json` are gitignored
- **Human-in-the-loop** — every action requires approval before execution
- **Prompt injection mitigation** — agent system prompt enforces "never execute directly, always request approval"
- **opencode API keys** stored in `~/.config/opencode/` — outside the project tree
- **Browser sessions** (WhatsApp/LinkedIn) gitignored

---

## 📁 Project Structure

```
├── main.py               # System entry point (run this)
├── approve.py            # Approval CLI (list/approve/reject)
├── auth_gmail.py         # Gmail OAuth flow
├── auth_calendar.py      # Calendar OAuth flow
├── setup_sessions.py     # WhatsApp/LinkedIn browser setup
├── pyproject.toml        # Dependencies
├── .env.example          # Secret template (copy → .env)
├── .gitignore
├── README.md
├── AGENTS.md             # Developer onboarding
│
├── Dockerfile            # Production container
├── docker-compose.yml    # One-command deploy
├── entrypoint.sh         # Container init script
│
├── src/
│   ├── config.py         # pydantic-settings
│   ├── scripts/          # Utility scripts
│   │   ├── check_sessions.py
│   │   └── login_linkedin.py
│   └── watchers/
│       ├── base_watcher.py
│       ├── filesystem_watcher.py
│       ├── gmail_watcher.py
│       ├── whatsapp_watcher.py
│       ├── linkedin_watcher.py
│       ├── ai_reasoning_watcher.py
│       ├── approval_watcher.py
│       ├── approval_server.py
│       ├── mcp_server.py      # Action executor (10 tools)
│       ├── scheduler.py
│       └── playwright_manager.py
│
├── LICENSE
├── .github/
│   └── workflows/ci.yml       # CI pipeline (ruff, black)
│
├── .opencode/
│   └── agents/ai-employee.md  # AI reasoning subagent
│
└── AI_Employee_Vault/    # Memory & data store
    ├── Company_Handbook.md
    ├── Business_Goals.md
    ├── Dashboard.md       # Auto-updated every 5 min
    └── LinkedIn_Templates/
```

---

## 🏆 Project Status

- ✅ **Bronze** — File watcher, Obsidian vault, basic AI reasoning
- ✅ **Silver** — Email, WhatsApp, LinkedIn, web search, invoices, scheduler, dashboard
- 🚧 **Gold** — Multi-tenant support, web UI, SMS/Payment integrations
- 🚀 **Cloud** — Dockerized, ready for VPS deployment

---

## 📄 License

MIT — see [LICENSE](LICENSE). Built for [Hackathon 0](https://opencode.ai).
