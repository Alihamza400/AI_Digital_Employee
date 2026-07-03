"""Authenticate Google Calendar — saves refresh token directly into .env"""
import sys
sys.path.insert(0, '.')
from pathlib import Path
from src.config import settings, CALENDAR_SCOPES
from google_auth_oauthlib.flow import InstalledAppFlow

if not settings.calendar_client_config_dict:
    print("❌ CALENDAR_CLIENT_ID and CALENDAR_CLIENT_SECRET not set in .env")
    print("   Add them from your Google Cloud Console Calendar OAuth client")
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(settings.calendar_client_config_dict, CALENDAR_SCOPES)
print("Open this URL in your browser and log in with Google Calendar access:\n")
print(flow.authorization_url()[0])
print("\nAfter authorizing, paste the full redirect URL here:")
auth_url = input("URL: ").strip()
flow.fetch_token(authorization_response=auth_url)
creds = flow.credentials

# Write directly into .env — parse, update, write back
env_path = Path('.env')
if not env_path.exists():
    print(f"❌ .env not found at {env_path.resolve()}")
    sys.exit(1)

lines = env_path.read_text().splitlines()
new_lines = []
found = False
for line in lines:
    if line.startswith('CALENDAR_REFRESH_TOKEN='):
        new_lines.append(f'CALENDAR_REFRESH_TOKEN={creds.refresh_token}')
        found = True
    else:
        new_lines.append(line)

if not found:
    new_lines.append(f'CALENDAR_REFRESH_TOKEN={creds.refresh_token}')

env_path.write_text('\n'.join(new_lines) + '\n')

print("\n✅ Calendar refresh token saved to .env")
print(f"   CALENDAR_REFRESH_TOKEN={creds.refresh_token[:40]}...")
print('\nTo verify: uv run python -c "from src.config import settings; print(\'Calendar OK:\', settings.calendar_configured)"')
