#!/usr/bin/env python3
"""
Полный SVG процессор со всеми функциями:
- Замена изображений (property, logo, headshot)
- Замена текстовых полей (даты, цены, контакты)
- Автоперенос адреса и длинных текстов
- Консистентные расстояния
- Создание карусели
- Возврат URL готовых файлов
"""

import re
import base64
import os
import tempfile
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET

class CompleteSVGProcessor:
    def __init__(self, svg_content: str, canvas_width: int = 1080):
        self.original_svg = svg_content
        self.processed_svg = svg_content
        self.canvas_width = canvas_width
        self.dyno_elements = {}
        self.analyze_template()
    
    def analyze_template(self):
        """Анализирует SVG шаблон и находит все dyno элементы"""
        print("📋 Анализ SVG шаблона...")
        
        # Находим все элементы с id содержащим "dyno."
        dyno_pattern = r'id="([^"]*dyno\.[^"]*)"'
        matches = re.findall(dyno_pattern, self.processed_svg)
        
        for element_id in matches:
            if 'dyno.' in element_id:
                dyno_id = element_id.split('dyno.')[1]
                
                # Определяем тип элемента
                if self._is_image_element(element_id):
                    element_type = 'image'
                else:
                    element_type = 'text'
                
                self.dyno_elements[dyno_id] = {
                    'id': element_id,
                    'type': element_type,
                    'original_content': self._get_element_content(element_id)
                }
        
        print(f"🔍 Найдено {len(self.dyno_elements)} динамических элементов:")
        for dyno_id, info in self.dyno_elements.items():
            print(f"  • {dyno_id} ({info['type']})")
    
    def _is_image_element(self, element_id: str) -> bool:
        """Проверяет, является ли элемент изображением"""
        # Ищем элемент image с данным id
        image_pattern = rf'<image[^>]*id="{re.escape(element_id)}"[^>]*>'
        return bool(re.search(image_pattern, self.processed_svg))
    
    def _get_element_content(self, element_id: str) -> str:
        """Получает содержимое элемента"""
        # Для текстовых элементов
        text_pattern = rf'<text[^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</text>'
        text_match = re.search(text_pattern, self.processed_svg, re.DOTALL)
        if text_match:
            return text_match.group(1).strip()
        
        # Для изображений
        image_pattern = rf'<image[^>]*id="{re.escape(element_id)}"[^>]*href="([^"]*)"'
        image_match = re.search(image_pattern, self.processed_svg)
        if image_match:
            return image_match.group(1)
        
        return ""
    
    def replace_text(self, dyno_id: str, new_text: str):
        """Заменяет текст в элементе с автопереносом"""
        if dyno_id not in self.dyno_elements:
            print(f"⚠️ Элемент {dyno_id} не найден")
            return
        
        element_id = self.dyno_elements[dyno_id]['id']
        
        # Специальная обработка для адреса
        if 'address' in dyno_id.lower():
            self._replace_address_with_wrapping(element_id, new_text)
        # Специальная обработка для bedroom/bathroom
        elif 'bedroom' in dyno_id.lower() or 'bathroom' in dyno_id.lower():
            self._replace_with_consistent_spacing(element_id, new_text)
        else:
            self._replace_simple_text(element_id, new_text)
        
        print(f"✅ Заменен текст в {dyno_id}: '{new_text}'")
    
    def _replace_address_with_wrapping(self, element_id: str, address: str):
        """Заменяет адрес с автопереносом на две строки"""
        # Разделяем адрес на части
        parts = address.split(',')
        if len(parts) >= 2:
            line1 = parts[0].strip()
            line2 = ','.join(parts[1:]).strip()
        else:
            # Если нет запятой, разделяем по последнему пробелу
            words = address.split()
            if len(words) > 3:
                split_point = len(words) // 2
                line1 = ' '.join(words[:split_point])
                line2 = ' '.join(words[split_point:])
            else:
                line1 = address
                line2 = ""
        
        # Находим оригинальный text элемент
        text_pattern = rf'(<text[^>]*id="{re.escape(element_id)}"[^>]*>)(.*?)(</text>)'
        match = re.search(text_pattern, self.processed_svg, re.DOTALL)
        
        if match:
            opening_tag = match.group(1)
            closing_tag = match.group(3)
            
            # Извлекаем координаты
            x_match = re.search(r'x="([^"]*)"', opening_tag)
            y_match = re.search(r'y="([^"]*)"', opening_tag)
            
            if x_match and y_match:
                x = float(x_match.group(1))
                y = float(y_match.group(1))
                
                # Создаем новый контент с двумя строками
                new_content = f"""<tspan x="{x}" y="{y}">{line1}</tspan>"""
                if line2:
                    new_content += f"""<tspan x="{x}" y="{y + 35}">{line2}</tspan>"""
                
                replacement = f"{opening_tag}{new_content}{closing_tag}"
                self.processed_svg = re.sub(text_pattern, replacement, self.processed_svg, flags=re.DOTALL)
    
    def _replace_with_consistent_spacing(self, element_id: str, text: str):
        """Заменяет текст с консистентными расстояниями для bedroom/bathroom"""
        # Разделяем на цифру и слово
        parts = text.split(' ', 1)
        if len(parts) == 2:
            number = parts[0]
            word = parts[1]
            
            # Находим оригинальный text элемент
            text_pattern = rf'(<text[^>]*id="{re.escape(element_id)}"[^>]*>)(.*?)(</text>)'
            match = re.search(text_pattern, self.processed_svg, re.DOTALL)
            
            if match:
                opening_tag = match.group(1)
                closing_tag = match.group(3)
                
                # Извлекаем координаты
                x_match = re.search(r'x="([^"]*)"', opening_tag)
                y_match = re.search(r'y="([^"]*)"', opening_tag)
                
                if x_match and y_match:
                    x = float(x_match.group(1))
                    y = float(y_match.group(1))
                    
                    # Создаем контент с фиксированным расстоянием 30px
                    new_content = f"""<tspan x="{x}" y="{y}">{number}</tspan><tspan x="{x + 30}" y="{y}">{word}</tspan>"""
                    
                    replacement = f"{opening_tag}{new_content}{closing_tag}"
                    self.processed_svg = re.sub(text_pattern, replacement, self.processed_svg, flags=re.DOTALL)
        else:
            self._replace_simple_text(element_id, text)
    
    def _replace_simple_text(self, element_id: str, new_text: str):
        """Простая замена текста"""
        text_pattern = rf'(<text[^>]*id="{re.escape(element_id)}"[^>]*>)(.*?)(</text>)'
        replacement = rf'\g<1>{new_text}\g<3>'
        self.processed_svg = re.sub(text_pattern, replacement, self.processed_svg, flags=re.DOTALL)
    
    def replace_image(self, dyno_id: str, image_path: str):
        """Заменяет изображение"""
        if dyno_id not in self.dyno_elements:
            print(f"⚠️ Элемент {dyno_id} не найден")
            return
        
        element_id = self.dyno_elements[dyno_id]['id']
        
        # Конвертируем изображение в base64
        try:
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Определяем MIME тип
                if image_path.lower().endswith('.png'):
                    mime_type = 'image/png'
                elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
                    mime_type = 'image/jpeg'
                else:
                    mime_type = 'image/png'
                
                data_url = f"data:{mime_type};base64,{img_base64}"
                
                # Заменяем href в image элементе
                image_pattern = rf'(<image[^>]*id="{re.escape(element_id)}"[^>]*href=")[^"]*(")'
                replacement = rf'\g<1>{data_url}\g<2>'
                self.processed_svg = re.sub(image_pattern, replacement, self.processed_svg)
                
                print(f"✅ Заменено изображение в {dyno_id}")
        
        except Exception as e:
            print(f"❌ Ошибка замены изображения {dyno_id}: {e}")
    
    def apply_universal_wrapping(self):
        """Применяет универсальный автоперенос для всех текстовых элементов"""
        print("🔄 Применение универсального автопереноса...")
        
        # Находим все текстовые элементы
        text_pattern = r'<text[^>]*x="([^"]*)"[^>]*>(.*?)</text>'
        matches = re.finditer(text_pattern, self.processed_svg, re.DOTALL)
        
        for match in matches:
            x_pos = float(match.group(1))
            text_content = match.group(2)
            
            # Проверяем, приближается ли текст к краю (80% от ширины canvas)
            edge_threshold = self.canvas_width * 0.8
            
            if x_pos > edge_threshold and len(text_content) > 20:
                # Применяем автоперенос
                self._wrap_text_element(match.group(0), text_content)
        
        return self.processed_svg
    
    def _wrap_text_element(self, original_element: str, text_content: str):
        """Переносит длинный текст на новую строку"""
        # Простая логика переноса по середине
        words = text_content.split()
        if len(words) > 2:
            mid_point = len(words) // 2
            line1 = ' '.join(words[:mid_point])
            line2 = ' '.join(words[mid_point:])
            
            # Заменяем элемент на многострочный
            x_match = re.search(r'x="([^"]*)"', original_element)
            y_match = re.search(r'y="([^"]*)"', original_element)
            
            if x_match and y_match:
                x = x_match.group(1)
                y = float(y_match.group(1))
                
                new_element = original_element.replace(
                    text_content,
                    f'<tspan x="{x}" y="{y}">{line1}</tspan><tspan x="{x}" y="{y + 25}">{line2}</tspan>'
                )
                
                self.processed_svg = self.processed_svg.replace(original_element, new_element)
    
    def process_complete_data(self, data: Dict):
        """Обрабатывает полный набор данных"""
        print("🔄 Обработка полного набора данных...")
        
        # Замена текстовых полей
        text_mappings = {
            'date': data.get('date', 'JUNE 15 2024'),
            'time': data.get('time', '2PM - 5PM'),
            'price': data.get('price', '$2,850,000'),
            'propertyaddress': data.get('address', '123 Luxury Lane, Beverly Hills, CA'),
            'bedrooms': data.get('bedrooms', '3 bedroom'),
            'bathrooms': data.get('bathrooms', '2 bathroom'),
            'name': data.get('agent_name', 'Sarah Johnson'),
            'phone': data.get('agent_phone', '+1 (310) 555-0123'),
            'email': data.get('agent_email', 'sarah.johnson@luxuryrealty.com'),
            'propertyfeatures': data.get('features', 'Pool, 3-car garage, wine cellar, marble floors')
        }
        
        for dyno_id, value in text_mappings.items():
            if dyno_id in self.dyno_elements:
                self.replace_text(dyno_id, value)
        
        # Замена изображений
        image_mappings = {
            'propertyimage': data.get('property_image'),
            'logo': data.get('logo_image'),
            'agentheadshot': data.get('agent_image')
        }
        
        for dyno_id, image_path in image_mappings.items():
            if dyno_id in self.dyno_elements and image_path and os.path.exists(image_path):
                self.replace_image(dyno_id, image_path)
        
        # Применяем универсальный автоперенос
        self.apply_universal_wrapping()
        
        print("✅ Обработка завершена!")
        return self.processed_svg
    
    def create_carousel_slides(self, main_data: Dict, additional_images: List[str]) -> List[str]:
        """Создает слайды карусели"""
        print(f"🎠 Создание карусели из {len(additional_images) + 1} слайдов...")
        
        slides = []
        
        # Первый слайд - основной с полными данными
        main_slide = self.process_complete_data(main_data)
        slides.append(main_slide)
        
        # Дополнительные слайды - только с заменой изображения property
        for i, image_path in enumerate(additional_images):
            slide_processor = CompleteSVGProcessor(self.original_svg, self.canvas_width)
            
            # Заменяем только изображение property
            if os.path.exists(image_path):
                slide_processor.replace_image('propertyimage', image_path)
            
            # Добавляем базовые данные
            slide_processor.process_complete_data(main_data)
            
            slides.append(slide_processor.processed_svg)
            print(f"✅ Создан слайд {i + 2}")
        
        print(f"🎊 Карусель готова: {len(slides)} слайдов")
        return slides
    
    def save_svg(self, filename: str) -> str:
        """Сохраняет обработанный SVG"""
        filepath = os.path.join(tempfile.gettempdir(), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.processed_svg)
        return filepath

