import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
from src.config import settings
from src.watchers import GmailSender

sender = GmailSender(settings.gmail_client_config_dict, settings.gmail_token_dict)
result = sender.send_email(
    to=settings.notify_email or 'you@example.com',
    subject='Test from AI Employee',
    body='This is a test message from the AI Employee system.'
)
print(f'Result: {result}')
