# AGENTS.md — Personal AI Employee (Hackathon 0)

## Quick start

```bash
cp .env.example .env                     # then set OPENCODE_MODEL + APPROVAL_SECRET
uv run python -m src.scripts.main        # full system
uv run python -m src.scripts.approve     # approval CLI (list/approve/reject)
uv run ai-employee                       # same entry point, via the console script
uv run pytest                            # 67 tests
```

Run everything from the repo root — all paths are CWD-relative.

## Python & tooling

- Python 3.12+, managed with **uv** (`uv.lock` + `pyproject.toml`)
- Dev: `uv run ruff check src/ tests/`, `uv run black src/ tests/`, `uv run pytest`
- CI (`.github/workflows/ci.yml`) runs those exact commands: a `lint` job and a
  `test` job. Both must stay green.
- 67 pytest tests in `tests/` — unit, integration, and a full-system end-to-end run
  (`test_full_system.py`) that boots the real watchers, HTTP approval server and
  executor and drives a file from `Inbox/` through to `Completed/executed/`

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
- `GmailWatcher` — Gmail API, polls unread mail (`is:unread`)
- `WhatsAppWatcher` — Playwright browser automation
- `LinkedInWatcher` — Playwright + Jinja2 templates
- `AIReasoningWatcher` — watches `Needs_Action/`, triggers `opencode run` as subprocess
- `ApprovalWatcher` — watches Approved/Rejected dirs, executes actions via MCPServer

`FileSystemWatcher`, `GmailWatcher`, `WhatsAppWatcher` and `LinkedInWatcher` extend the
`BaseWatcher` ABC (`check_for_updates()` + `create_action_file()`). `AIReasoningWatcher`
and `ApprovalWatcher` are standalone: they are long-running event loops rather than
pollers, so they share no base class.

## OpenCode subagent

**`.opencode/agents/ai-employee.md`** defines the AI reasoning subagent. It:
1. Reads action files from `Needs_Action/`
2. Reads `Company_Handbook.md`, `Business_Goals.md`, `Dashboard.md`
3. Writes a plan to `Plans/PLAN_<id>.md`
4. Creates approval JSON in `Pending_Approval/APPROVAL_<type>_<id>.json`
5. Moves processed file to `Needs_Action/Done/`

Invoked via (see `AIReasoningWatcher._run_opencode`):

```bash
opencode run "<prompt>" --print-logs --format json --auto \
  --agent ai-employee --model <provider>/<model>
```

`--format json` emits an event stream that the watcher parses for `type: "error"`
entries. opencode exits 0 even when the model call itself failed, so the exit code
alone is not a success signal.

## Vault file conventions

| Pattern | Example |
|---------|---------|
| Action files | `FILE_<name>`, `EMAIL_<id>_<ts>.md`, `WHATSAPP_<chat>_<ts>.md` |
| Approval requests | `APPROVAL_<type>_<id>.json` (in `Pending_Approval/`) |
| Plans | `PLAN_<id>.md` (in `Plans/`) |
| Logs | `YYYY-MM-DD.json` (in `Logs/`, array of action records) |

## Approval workflow

- `src/scripts/approve.py` — CLI: `uv run python -m src.scripts.approve list|show|approve|reject <file>`
- HTTP server on `:8080` (`APPROVAL_PORT`) — `src/watchers/approval_server.py`
- Both work by **renaming** JSON files between `Pending_Approval/`, `Approved/`, `Rejected/`
- Setting `APPROVAL_SECRET` requires `?token=<secret>` on **every** endpoint, and the
  notification-email links include it automatically. Without it, anyone who can reach
  the port can approve actions — `main.py` logs a loud warning at startup.

## Gotchas

- WhatsApp/LinkedIn require `playwright install` and a valid browser session
- Gmail needs `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` in
  `.env` — there are no credential files on disk, tokens are rebuilt in memory.
  Generate the refresh token with `uv run python -m src.scripts.auth_gmail`.
  Calendar is the same via the `CALENDAR_*` vars and `src.scripts.auth_calendar`.
- `AIReasoningWatcher` calls `opencode run` as a subprocess — requires `opencode` in PATH
- **`OPENCODE_MODEL` must be set to a funded/available model** (e.g. `google/gemini-3.6-flash`).
  If it is empty, opencode uses its default model, which may be rate-limited or
  unfunded: `opencode run` then retries until `OPENCODE_TIMEOUT` (default 300s) and
  exits without producing a plan or approval request. Check availability with
  `opencode models` and a smoke test: `opencode run --model <model> "Say PONG"`.
- The `ai-employee` subagent is `mode: primary` so `opencode run --agent ai-employee`
  works; `mode: subagent` makes the CLI silently fall back to the default `build` agent
- All configuration lives in `.env` (pydantic-settings — see `src/config.py`).
  `AI_Employee_Vault/config.json` is deprecated and is no longer read.
- `FILE_OPERATION` is confined to the vault directory: a path resolving outside it is
  rejected, so an approved action cannot read, write or delete files on the host.
- Tunnel mode: `uv run python -m src.scripts.main --tunnel` creates public URL via localhost.run
- Run all scripts from repo root so CWD-relative paths work
