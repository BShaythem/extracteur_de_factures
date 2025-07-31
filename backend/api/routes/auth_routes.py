from flask import Blueprint, request, jsonify, session
import sqlite3
import hashlib
import os
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

def init_db():
    """Initialize the SQLite database for users"""
    conn = sqlite3.connect('invoices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        password_hash = hash_password(password)
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                         (username, password_hash))
            conn.commit()
            user_id = cursor.lastrowid
            
            # Log in the user after registration
            session['user_id'] = user_id
            session['username'] = username
            
            return jsonify({
                'message': 'User registered successfully',
                'user': {
                    'id': user_id,
                    'username': username
                }
            }), 201
            
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username already exists'}), 409
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in a user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        password_hash = hash_password(password)
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username FROM users WHERE username = ? AND password_hash = ?', 
                      (username, password_hash))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            user_id, username = user
            session['user_id'] = user_id
            session['username'] = username
            
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user_id,
                    'username': username
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out a user"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    if user_id and username:
        return jsonify({
            'user': {
                'id': user_id,
                'username': username
            }
        }), 200
    else:
        return jsonify({'error': 'Not logged in'}), 401

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function 