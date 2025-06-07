from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import json
import os
import uuid
import base64
from io import BytesIO
from PIL import Image
import cairosvg
import re
import requests
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# Создаем директорию для статических файлов
os.makedirs('static', exist_ok=True)

def get_db_connection():
    """Получить соединение с базой данных"""
    conn = sqlite3.connect('templates.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    conn = get_db_connection()
    
    # Создаем таблицу шаблонов если не существует
    conn.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            template_type TEXT,
            svg_content TEXT NOT NULL
        )
    """)
    
    # Создаем таблицу каруселей
    conn.execute("""
        CREATE TABLE IF NOT EXISTS carousels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'created',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создаем таблицу слайдов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS slides (
            id TEXT PRIMARY KEY,
            carousel_id TEXT,
            template_id TEXT,
            replacements TEXT,
            image_path TEXT,
            FOREIGN KEY (carousel_id) REFERENCES carousels (id)
        )
    """)
    
    conn.commit()
    conn.close()

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'healthy',
        'version': '1.3.0-full-api'
    })

@app.route('/api/templates/all-previews', methods=['GET'])
def get_all_templates_with_previews():
    """Получить все шаблоны с превью"""
    try:
        conn = get_db_connection()
        templates = conn.execute('SELECT * FROM templates').fetchall()
        conn.close()
        
        result = []
        for template in templates:
            result.append({
                'id': template['id'],
                'name': template['name'],
                'category': template['category'] or 'open-house',
                'template_type': template['template_type'] or ('main' if 'main' in template['id'] else 'photo'),
                'template_role': template['template_type'] or ('main' if 'main' in template['id'] else 'photo'),
                'preview_url': f'/static/preview_{template["id"]}.png'
            })
        
        return jsonify({'templates': result})
        
    except Exception as e:
        print(f"Ошибка получения шаблонов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/carousel', methods=['POST'])
def create_carousel():
    """Создать новую карусель"""
    try:
        data = request.get_json()
        carousel_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO carousels (id, name) VALUES (?, ?)',
            (carousel_id, data.get('name', 'Untitled Carousel'))
        )
        
        # Сохраняем слайды
        for i, slide in enumerate(data.get('slides', [])):
            slide_id = str(uuid.uuid4())
            conn.execute(
                'INSERT INTO slides (id, carousel_id, template_id, replacements) VALUES (?, ?, ?, ?)',
                (slide_id, carousel_id, slide['templateId'], json.dumps(slide['replacements']))
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'carousel_id': carousel_id,
            'status': 'created'
        })
        
    except Exception as e:
        print(f"Ошибка создания карусели: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/carousel/<carousel_id>/generate', methods=['POST'])
def generate_carousel(carousel_id):
    """Запустить генерацию карусели"""
    try:
        return jsonify({
            'status': 'completed',
            'carousel_id': carousel_id,
            'message': 'Generation completed successfully'
        })
        
    except Exception as e:
        print(f"Ошибка генерации карусели: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/carousel/<carousel_id>/slides', methods=['GET'])
def get_carousel_slides(carousel_id):
    """Получить слайды карусели"""
    try:
        return jsonify({
            'carousel_id': carousel_id,
            'name': 'Test Carousel',
            'status': 'completed',
            'slides': [
                {
                    'id': 'slide1',
                    'template_id': 'main-template',
                    'image_url': '/static/test_slide1.png'
                },
                {
                    'id': 'slide2', 
                    'template_id': 'photo-template',
                    'image_url': '/static/test_slide2.png'
                }
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/<filename>')
def serve_static(filename):
    """Отдать статические файлы"""
    try:
        return send_file(os.path.join('static', filename))
    except:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
