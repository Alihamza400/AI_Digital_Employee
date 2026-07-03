# Gmail Watcher

## Two Components

### 1. GmailWatcher (monitors inbox)
- **Polling**: checks Gmail every 120s for `is:unread is:important` emails
- **On new email**: extracts headers (From, Subject, Date) + body text
- **Output**: writes a `.md` file to `Needs_Action/` with YAML frontmatter and suggested actions

### 2. GmailSender (sends emails on demand)
- **send_email()**: builds MIME message → base64 encodes → sends via Gmail API
- **create_draft()**: same but saves as draft instead of sending

## OAuth Flow (first-time only)
```
credentials.json ──> browser login ──> token.json (saved for future)
```
`token.json` contains a refresh token — subsequent starts skip the browser.

## File Format Created in Needs_Action/
```
---
type: email
message_id: <id>
from: sender@example.com
subject: "Meeting Request"
priority: high
status: pending
---
## Email Content
...
## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Create task from email
```

## Dependencies
- `google-api-python-client` — REST API wrapper
- `google-auth-oauthlib` — OAuth browser flow
- `google-auth` — token refresh
