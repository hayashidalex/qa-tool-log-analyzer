import os
from dotenv import load_dotenv

load_dotenv()

FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

LOG_DIR = os.getenv('LOG_DIR')
DB_FILE = os.getenv('DATABASE_PATH')

AUTHORIZED_USERS_FILE = os.getenv('AUTHORIZED_USERS_FILE')
READONLY_USERS_FILE = os.getenv('READONLY_USERS_FILE')
FILES_OFFSETS_PATH = os.getenv('FILES_OFFSETS_PATH')

UNAUTHORIZED_LOG_PATH = 'logs/unauthorized_access.log'
USER_LOGIN_LOG_PATH = 'logs/user_logins.log'

PER_PAGE = 10

ALLOWED_TAGS = ['a', 'br', 'code', 'pre', 'em', 'strong', 'p', 'span']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'span': ['style']
}
