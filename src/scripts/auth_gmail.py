"""Re-authenticate Gmail — prints new token values to paste into .env"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import settings
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

if not settings.gmail_client_config_dict:
    print("❌ GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET not set in .env")
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(settings.gmail_client_config_dict, SCOPES)
print("A browser window will open for Gmail authorization.\n")
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\n✅ New token generated. Add these to your .env file:\n")
print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
print("# (Keep GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET the same)")
print()
