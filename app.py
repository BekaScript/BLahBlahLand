from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_mail import Mail, Message
import sqlite3
import os
import re
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json

# For PythonAnywhere compatibility, specify the path to your static files
# This assumes your files are in the same directory as app.py
app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)), static_url_path='', template_folder='templates')
CORS(app)

# Use a consistent secret key, not a random one that changes on restart
app.secret_key = 'blahblahland_secret_key'  # For session management

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bekbolsunysmanov07@gmail.com'  # Replace with your Gmail address
app.config['MAIL_PASSWORD'] = 'wdbw xsuu dsaf qkww'     # Replace with your app password
app.config['MAIL_DEFAULT_SENDER'] = ('BlahBlahLand', 'bekbolsunysmanov07@gmail.com')

# Initialize Flask-Mail
mail = Mail(app)

# Database initialization
def init_db():
    # Use absolute path for database to ensure it works correctly
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table with email column
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    # Create contacts table (for user-to-user relationships)
    cursor.execute('''
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    display_name TEXT,
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

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({"success": False, "message": "Message is required"}), 400
    
    try:
        # Call OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer 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",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral/mistral-7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that helps users write messages. Be concise and helpful."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Extract the AI's response
        ai_response = response.json()
        ai_message = ai_response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        return jsonify({
            "success": True, 
            "ai_response": ai_message
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"Error: {str(e)}"
        }), 500

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
    username_or_email = data.get('usernameOrEmail')
    password = data.get('password')
    
    if not username_or_email or not password:
        return jsonify({"success": False, "message": "Username/Email and password are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the input contains @ symbol, which suggests it's an email
    if '@' in username_or_email:
        cursor.execute("SELECT id, username, password FROM users WHERE email = ?", (username_or_email,))
    else:
        cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username_or_email,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['username'] = user[1]  # Always store the username in session
        return jsonify({"success": True, "username": user[1]})
    
    return jsonify({"success": False, "message": "Invalid username/email or password"}), 401


def is_valid_email(email):
    # Regular expression for email validation
    email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_regex.match(email))

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Validate input
    if not username or not email or not password:
        return jsonify({"success": False, "message": "Username, email, and password are required"}), 400
    
    # Validate email format
    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format"}), 400
    
    hashed_password = generate_password_hash(password)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the email is already registered
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Email already registered"}), 409
        
        # Check if the username is already taken
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Username already taken"}), 409
        
        # Insert the new user into the database
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                      (username, email, hashed_password))
        conn.commit()
        
        # Get the new user's ID
        user_id = cursor.lastrowid
        
        # Set session variables
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({"success": True, "message": "Registration successful", "username": username})
    
    except sqlite3.IntegrityError as e:
        return jsonify({"success": False, "message": "Registration failed due to a database error"}), 500
    
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

@app.route('/api/contacts', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    data = request.get_json()
    username = data.get('username')
    display_name = data.get('displayName')
    
    if not username:
        return jsonify({"success": False, "message": "Username is required"}), 400
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, find the user by username or email
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, username))
        contact = cursor.fetchone()
        
        if not contact:
            conn.close()
            return jsonify({"success": False, "message": "User not found"}), 404
        
        contact_id = contact[0]
        
        # Check if trying to add self
        if contact_id == user_id:
            conn.close()
            return jsonify({"success": False, "message": "Cannot add yourself as a contact"}), 400
        
        # Check if contact already exists
        cursor.execute("SELECT id FROM contacts WHERE user_id = ? AND contact_id = ?", 
                      (user_id, contact_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Contact already exists"}), 409
        
        # Add the contact
        cursor.execute("INSERT INTO contacts (user_id, contact_id, display_name) VALUES (?, ?, ?)",
                      (user_id, contact_id, display_name))
        conn.commit()
        
        conn.close()
        return jsonify({"success": True, "message": "Contact added successfully"})
    
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error adding contact: {str(e)}"}), 500

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