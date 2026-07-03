import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
from src.config import settings
from src.watchers import GmailWatcher
w = GmailWatcher(settings.vault_path, settings.gmail_client_config_dict, settings.gmail_token_dict)
print('✅ Authenticated')
msgs = w.check_for_updates()
print(f'📬 Unread important emails found: {len(msgs)}')
if msgs:
    print(f'   First email ID: {msgs[0]["id"]}')
