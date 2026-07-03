"""Re-authenticate Gmail — prints new token values to paste into .env"""
import sys
sys.path.insert(0, '.')
from src.config import settings
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send']

if not settings.gmail_client_config_dict:
    print("❌ GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET not set in .env")
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(settings.gmail_client_config_dict, SCOPES)
print("Open this URL in your browser and log in:\n")
print(flow.authorization_url()[0])
print("\nAfter authorizing, paste the full redirect URL here:")
auth_url = input("URL: ").strip()
flow.fetch_token(authorization_response=auth_url)
creds = flow.credentials

print("\n✅ New token generated. Add these to your .env file:\n")
print(f'GMAIL_REFRESH_TOKEN={creds.refresh_token}')
print('# (Keep GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET the same)')
print()
