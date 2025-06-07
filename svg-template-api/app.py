from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'svg'}
API_SERVER_URL = 'https://svg-template-api-server.onrender.com'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_database():
    conn = sqlite3.connect('templates.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            template_type TEXT NOT NULL,
            template_role TEXT NOT NULL,
            svg_content TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def send_template_to_api_server(template_data):
    try:
        response = requests.post(
            f'{API_SERVER_URL}/api/templates/upload',
            json=template_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('success', False)
        return False
    except:
        return False

@app.route('/')
def index():
    conn = sqlite3.connect('templates.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates ORDER BY created_at DESC")
    templates = cursor.fetchall()
    conn.close()
    return render_template('index.html', templates=templates)

@app.route('/upload', methods=['GET', 'POST'])
def upload_template():
    if request.method == 'POST':
        try:
            template_name = request.form.get('name')
            category = request.form.get('category')
            template_type = request.form.get('template_type')
            template_role = request.form.get('template_role')
            
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '' or not allowed_file(file.filename):
                flash('Invalid file', 'error')
                return redirect(request.url)
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            template_id = f"{category}-{template_role}"
            
            # Сохранить локально
            conn = sqlite3.connect('templates.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO templates 
                (id, name, category, template_type, template_role, svg_content, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (template_id, template_name, category, template_type, template_role, svg_content, filename))
            conn.commit()
            conn.close()
            
            # Отправить в API сервер
            template_data = {
                'id': template_id,
                'name': template_name,
                'category': category,
                'template_type': template_type,
                'template_role': template_role,
                'svg_content': svg_content
            }
            
            api_success = send_template_to_api_server(template_data)
            
            if api_success:
                flash('Template uploaded and synced!', 'success')
            else:
                flash('Template uploaded locally, sync failed', 'warning')
            
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
    
    return render_template('upload.html')

if __name__ == '__main__':
    init_database()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
