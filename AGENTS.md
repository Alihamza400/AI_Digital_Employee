# AGENTS.md — Personal AI Employee (Hackathon 0)

## Quick start

```bash
uv run python main.py                  # full system
uv run python start_watcher.py          # FileSystemWatcher only
uv run python approve.py                # approval CLI (list/approve/reject)
```

## Python & tooling

- Python 3.12+, managed with **uv** (`uv.lock` + `pyproject.toml`)
- Dev: `uv run ruff check src/`, `uv run black src/`, `uv run pytest`
- Tests live in `main.py --test` (inline unittest) and standalone scripts (`test_gmail.py`, etc.)
- No formal pytest test suite exists yet

## Architecture

**Obsidian vault** (`AI_Employee_Vault/`) is the AI's memory and communication medium. Everything is file-based.

```
Inbox/ → [watchers] → Needs_Action/ → [AI reasoning] → Plans/ + Pending_Approval/
                                                              ↓
                                                        Approved/ → [execution] → Completed/
                                                        Rejected/
```

6 watcher types (all in `src/watchers/`):
- `FileSystemWatcher` — watchdog-based, monitors `Inbox/`
- `GmailWatcher` — Gmail API, polls unread important emails
- `WhatsAppWatcher` — Playwright browser automation
- `LinkedInWatcher` — Playwright + Jinja2 templates
- `AIReasoningWatcher` — watches `Needs_Action/`, triggers `opencode run` as subprocess
- `ApprovalWatcher` — watches Approved/Rejected dirs, executes actions via MCPServer

All extend `BaseWatcher` ABC with `check_for_updates()` + `create_action_file()`.

## OpenCode subagent

**`.opencode/agents/ai-employee.md`** defines the AI reasoning subagent. It:
1. Reads action files from `Needs_Action/`
2. Reads `Company_Handbook.md`, `Business_Goals.md`, `Dashboard.md`
3. Writes a plan to `Plans/PLAN_<id>.md`
4. Creates approval JSON in `Pending_Approval/APPROVAL_<type>_<id>.json`
5. Moves processed file to `Needs_Action/Done/`

Invoked via: `opencode run @ai-employee Process Needs_Action/FILE_xxx.md`

## Vault file conventions

| Pattern | Example |
|---------|---------|
| Action files | `FILE_<name>`, `EMAIL_<id>_<ts>.md`, `WHATSAPP_<chat>_<ts>.md` |
| Approval requests | `APPROVAL_<type>_<id>.json` (in `Pending_Approval/`) |
| Plans | `PLAN_<id>.md` (in `Plans/`) |
| Logs | `YYYY-MM-DD.json` (in `Logs/`, array of action records) |

## Approval workflow

- `approve.py` — CLI: `python approve.py list|show|approve|reject <file>`
- HTTP server on `:8080` — `src/watchers/approval_server.py`
- Both work by **renaming** JSON files between `Pending_Approval/`, `Approved/`, `Rejected/`

## Gotchas

- WhatsApp/LinkedIn require `playwright install` and a valid browser session
- Gmail needs `credentials.json` + `token.json` in vault (OAuth 2.0)
- `ai_reasoning_watcher.py:39` has a bare-word `HAMZA` bug that causes a SyntaxError on import
- `AIReasoningWatcher` calls `opencode run` as a subprocess — requires `opencode` in PATH
- Vault config stored in `AI_Employee_Vault/config.json` (email, approval URL, etc.)
- Tunnel mode: `python main.py --tunnel` creates public URL via localhost.run
- `start_watcher.py` uses `Path.cwd()` — run from repo root
