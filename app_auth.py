# auth.py

from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from functools import wraps
import json
import os

auth_bp = Blueprint('auth', __name__)

_users_file = os.path.join(os.path.dirname(__file__), 'users.json')
with open(_users_file) as f:
    _users = json.load(f)

_write_users = _users.get('write_users', {})
_read_only_users = _users.get('read_only_users', {})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in _write_users and _write_users[username] == password:
            session['user_id'] = username
            session['read_only'] = False
            return redirect(url_for('main.home_route'))
        elif username in _read_only_users and _read_only_users[username] == password:
            session['user_id'] = username
            session['read_only'] = True
            return redirect(url_for('main.home_route'))
        else:
            flash('Invalid credentials', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
