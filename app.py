import os
import smtplib
import pytz
from datetime import datetime
from email.message import EmailMessage
from typing import List
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func

# --- 1. App Initialization and Configuration ---
app = Flask(__name__) # No longer need template_folder

# Configure CORS to allow requests from your frontend domains
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # Add your production frontend domains here
]
CORS(app, resources={r"/*": {"origins": origins}})

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. Embedded HTML Content ---

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register User</title>
    <style>
        :root {
            --primary-color: #6a5af9; --primary-color-dark: #5a4af7; --background-color: #f3f4f6;
            --form-background: #ffffff; --text-color: #1f2937; --label-color: #4b5563;
            --border-color: #d1d5db; --success-color: #10b981; --error-color: #ef4444;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex; justify-content: center; align-items: center; min-height: 100vh;
            margin: 0; background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%);
        }
        .form-container {
            background-color: var(--form-background); padding: 2.5rem; border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); width: 100%; max-width: 420px;
            box-sizing: border-box; animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        h1 { color: var(--text-color); text-align: center; margin-bottom: 2rem; font-size: 2rem; font-weight: 700; }
        .input-group { margin-bottom: 1.5rem; position: relative; }
        label { display: block; margin-bottom: 0.5rem; color: var(--label-color); font-weight: 500; }
        input[type="text"], input[type="email"] {
            width: 100%; padding: 0.9rem; border: 1px solid var(--border-color); border-radius: 8px;
            box-sizing: border-box; font-size: 1rem; background-color: #f9fafb;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        input[type="text"]:focus, input[type="email"]:focus {
            border-color: var(--primary-color); box-shadow: 0 0 0 3px rgba(106, 90, 249, 0.2); outline: none;
        }
        button {
            width: 100%; padding: 0.9rem; border: none; border-radius: 8px; background-color: var(--primary-color);
            color: white; font-size: 1.1rem; font-weight: 600; cursor: pointer;
            transition: background-color 0.2s, transform 0.1s; display: flex;
            justify-content: center; align-items: center;
        }
        button:hover:not(:disabled) { background-color: var(--primary-color-dark); }
        button:active:not(:disabled) { transform: scale(0.98); }
        button:disabled { background-color: #9ca3af; cursor: not-allowed; }
        .loader {
            width: 18px; height: 18px; border: 2px solid #FFF; border-bottom-color: transparent;
            border-radius: 50%; display: inline-block; box-sizing: border-box;
            animation: rotation 1s linear infinite; margin-right: 10px;
        }
        @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        #message { margin-top: 1.5rem; text-align: center; font-size: 1rem; min-height: 24px; font-weight: 500; }
        .success { color: var(--success-color); }
        .error { color: var(--error-color); }
        .user-counter {
            text-align: center; margin-top: 2rem; padding-top: 1.5rem;
            border-top: 1px solid var(--border-color); color: var(--label-color);
            font-weight: 500; font-size: 0.9rem;
        }
        #userCount { font-weight: 700; color: var(--primary-color); font-size: 1rem; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Join Us</h1>
        <form id="userForm">
            <div class="input-group">
                <label for="name">Full Name</label>
                <input type="text" id="name" name="name" required>
            </div>
            <div class="input-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" required>
            </div>
            <button type="submit" id="submitButton"><span class="button-text">Submit</span></button>
        </form>
        <div id="message"></div>
        <div class="user-counter">Total Subscribed Users: <span id="userCount">...</span></div>
    </div>
    <script>
        const userForm = document.getElementById('userForm');
        const messageDiv = document.getElementById('message');
        const submitButton = document.getElementById('submitButton');
        const buttonText = submitButton.querySelector('.button-text');
        const userCountSpan = document.getElementById('userCount');
        const usersApiUrl = '/users/';
        const countApiUrl = '/users/count';

        async function fetchUserCount() {
            try {
                const response = await fetch(countApiUrl);
                if (response.ok) {
                    const data = await response.json();
                    userCountSpan.textContent = data.count;
                } else { userCountSpan.textContent = 'N/A'; }
            } catch (error) {
                console.error('Could not fetch user count:', error);
                userCountSpan.textContent = 'N/A';
            }
        }
        function showLoading(isLoading) {
            if (isLoading) {
                submitButton.disabled = true;
                buttonText.textContent = 'Submitting...';
                const loader = document.createElement('span');
                loader.className = 'loader';
                submitButton.prepend(loader);
            } else {
                submitButton.disabled = false;
                buttonText.textContent = 'Submit';
                const loader = submitButton.querySelector('.loader');
                if (loader) loader.remove();
            }
        }
        userForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            messageDiv.textContent = '';
            messageDiv.className = '';
            showLoading(true);
            const formData = { name: document.getElementById('name').value, email: document.getElementById('email').value };
            const fetchOptions = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData) };
            try {
                const response = await fetch(usersApiUrl, fetchOptions);
                if (response.ok) {
                    messageDiv.textContent = 'User created successfully!';
                    messageDiv.className = 'success';
                    fetchUserCount();
                    setTimeout(() => { userForm.reset(); messageDiv.textContent = ''; }, 2000);
                } else {
                    const errorData = await response.json();
                    messageDiv.textContent = `Error: ${errorData.error || 'Could not create user.'}`;
                    messageDiv.className = 'error';
                }
            } catch (error) {
                messageDiv.textContent = 'Network Error. Check API status.';
                messageDiv.className = 'error';
            } finally {
                if (!messageDiv.classList.contains('success')) {
                    showLoading(false);
                } else {
                    setTimeout(() => showLoading(false), 2000);
                }
            }
        });
        document.addEventListener('DOMContentLoaded', fetchUserCount);
    </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - Bulk Upload</title>
    <style>
        :root {
            --primary-color: #d9480f; --primary-color-dark: #c9400a; --background-color: #f8f9fa;
            --form-background: #ffffff; --text-color: #212529; --label-color: #495057;
            --border-color: #ced4da; --success-color: #28a745; --error-color: #dc3545;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0; background-color: var(--background-color);
        }
        .admin-container {
            background-color: var(--form-background); padding: 2.5rem; border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); width: 100%; max-width: 600px;
            box-sizing: border-box; animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        h1 { color: var(--text-color); text-align: center; margin-bottom: 1rem; font-size: 2rem; font-weight: 700; }
        p.description { text-align: center; color: var(--label-color); margin-bottom: 2rem; }
        textarea {
            width: 100%; height: 250px; padding: 1rem; border: 1px solid var(--border-color);
            border-radius: 8px; box-sizing: border-box; font-size: 0.9rem;
            font-family: 'Courier New', Courier, monospace; background-color: #f8f9fa;
            resize: vertical; transition: border-color 0.2s, box-shadow 0.2s;
        }
        textarea:focus {
            border-color: var(--primary-color); box-shadow: 0 0 0 3px rgba(217, 72, 15, 0.2); outline: none;
        }
        button {
            width: 100%; padding: 0.9rem; border: none; border-radius: 8px;
            background-color: var(--primary-color); color: white; font-size: 1.1rem;
            font-weight: 600; cursor: pointer; transition: background-color 0.2s, transform 0.1s;
            margin-top: 1rem;
        }
        button:hover:not(:disabled) { background-color: var(--primary-color-dark); }
        #message { margin-top: 1.5rem; text-align: center; font-size: 1rem; min-height: 24px; font-weight: 500; }
        .success { color: var(--success-color); }
        .error { color: var(--error-color); }
    </style>
