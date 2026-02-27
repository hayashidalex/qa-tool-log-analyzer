import os
import logging

from flask import Flask

from config import FLASK_SECRET_KEY, UNAUTHORIZED_LOG_PATH, USER_LOGIN_LOG_PATH, validate
validate()
from app_auth import auth_bp
from routes import main_bp
from db import init_db, ensure_notes_column

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# --- Logging setup ---
os.makedirs('logs', exist_ok=True)

file_handler = logging.FileHandler('logs/app.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

unauth_logger = logging.getLogger('unauthorized_access')
unauth_handler = logging.FileHandler(UNAUTHORIZED_LOG_PATH)
unauth_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
unauth_logger.addHandler(unauth_handler)
unauth_logger.setLevel(logging.INFO)

user_login_logger = logging.getLogger('user_login')
user_login_handler = logging.FileHandler(USER_LOGIN_LOG_PATH)
user_login_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
user_login_logger.addHandler(user_login_handler)
user_login_logger.setLevel(logging.INFO)

# --- Blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# --- DB init at startup ---
with app.app_context():
    init_db()
    ensure_notes_column()

if __name__ == '__main__':
    app.run(
        debug=True,
        host=os.getenv('FLASK_HOST', '127.0.0.1'),
        port=int(os.getenv('FLASK_PORT', 5000))
    )
