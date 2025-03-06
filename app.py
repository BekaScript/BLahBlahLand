from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash

# For PythonAnywhere compatibility, specify the path to your static files
# This assumes your files are in the same directory as app.py
app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)), static_url_path='', template_folder='templates')
CORS(app)
# Use a consistent secret key, not a random one that changes on restart
app.secret_key = 'blahblahland_secret_key'  # For session management

# Database initialization
def init_db():
    # Use absolute path for database to ensure it works correctly
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    # Create contacts table (for user-to-user relationships)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        contact_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (contact_id) REFERENCES users (id),
        UNIQUE(user_id, contact_id)
    )
    ''')
    
    # Create messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message_text TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helper function to get db connection with consistent path
def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat.db')
    conn = sqlite3.connect(db_path)
    return conn

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        session['user_id'] = user[0]
        session['username'] = username
        return jsonify({"success": True, "username": username})
    
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"}), 400
    
    hashed_password = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({"success": True, "username": username})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists"}), 409
    finally:
        if conn:
            conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({"success": True})

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT u.id, u.username FROM users u
    JOIN contacts c ON u.id = c.contact_id
    WHERE c.user_id = ?
    ''', (user_id,))
    
    contacts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({"success": True, "contacts": contacts})

@app.route('/api/contacts', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    contact_username = data.get('username')
    
    if not contact_username:
        return jsonify({"success": False, "message": "Contact username required"}), 400
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find the contact's user_id
    cursor.execute("SELECT id FROM users WHERE username = ?", (contact_username,))
    contact = cursor.fetchone()
    
    if not contact:
        conn.close()
        return jsonify({"success": False, "message": "User not found"}), 404
    
    contact_id = contact[0]
    
    # Check if it's the same user
    if user_id == contact_id:
        conn.close()
        return jsonify({"success": False, "message": "Cannot add yourself as a contact"}), 400
    
    try:
        # Add the contact
        cursor.execute("INSERT INTO contacts (user_id, contact_id) VALUES (?, ?)", (user_id, contact_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Contact added"})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "message": "Contact already exists"}), 409

@app.route('/api/messages/<int:contact_id>', methods=['GET'])
def get_messages(contact_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get messages between the two users (in both directions)
    cursor.execute('''
    SELECT m.id, m.sender_id, sender.username as sender_username, 
           m.receiver_id, receiver.username as receiver_username, 
           m.message_text, m.timestamp
    FROM messages m
    JOIN users sender ON m.sender_id = sender.id
    JOIN users receiver ON m.receiver_id = receiver.id
    WHERE (m.sender_id = ? AND m.receiver_id = ?) 
       OR (m.sender_id = ? AND m.receiver_id = ?)
    ORDER BY m.timestamp ASC
    ''', (user_id, contact_id, contact_id, user_id))
    
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({"success": True, "messages": messages})

@app.route('/api/messages', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message_text = data.get('message')
    
    if not receiver_id or not message_text:
        return jsonify({"success": False, "message": "Receiver ID and message required"}), 400
    
    sender_id = session['user_id']
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO messages (sender_id, receiver_id, message_text)
    VALUES (?, ?, ?)
    ''', (sender_id, receiver_id, message_text))
    
    conn.commit()
    
    # Get the inserted message
    cursor.execute('''
    SELECT m.id, m.sender_id, sender.username as sender_username, 
           m.receiver_id, receiver.username as receiver_username, 
           m.message_text, m.timestamp
    FROM messages m
    JOIN users sender ON m.sender_id = sender.id
    JOIN users receiver ON m.receiver_id = receiver.id
    WHERE m.id = ?
    ''', (cursor.lastrowid,))
    
    message = dict(cursor.fetchone())
    conn.close()
    
    return jsonify({"success": True, "message": message})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session or 'username' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    return jsonify({
        "success": True, 
        "user": {
            "id": session['user_id'],
            "username": session['username']
        }
    })

# This route is to help test that Flask is running
@app.route('/hello')
def hello():
    return "Hello from Flask!"

# Add a special route for PythonAnywhere's health checks
@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