</head>
<body>
    <div class="admin-container">
        <h1>Bulk Word Upload</h1>
        <p class="description">Paste a JSON array of word objects into the text area below.</p>
        <form id="bulkUploadForm">
            <textarea id="jsonInput" placeholder='[{
  "title": "Immutable",
  "description": "Unchanging over time or unable to be changed.",
  "example": "In many programming languages, strings are immutable.",
   "published_data": "2025-06-16"
}]' required></textarea>
            <button type="submit">Upload Words</button>
        </form>
        <div id="message"></div>
    </div>
    <script>
        const uploadForm = document.getElementById('bulkUploadForm');
        const jsonInput = document.getElementById('jsonInput');
        const messageDiv = document.getElementById('message');
        uploadForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            messageDiv.textContent = '';
            messageDiv.className = '';
            let words;
            try {
                words = JSON.parse(jsonInput.value);
                if (!Array.isArray(words)) throw new Error('Input is not a JSON array.');
                if (words.length === 0) throw new Error('JSON array is empty.');
            } catch (error) {
                messageDiv.textContent = `Invalid JSON: ${error.message}`;
                messageDiv.className = 'error';
                return;
            }
            const apiUrl = '/words/bulk';
            const fetchOptions = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(words) };
            try {
                const response = await fetch(apiUrl, fetchOptions);
                const result = await response.json();
                if (response.ok) {
                    messageDiv.textContent = result.message;
                    messageDiv.className = 'success';
                    jsonInput.value = '';
                } else {
                    messageDiv.textContent = `Error: ${result.error || 'Could not upload words.'}`;
                    messageDiv.className = 'error';
                }
            } catch (error) {
                messageDiv.textContent = 'Network error. Could not connect to the API.';
                messageDiv.className = 'error';
            }
        });
    </script>