def test_complete_processor():
    """Тестирование полного процессора"""
    print("🧪 Тестирование полного SVG процессора...")
    
    # Загружаем шаблон
    template_path = "/home/ubuntu/upload/post(9).svg"
    if not os.path.exists(template_path):
        print("❌ Шаблон не найден")
        return
    
    with open(template_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    # Создаем процессор
    processor = CompleteSVGProcessor(svg_content)
    
    # Тестовые данные
    test_data = {
        'date': 'JUNE 15 2024',
        'time': '2PM - 5PM',
        'price': '$2,850,000',
        'address': '123 Luxury Lane, Beverly Hills, CA 90210',
        'bedrooms': '3 bedroom',
        'bathrooms': '2 bathroom',
        'agent_name': 'Sarah Johnson',
        'agent_phone': '+1 (310) 555-0123',
        'agent_email': 'sarah.johnson@luxuryrealty.com',
        'features': 'Pool, 3-car garage, wine cellar, marble floors'
    }
    
    # Обрабатываем
    result = processor.process_complete_data(test_data)
    
    # Сохраняем результат
    output_path = processor.save_svg('complete_test_result.svg')
    print(f"💾 Результат сохранен: {output_path}")
    
    return output_path

if __name__ == "__main__":
    test_complete_processor()

