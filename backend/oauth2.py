import os
import jwt
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

class OAuth2Manager:
    def __init__(self):
        self.google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        self.google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
        self.jwt_secret = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key')
    
    def verify_google_token(self, token):
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Google token verification error: {e}")
            return None
    
    def generate_jwt(self, user_data):
        payload = {
            'user_id': user_data.get('id'),
            'username': user_data.get('username'),
            'email': user_data.get('email'),
            'role': user_data.get('role', 'user'),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_jwt(self, token):
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            if payload['exp'] > datetime.utcnow():
                return payload
            return None
        except Exception as e:
            print(f"JWT verification error: {e}")
            return None
    
    def login_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'No authorization token'}), 401
            
            token = auth_header.replace('Bearer ', '')
            user = self.verify_jwt(token)
            if not user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function

oauth2 = OAuth2Manager()