</body>
</html>
"""

# --- 3. Database Models (using Flask-SQLAlchemy) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    joined_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'joined_date': self.joined_date.isoformat()}

class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    example = db.Column(db.String(500), nullable=False)
    published_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'title': self.title, 'description': self.description, 'example': self.example, 'published_date': self.published_date.isoformat()}

# --- 4. HTML Page Routes ---
@app.route('/')
def index_page():
    return INDEX_HTML

@app.route('/admin')
def admin_page():
    return ADMIN_HTML


# --- 5. API Endpoints ---
@app.route('/users/', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'error': 'Missing name or email'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    new_user = User(name=data['name'], email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify(new_user.to_dict()), 201

@app.route('/words/', methods=['POST'])
def create_word():
    data = request.get_json()
    if not all(key in data for key in ['title', 'description', 'example']):
        return jsonify({'error': 'Missing required fields'}), 400
    new_word = Word(title=data['title'], description=data['description'], example=data['example'])
    db.session.add(new_word)
    db.session.commit()
    return jsonify(new_word.to_dict()), 201

@app.route('/words/bulk', methods=['POST'])
def create_bulk_words():
    words_data = request.get_json()
    if not isinstance(words_data, list):
        return jsonify({'error': 'Request body must be a list of words'}), 400
    try:
        for word_data in words_data:
            new_word = Word(title=word_data['title'], description=word_data['description'], example=word_data['example'])
            db.session.add(new_word)
        db.session.commit()
        return jsonify({'message': f'Successfully added {len(words_data)} words.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {e}'}), 500

@app.route('/words/', methods=['GET'])
def get_words():
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    words = Word.query.offset(skip).limit(limit).all()
    return jsonify([word.to_dict() for word in words])

@app.route('/words/today', methods=['GET'])
def get_today_word():
    word = Word.query.order_by(Word.published_date.desc()).first()
    if not word:
        return jsonify({'error': 'Word of the day not found'}), 404
    return jsonify(word.to_dict())

@app.route('/users/count', methods=['GET'])
def get_users_count():
    count = db.session.query(func.count(User.id)).scalar()
    return jsonify({'count': count})


# --- 6. Helper Functions & Scheduled Job ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", 2525))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def send_email_to_recipients(subject: str, content: dict, recipients: List[str]):
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL]):
        print("SMTP environment variables not configured. Skipping email job.")
        return

    print(f"Starting email job to send to {len(recipients)} recipients...")
    html_body = f"""
    <html>
      <head></head>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f9f9f9;">
          <h1 style="font-size: 24px; color: #1a1a1a; border-bottom: 2px solid #eee; padding-bottom: 10px;">Word of the Day</h1>
          <h2 style="font-size: 28px; color: #0056b3; margin-top: 20px;">{content['title']}</h2>
          <h3 style="font-size: 16px; color: #333; margin-top: 25px; border-bottom: 1px solid #eee; padding-bottom: 5px;">DESCRIPTION</h3>
          <p style="font-size: 16px;">{content['description']}</p>
          <h3 style="font-size: 16px; color: #333; margin-top: 25px; border-bottom: 1px solid #eee; padding-bottom: 5px;">EXAMPLE</h3>
          <blockquote style="border-left: 4px solid #0056b3; padding-left: 15px; margin-left: 0; font-style: italic; color: #555;">
            {content['example']}
          </blockquote>
          <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
          <p style="color: #888; font-size: 12px; text-align: center;">Have a great day!</p>
        </div>
      </body>
    </html>
    """
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            for recipient in recipients:
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = SENDER_EMAIL
                msg['To'] = recipient
                # Create a plain-text fallback
                plain_text_body = f"Word of the Day: {content['title']}\\nDescription: {content['description']}\\nExample: {content['example']}"
                msg.set_content(plain_text_body)
                msg.add_alternative(html_body, subtype='html')
                server.send_message(msg)
                print(f"Email sent to {recipient}")
        print("Email job finished successfully.")
    except Exception as e:
        print(f"An error occurred while sending emails: {e}")

def send_daily_word_job():
    # app_context is needed to access the database outside of a request
    with app.app_context():
        print(f"Running scheduled job at {datetime.now(pytz.timezone('US/Eastern'))}")
        word_of_day = Word.query.order_by(Word.published_date.desc()).first()
        if not word_of_day:
            print("Job aborted: No word of the day found.")
            return

        users = User.query.all()
        recipient_emails = [user.email for user in users]
        if not recipient_emails:
            print("Job aborted: No users to email.")
            return

        subject = f"Word of the Day: {word_of_day.title}"
        content = word_of_day.to_dict()
        send_email_to_recipients(subject, content, recipient_emails)


# --- 7. Scheduler and App Execution ---
# Initialize the database within the application context
with app.app_context():
    db.create_all()

# This check prevents the scheduler from running twice when Flask is in debug mode
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler(timezone=pytz.timezone('US/Eastern'))
    scheduler.add_job(send_daily_word_job, 'cron', hour=19, minute=27)
    scheduler.start()
    print("Scheduler started.")

if __name__ == '__main__':
    # This runs the Flask development server.
    # For production, use a WSGI server like Gunicorn: gunicorn --bind 0.0.0.0:8000 app:app
    # app.run(debug=True, host='0.0.0.0', port=8000)
    app.run(debug=True, host='0.0.0.0')
