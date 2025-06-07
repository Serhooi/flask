#!/usr/bin/env python3
"""
SVG Template API - Финальная версия с превью и исправлениями
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import uuid
import os
import threading
import time
import requests
import base64
import re
from io import BytesIO
from PIL import Image
import cairosvg

app = Flask(__name__)
CORS(app)

# Глобальное хранилище каруселей
carousels = {}

def download_and_process_image(url, image_type="property"):
    """Скачивает и обрабатывает изображение с правильными пропорциями"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        if image_type == "headshot":
            # ЗАПОЛНЯЕМ ВЕСЬ КРУГ - object-fit: cover эффект
            target_size = 100
            scale_factor = max(target_size / img.width, target_size / img.height)
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Обрезаем по центру
            left = (new_width - target_size) // 2
            top = (new_height - target_size) // 2
            img = img.crop((left, top, left + target_size, top + target_size))
            
        elif image_type == "logo":
            # Сохраняем пропорции логотипа
            img.thumbnail((142, 56), Image.Resampling.LANCZOS)
        else:
            # Обычное изображение
            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
        
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        img_data = buffer.getvalue()
        
        base64_string = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_string}"
        
    except Exception as e:
        print(f"❌ Ошибка при обработке изображения: {e}")
        return None

def replace_address_with_lines(svg_content, address):
    """Заменяет адрес на 3 строки в исправленном шаблоне"""
    
    # Разбиваем адрес на части
    parts = address.split(', ')
    
    lines = []
    if len(parts) >= 3:
        lines.append(parts[0])  # Номер и улица
        lines.append(', '.join(parts[1:-1]))  # Город
        lines.append(parts[-1])  # Штат и ZIP
    elif len(parts) == 2:
        lines.append(parts[0])
        lines.append(parts[1])
    else:
        lines.append(address)
    
    # Заменяем каждую строку в соответствующем tspan
    for i, line in enumerate(lines):
        if i == 0:
            svg_content = re.sub(r'(<tspan x="766" y="1000\.04">)[^<]*(</tspan>)', rf'\g<1>{line}\g<2>', svg_content)
        elif i == 1:
            svg_content = re.sub(r'(<tspan x="766" y="1028\.04">)[^<]*(</tspan>)', rf'\g<1>{line}\g<2>', svg_content)
        elif i == 2:
            svg_content = re.sub(r'(<tspan x="766" y="1056\.04">)[^<]*(</tspan>)', rf'\g<1>{line}\g<2>', svg_content)
    
    return svg_content

def process_svg_template(svg_content, replacements):
    """Обрабатывает SVG шаблон с заменами"""
    
    modified_svg = svg_content
    
    # Заменяем текстовые поля
    text_mappings = {
        'dyno.date': replacements.get('dyno.date', ''),
        'dyno.time': replacements.get('dyno.time', ''),
        'dyno.price': replacements.get('dyno.price', ''),
        'dyno.bedrooms': replacements.get('dyno.bedrooms', ''),
        'dyno.bathrooms': replacements.get('dyno.bathrooms', ''),
        'dyno.propertyfeatures': replacements.get('dyno.propertyfeatures', ''),
        'dyno.name': replacements.get('dyno.name', ''),
        'dyno.phone': replacements.get('dyno.phone', ''),
        'dyno.email': replacements.get('dyno.email', '')
    }
    
    for field_id, new_text in text_mappings.items():
        if new_text:
            pattern = rf'(<text id="{re.escape(field_id)}"[^>]*>.*?<tspan[^>]*>)[^<]*(</tspan>.*?</text>)'
            replacement = rf'\g<1>{new_text}\g<2>'
            
            if re.search(pattern, modified_svg, re.DOTALL):
                modified_svg = re.sub(pattern, replacement, modified_svg, flags=re.DOTALL)
    
    # Заменяем адрес специальной функцией
    if 'dyno.propertyaddress' in replacements:
        modified_svg = replace_address_with_lines(modified_svg, replacements['dyno.propertyaddress'])
    
    # Заменяем изображения
    image_mappings = {
        'dyno.propertyimage': ('image0_294_4', 'property'),
        'dyno.logo': ('image1_294_4', 'logo'), 
        'dyno.agentheadshot': ('image2_294_4', 'headshot')
    }
    
    # Проверяем альтернативные ID для Photo Template
    if 'image0_332_4' in svg_content:
        image_mappings['dyno.propertyimage'] = ('image0_332_4', 'property')
    
    for field, (image_id, image_type) in image_mappings.items():
        if field in replacements and replacements[field]:
            url = replacements[field]
            
            base64_data = download_and_process_image(url, image_type)
            
            if base64_data:
                pattern = rf'(<image id="{re.escape(image_id)}"[^>]*xlink:href=")[^"]*(")'
                replacement = rf'\g<1>{base64_data}\g<2>'
                
                if re.search(pattern, modified_svg):
                    modified_svg = re.sub(pattern, replacement, modified_svg)
    
    return modified_svg

