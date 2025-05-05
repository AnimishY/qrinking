from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
import qrcode
import uuid
import os
import json
import datetime
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Create data directories if they don't exist
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
QR_IMAGES_DIR = os.path.join(DATA_DIR, 'qr_images')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(QR_IMAGES_DIR, exist_ok=True)

# Data storage paths
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
QR_CODES_FILE = os.path.join(DATA_DIR, 'qr_codes.json')

# Initialize local storage
def load_data(file_path, default=None):
    if default is None:
        default = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        with open(file_path, 'w') as f:
            json.dump(default, f)
        return default

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)

# Load initial data
users = load_data(USERS_FILE)
qr_codes = load_data(QR_CODES_FILE)

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
    return "Hello, this is your Flask application running on Render!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        
        if username in users and users[username] == password:
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
        
        if username in users:
            flash('Username already exists')
            return redirect(url_for('signup'))
            
        users[username] = password
        save_data(USERS_FILE, users)
        
        session['username'] = username
        return redirect(url_for('dashboard'))
    
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
    if username in qr_codes:
        for qr_id, qr_data in qr_codes[username].items():
            # Format the created_at date for better display
            created_date = qr_data['created_at']
            # Extract URL for display (remove protocol for cleaner UI)
            display_url = qr_data['link'].replace('https://', '').replace('http://', '')
            
            user_qr_codes.append({
                'id': qr_id,
                'link': qr_data['link'],
                'display_url': display_url,
                'image_url': qr_data['image_url'],
                'created_at': created_date,
                'download_url': url_for('download_qr', qr_id=qr_id, caption_type='no-caption'),
                'download_with_caption_url': url_for('download_qr', qr_id=qr_id, caption_type='with-caption')
            })
    
    # Sort QR codes by creation date (newest first)
    user_qr_codes.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('dashboard.html', qr_codes=user_qr_codes)

@app.route('/generate-qr', methods=['POST'])
@login_required
def generate_qr():
    link = request.form['link']
    username = session['username']
    
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
    
    # Generate unique ID for the QR code
    qr_id = str(uuid.uuid4())
    
    # Save QR code to local file system
    image_path = os.path.join(QR_IMAGES_DIR, f"{qr_id}.png")
    img.save(image_path)
    
    # Generate a relative URL
    image_url = f"/qr_images/{qr_id}.png"
    
    # Save to local storage
    qr_data = {
        'link': link,
        'image_url': image_url,
        'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if username not in qr_codes:
        qr_codes[username] = {}
    
    qr_codes[username][qr_id] = qr_data
    save_data(QR_CODES_FILE, qr_codes)
    
    return redirect(url_for('dashboard'))

@app.route('/delete-qr/<qr_id>')
@login_required
def delete_qr(qr_id):
    username = session['username']
    
    # Delete from filesystem
    image_path = os.path.join(QR_IMAGES_DIR, f"{qr_id}.png")
    if os.path.exists(image_path):
        os.remove(image_path)
    
    # Delete from local storage
    if username in qr_codes and qr_id in qr_codes[username]:
        del qr_codes[username][qr_id]
        save_data(QR_CODES_FILE, qr_codes)
    
    return redirect(url_for('dashboard'))

@app.route('/download-qr/<qr_id>/<caption_type>')
@login_required
def download_qr(qr_id, caption_type):
    username = session['username']
    
    # Check if QR code exists for this user
    if username not in qr_codes or qr_id not in qr_codes[username]:
        flash('QR code not found')
        return redirect(url_for('dashboard'))
    
    # Get QR code data
    qr_data = qr_codes[username][qr_id]
    qr_path = os.path.join(QR_IMAGES_DIR, f"{qr_id}.png")
    
    if not os.path.exists(qr_path):
        flash('QR code image not found')
        return redirect(url_for('dashboard'))
    
    # Prepare filename for download
    link = qr_data['link']
    safe_link = ''.join(c if c.isalnum() else '_' for c in link)[:30]  # Create safe filename
    
    if caption_type == 'with-caption':
        # Create a new image with caption
        qr_img = Image.open(qr_path)
        
        # Create a new image with extra space for caption
        width, height = qr_img.size
        new_img = Image.new('RGB', (width, height + 40), color='white')
        new_img.paste(qr_img, (0, 0))
        
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
        
        # Save to memory
        img_byte_array = io.BytesIO()
        new_img.save(img_byte_array, format='PNG')
        img_byte_array.seek(0)
        
        return send_file(
            img_byte_array,
            mimetype='image/png',
            as_attachment=True,
            download_name=f"qr_code_{safe_link}_with_caption.png"
        )
    else:
        # Return the original QR code without caption
        return send_file(
            qr_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=f"qr_code_{safe_link}.png"
        )

# Route to serve QR images
@app.route('/qr_images/<filename>')
def serve_qr_image(filename):
    return send_from_directory(QR_IMAGES_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)
