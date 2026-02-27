import os
from dotenv import load_dotenv

load_dotenv()

FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

LOG_DIR = os.getenv('LOG_DIR')
DB_FILE = os.getenv('DATABASE_PATH')


UNAUTHORIZED_LOG_PATH = 'logs/unauthorized_access.log'
USER_LOGIN_LOG_PATH = 'logs/user_logins.log'

PER_PAGE = 10

def validate():
    """Fail fast with a clear message if required .env vars are missing or invalid."""
    errors = []

    required = {
        'FLASK_SECRET_KEY': FLASK_SECRET_KEY,
        'LOG_DIR': LOG_DIR,
        'DATABASE_PATH': DB_FILE,
    }
    for name, value in required.items():
        if not value:
            errors.append(f"  {name} is not set")

    if LOG_DIR and not os.path.isdir(LOG_DIR):
        errors.append(f"  LOG_DIR '{LOG_DIR}' does not exist or is not a directory")

    if errors:
        raise RuntimeError(
            "Missing or invalid .env configuration:\n" + "\n".join(errors)
        )


ALLOWED_TAGS = ['a', 'br', 'code', 'pre', 'em', 'strong', 'p', 'span']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'span': ['style']
}
