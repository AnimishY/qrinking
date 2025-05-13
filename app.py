from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import qrcode
import uuid
import os
import datetime
import mysql.connector
from mysql.connector import Error
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# We no longer need to store QR images, but keep the data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'use_pure': True,  # Use pure Python implementation
}

# Add SSL if required
if os.getenv('DB_SSL', 'False').lower() == 'true':
    DB_CONFIG['ssl_disabled'] = False

# Database connection functions
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def execute_query(query, params=None, fetch=False):
    connection = get_db_connection()
    result = None
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
                result = True
        except Error as e:
            print(f"Error executing query: {e}")
            result = False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return result

# Helper function to generate QR code image from link
def generate_qr_image(link, with_caption=False):
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    if with_caption:
        # Create a new image with extra space for caption
        width, height = img.size
        new_img = Image.new('RGB', (width, height + 40), color='white')
        new_img.paste(img, (0, 0))
        
        # Add caption
        draw = ImageDraw.Draw(new_img)
        
        # Try to use a system font or fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            font = ImageFont.load_default()
        
        # Truncate link if too long
        display_link = link if len(link) < 40 else link[:37] + "..."
        
        # Draw text
        draw.text((10, height + 10), display_link, fill="black", font=font)
        return new_img
    
    return img

# Function to get QR code as base64 data URI
def get_qr_as_base64(link):
    img = generate_qr_image(link)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# User functions
def get_user(username):
    query = "SELECT * FROM users WHERE username = %s"
    users = execute_query(query, (username,), fetch=True)
    return users[0] if users else None

def create_user(username, password):
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    return execute_query(query, (username, password))

def verify_user(username, password):
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    users = execute_query(query, (username, password), fetch=True)
    return len(users) > 0

# QR code functions
def save_qr_code(username, qr_id, link):
    query = """
    INSERT INTO qr_codes (id, username, link, created_at) 
    VALUES (%s, %s, %s, %s)
    """
    now = datetime.datetime.now()
    return execute_query(query, (qr_id, username, link, now))

def get_user_qr_codes(username):
    query = "SELECT * FROM qr_codes WHERE username = %s ORDER BY created_at DESC"
    return execute_query(query, (username,), fetch=True)

def get_qr_code(qr_id, username):
    query = "SELECT * FROM qr_codes WHERE id = %s AND username = %s"
    qr_codes = execute_query(query, (qr_id, username), fetch=True)
    return qr_codes[0] if qr_codes else None

def delete_qr_code(qr_id, username):
    query = "DELETE FROM qr_codes WHERE id = %s AND username = %s"
    return execute_query(query, (qr_id, username))

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')  # Use the index.html template

@app.route('/qr-form')
@login_required
def qr_form():
    return render_template('dashboard.html', qr_codes=[])

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    data = request.form.get('data', '')
    if not data:
        flash("No data provided")
        return redirect(url_for('qr_form'))
    
    # Generate QR code ID
    qr_id = str(uuid.uuid4())
    
    # Save QR code data to database (without image path)
    username = session['username']
    save_qr_code(username, qr_id, data)
    
    # Generate QR code image on-the-fly for display
    img_data_uri = get_qr_as_base64(data)
    
    return render_template('qr_result.html', qr_code=img_data_uri, data=data)

@app.route('/about')
def about():
    return """
    <h1>About QR Code Generator</h1>
    <p>This simple web application allows you to generate QR codes for text or URLs.</p>
    <p>Built with Flask and deployed on Render.</p>
    <p><a href="/">Back to home</a></p>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        
        if verify_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        if get_user(username):
            flash('Username already exists')
            return redirect(url_for('signup'))
        
        # Create new user
        if create_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('An error occurred, please try again')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    username = session['username']
    
    user_qr_codes = []
    db_qr_codes = get_user_qr_codes(username)
    
    if db_qr_codes:
        for qr_data in db_qr_codes:
            # Format the created_at date for better display
            created_date = qr_data['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            # Extract URL for display (remove protocol for cleaner UI)
            display_url = qr_data['link'].replace('https://', '').replace('http://', '')
            
            user_qr_codes.append({
                'id': qr_data['id'],
                'link': qr_data['link'],
                'display_url': display_url,
                'image_url': url_for('serve_qr_image', qr_id=qr_data['id']),
                'created_at': created_date,
                'download_url': url_for('download_qr', qr_id=qr_data['id'], caption_type='no-caption'),
                'download_with_caption_url': url_for('download_qr', qr_id=qr_data['id'], caption_type='with-caption')
            })
    
    return render_template('dashboard.html', qr_codes=user_qr_codes)

@app.route('/generate-qr', methods=['POST'])
@login_required
def generate_qr():
    link = request.form['link']
    username = session['username']
    
    # Generate unique ID for the QR code
    qr_id = str(uuid.uuid4())
    
    # Save to database (without storing the image)
    save_qr_code(username, qr_id, link)
    
    return redirect(url_for('dashboard'))

@app.route('/delete-qr/<qr_id>')
@login_required
def delete_qr(qr_id):
    username = session['username']
    
    # Delete from database
    delete_qr_code(qr_id, username)
    
    return redirect(url_for('dashboard'))

@app.route('/download-qr/<qr_id>/<caption_type>')
@login_required
def download_qr(qr_id, caption_type):
    username = session['username']
    
    # Check if QR code exists for this user
    qr_data = get_qr_code(qr_id, username)
    if not qr_data:
        flash('QR code not found')
        return redirect(url_for('dashboard'))
    
    # Get link and generate QR code on-the-fly
    link = qr_data['link']
    
    # Generate QR code with or without caption
    img = generate_qr_image(link, with_caption=(caption_type == 'with-caption'))
    
    # Prepare filename for download
    safe_link = ''.join(c if c.isalnum() else '_' for c in link)[:30]  # Create safe filename
    suffix = "_with_caption" if caption_type == 'with-caption' else ""
    
    # Save to memory
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    
    return send_file(
        img_byte_array,
        mimetype='image/png',
        as_attachment=True,
        download_name=f"qr_code_{safe_link}{suffix}.png"
    )

# New route to serve QR images dynamically
@app.route('/qr_images/<qr_id>')
def serve_qr_image(qr_id):
    # Find the QR code in database
    connection = get_db_connection()
    if not connection:
        return "Database connection error", 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM qr_codes WHERE id = %s", (qr_id,))
        qr_data = cursor.fetchone()
        
        if not qr_data:
            return "QR code not found", 404
        
        # Generate QR code on-the-fly
        img = generate_qr_image(qr_data['link'])
        
        # Convert to response
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    
    except Exception as e:
        return f"Error: {str(e)}", 500
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
