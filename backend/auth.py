import hashlib
import secrets
from datetime import datetime, timedelta
import json
import os

class UserAuth:
    def __init__(self):
        self.users_file = 'data/users.json'
        self.sessions_file = 'data/sessions.json'
        self._ensure_data_dir()
        self._ensure_users_file()
    
    def _ensure_data_dir(self):
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def _ensure_users_file(self):
        if not os.path.exists(self.users_file):
            default_users = {
                "demo": {
                    "password": self._hash_password("demo123"),
                    "email": "demo@shrine.com",
                    "created_at": datetime.now().isoformat(),
                    "role": "user"
                }
            }
            self._save_users(default_users)
    
    def _hash_password(self, password):
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"{salt}:{hash_obj.hexdigest()}"
    
    def _verify_password(self, password, stored_hash):
        salt, hash_value = stored_hash.split(':')
        new_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return new_hash == hash_value
    
    def _load_users(self):
        with open(self.users_file, 'r') as f:
            return json.load(f)
    
    def _save_users(self, users):
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def _load_sessions(self):
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_sessions(self, sessions):
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
    
    def register(self, username, password, email):
        users = self._load_users()
        if username in users:
            return {'success': False, 'error': 'Username already exists'}
        users[username] = {
            'password': self._hash_password(password),
            'email': email,
            'created_at': datetime.now().isoformat(),
            'role': 'user'
        }
        self._save_users(users)
        return {'success': True, 'message': 'User registered successfully'}
    
    def login(self, username, password):
        users = self._load_users()
        if username not in users:
            return {'success': False, 'error': 'Invalid username or password'}
        if not self._verify_password(password, users[username]['password']):
            return {'success': False, 'error': 'Invalid username or password'}
        session_token = secrets.token_hex(32)
        sessions = self._load_sessions()
        sessions[session_token] = {
            'username': username,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
            'role': users[username]['role']
        }
        self._save_sessions(sessions)
        return {'success': True, 'token': session_token, 'username': username, 'role': users[username]['role']}
    
    def logout(self, token):
        sessions = self._load_sessions()
        if token in sessions:
            del sessions[token]
            self._save_sessions(sessions)
        return {'success': True}
    
    def verify_session(self, token):
        sessions = self._load_sessions()
        if token not in sessions:
            return {'success': False, 'error': 'Invalid session'}
        session = sessions[token]
        expires_at = datetime.fromisoformat(session['expires_at'])
        if expires_at < datetime.now():
            del sessions[token]
            self._save_sessions(sessions)
            return {'success': False, 'error': 'Session expired'}
        return {'success': True, 'username': session['username'], 'role': session['role']}
    
    def get_user_monitoring_history(self, username):
        history_file = f'data/history_{username}.json'
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_monitoring_session(self, username, video_id, video_title, report_data):
        history_file = f'data/history_{username}.json'
        history = self.get_user_monitoring_history(username)
        history.append({
            'timestamp': datetime.now().isoformat(),
            'video_id': video_id,
            'video_title': video_title,
            'report': report_data
        })
        if len(history) > 50:
            history = history[-50:]
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)