def generate_carousel_async(carousel_id, slides_data):
    """Асинхронная генерация карусели"""
    try:
        conn = sqlite3.connect('templates.db')
        cursor = conn.cursor()
        
        generated_slides = []
        
        for i, slide_data in enumerate(slides_data):
            template_id = slide_data['templateId']
            replacements = slide_data['replacements']
            
            # Получаем шаблон из базы данных
            if template_id == 'main-template':
                cursor.execute("SELECT svg_content FROM templates WHERE name = 'Open House - Main Template'")
            else:
                cursor.execute("SELECT svg_content FROM templates WHERE name = 'Open House - Photo Template'")
            
            result = cursor.fetchone()
            if not result:
                continue
                
            svg_content = result[0]
            
            # Обрабатываем шаблон
            processed_svg = process_svg_template(svg_content, replacements)
            
            # Конвертируем в PNG
            png_data = cairosvg.svg2png(bytestring=processed_svg.encode('utf-8'))
            
            # Сохраняем файл
            filename = f"carousel_{carousel_id}_slide_{i+1}.png"
            filepath = f"static/{filename}"
            
            os.makedirs("static", exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(png_data)
            
            generated_slides.append({
                "slideNumber": i + 1,
                "imageUrl": f"/static/{filename}"
            })
        
        # Обновляем статус карусели
        carousels[carousel_id]['status'] = 'completed'
        carousels[carousel_id]['slides'] = generated_slides
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка генерации карусели: {e}")
        carousels[carousel_id]['status'] = 'failed'
        carousels[carousel_id]['error'] = str(e)

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Получить список шаблонов"""
    try:
        conn = sqlite3.connect('templates.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM templates")
        templates = cursor.fetchall()
        
        result = {
            "templates": [
                {
                    "id": "main-template" if "Main" in name else "photo-template",
                    "name": name,
                    "category": "open-house",
                    "template_type": "flyer"
                }
                for template_id, name in templates
            ]
        }
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates/<template_id>/preview', methods=['GET'])
def get_template_preview(template_id):
    """Генерирует превью шаблона"""
    try:
        conn = sqlite3.connect('templates.db')
        cursor = conn.cursor()
        
        # Определяем какой шаблон запрашивается
        if template_id == 'main-template':
            cursor.execute("SELECT svg_content FROM templates WHERE name = 'Open House - Main Template'")
        elif template_id == 'photo-template':
            cursor.execute("SELECT svg_content FROM templates WHERE name = 'Open House - Photo Template'")
        else:
            return jsonify({"error": "Template not found"}), 404
        
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Template not found"}), 404
            
        svg_content = result[0]
        
        # Создаем превью с демо данными
        demo_data = {
            'dyno.date': 'JUNE 15 2028',
            'dyno.time': '6PM - 10PM',
            'dyno.propertyaddress': '123 Luxury Estate Drive, Beverly Hills, CA 90210',
            'dyno.price': '$15,750,000',
            'dyno.bedrooms': '8',
            'dyno.bathrooms': '10',
            'dyno.propertyfeatures': 'infinity pool, wine cellar, home theater, guest house',
            'dyno.name': 'Sarah Johnson',
            'dyno.phone': '+1 555 777 8888',
            'dyno.email': 'sarah.johnson@luxuryrealty.com',
            'dyno.propertyimage': 'https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=400&h=300&fit=crop',
            'dyno.logo': 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=100&h=50&fit=crop',
            'dyno.agentheadshot': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop'
        }
        
        # Для Photo Template используем только изображение
        if template_id == 'photo-template':
            demo_data = {'dyno.propertyimage': 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=400&h=300&fit=crop'}
        
        # Обрабатываем шаблон
        processed_svg = process_svg_template(svg_content, demo_data)
        
        # Конвертируем в PNG
        png_data = cairosvg.svg2png(bytestring=processed_svg.encode('utf-8'), output_width=400, output_height=300)
        
        # Сохраняем превью
        preview_filename = f"preview_{template_id}.png"
        preview_path = f"static/{preview_filename}"
        
        os.makedirs("static", exist_ok=True)
        with open(preview_path, 'wb') as f:
            f.write(png_data)
        
        conn.close()
        
        return jsonify({
            "preview_url": f"/static/{preview_filename}",
            "template_id": template_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates/all-previews', methods=['GET'])
def get_all_previews():
    """Генерирует превью для всех шаблонов"""
    try:
        previews = []
        
        # Генерируем превью для Main Template
        main_response = get_template_preview('main-template')
        if main_response.status_code == 200:
            main_data = main_response.get_json()
            previews.append({
                "id": "main-template",
                "name": "Open House - Main Template",
                "category": "open-house",
                "template_type": "main",
                "preview_url": main_data["preview_url"]
            })
        
        # Генерируем превью для Photo Template
        photo_response = get_template_preview('photo-template')
        if photo_response.status_code == 200:
            photo_data = photo_response.get_json()
            previews.append({
                "id": "photo-template",
                "name": "Open House - Photo Template",
                "category": "open-house",
                "template_type": "photo",
                "preview_url": photo_data["preview_url"]
            })
        
        return jsonify({"templates": previews})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/carousel', methods=['POST'])
def create_carousel():
    """Создать новую карусель"""
    try:
        data = request.json
        carousel_id = str(uuid.uuid4())
        
        carousels[carousel_id] = {
            'name': data.get('name', 'Untitled Carousel'),
            'slides': data.get('slides', []),
            'status': 'created',
            'created_at': time.time()
        }
        
        return jsonify({"carouselId": carousel_id})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/carousel/<carousel_id>/generate', methods=['POST'])
def generate_carousel(carousel_id):
    """Запустить генерацию карусели"""
    try:
        if carousel_id not in carousels:
            return jsonify({"error": "Carousel not found"}), 404
        
        carousel = carousels[carousel_id]
        carousel['status'] = 'generating'
        
        # Запускаем асинхронную генерацию
        thread = threading.Thread(
            target=generate_carousel_async,
            args=(carousel_id, carousel['slides'])
        )
        thread.start()
        
        return jsonify({"status": "generation_started"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/carousel/<carousel_id>/slides', methods=['GET'])
def get_carousel_slides(carousel_id):
    """Получить слайды карусели"""
    try:
        if carousel_id not in carousels:
            return jsonify({"error": "Carousel not found"}), 404
        
        carousel = carousels[carousel_id]
        
        if carousel['status'] == 'completed':
            return jsonify({
                "status": "completed",
                "slides": carousel['slides']
            })
        elif carousel['status'] == 'failed':
            return jsonify({
                "status": "failed",
                "error": carousel.get('error', 'Unknown error')
            })
        else:
            return jsonify({
                "status": carousel['status']
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/<filename>')
def serve_static(filename):
    """Отдача статических файлов"""
    return send_file(f"static/{filename}")

@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    return jsonify({"status": "healthy", "version": "1.2.0-with-previews"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
