import sqlite3
import os
from datetime import datetime
import uuid

class Database:
    def __init__(self, db_path='templates.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                template_type TEXT NOT NULL,
                svg_content TEXT NOT NULL,
                preview_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Carousels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carousels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Carousel slides table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carousel_slides (
                id TEXT PRIMARY KEY,
                carousel_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                slide_number INTEGER NOT NULL,
                image_url TEXT,
                replacements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (carousel_id) REFERENCES carousels (id),
                FOREIGN KEY (template_id) REFERENCES templates (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Insert default templates if database is empty
        self.insert_default_templates()
    
    def insert_default_templates(self):
        """Insert default templates if none exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if templates exist
        cursor.execute('SELECT COUNT(*) FROM templates')
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert default templates
            default_templates = [
                {
                    'id': 'open-house-main',
                    'name': 'Open House - Main Template',
                    'category': 'open-house',
                    'template_type': 'main',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/open-house-main/preview'
                },
                {
                    'id': 'open-house-photo',
                    'name': 'Open House - Photo Template',
                    'category': 'open-house',
                    'template_type': 'photo',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/open-house-photo/preview'
                },
                {
                    'id': 'sold-main',
                    'name': 'Sold - Main Template',
                    'category': 'sold',
                    'template_type': 'main',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/sold-main/preview'
                },
                {
                    'id': 'sold-photo',
                    'name': 'Sold - Photo Template',
                    'category': 'sold',
                    'template_type': 'photo',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/sold-photo/preview'
                },
                {
                    'id': 'for-rent-main',
                    'name': 'For Rent - Main Template',
                    'category': 'for-rent',
                    'template_type': 'main',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/for-rent-main/preview'
                },
                {
                    'id': 'for-rent-photo',
                    'name': 'For Rent - Photo Template',
                    'category': 'for-rent',
                    'template_type': 'photo',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/for-rent-photo/preview'
                },
                {
                    'id': 'lease-main',
                    'name': 'Lease - Main Template',
                    'category': 'lease',
                    'template_type': 'main',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/lease-main/preview'
                },
                {
                    'id': 'lease-photo',
                    'name': 'Lease - Photo Template',
                    'category': 'lease',
                    'template_type': 'photo',
                    'svg_content': self.get_default_svg_content(),
                    'preview_url': '/api/templates/lease-photo/preview'
                }
            ]
            
            for template in default_templates:
                cursor.execute('''
                    INSERT INTO templates (id, name, category, template_type, svg_content, preview_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    template['id'],
                    template['name'],
                    template['category'],
                    template['template_type'],
                    template['svg_content'],
                    template['preview_url']
                ))
            
            conn.commit()
        
        conn.close()
    
    def get_default_svg_content(self):
        """Get default SVG content from the static file"""
        try:
            svg_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'post(9).svg')
            with open(svg_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return '<svg>Default SVG content</svg>'
    
    # Template methods
    def create_template(self, name, category, template_type, svg_content, preview_url=None):
        """Create a new template"""
        template_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO templates (id, name, category, template_type, svg_content, preview_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (template_id, name, category, template_type, svg_content, preview_url))
        
        conn.commit()
        conn.close()
        return template_id
    
    def get_templates(self, category=None, template_type=None):
        """Get templates with optional filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM templates WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if template_type:
            query += ' AND template_type = ?'
            params.append(template_type)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        templates = cursor.fetchall()
        conn.close()
        
        # Convert to dict format
        result = []
        for template in templates:
            result.append({
                'id': template[0],
                'name': template[1],
                'category': template[2],
                'template_type': template[3],
                'svg_content': template[4],
                'preview_url': template[5],
                'created_at': template[6],
                'updated_at': template[7]
            })
        
        return result
    
    def get_template_by_id(self, template_id):
        """Get template by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM templates WHERE id = ?', (template_id,))
        template = cursor.fetchone()
        conn.close()
        
        if template:
            return {
                'id': template[0],
                'name': template[1],
                'category': template[2],
                'template_type': template[3],
                'svg_content': template[4],
                'preview_url': template[5],
                'created_at': template[6],
                'updated_at': template[7]
            }
        return None
    
    def update_template(self, template_id, **kwargs):
        """Update template"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['name', 'category', 'template_type', 'svg_content', 'preview_url']:
                fields.append(f'{key} = ?')
                values.append(value)
        
        if fields:
            fields.append('updated_at = ?')
            values.append(datetime.utcnow().isoformat())
            values.append(template_id)
            
            query = f'UPDATE templates SET {", ".join(fields)} WHERE id = ?'
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def delete_template(self, template_id):
        """Delete template"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM templates WHERE id = ?', (template_id,))
        conn.commit()
        conn.close()
    
    # Carousel methods
    def create_carousel(self, name):
        """Create a new carousel"""
        carousel_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO carousels (id, name, status)
            VALUES (?, ?, ?)
        ''', (carousel_id, name, 'pending'))
        
        conn.commit()
        conn.close()
        return carousel_id
    
    def get_carousel(self, carousel_id):
        """Get carousel by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM carousels WHERE id = ?', (carousel_id,))
        carousel = cursor.fetchone()
        conn.close()
        
        if carousel:
            return {
                'id': carousel[0],
                'name': carousel[1],
                'status': carousel[2],
                'created_at': carousel[3],
                'updated_at': carousel[4]
            }
        return None
    
    def update_carousel_status(self, carousel_id, status):
        """Update carousel status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE carousels SET status = ?, updated_at = ? WHERE id = ?
        ''', (status, datetime.utcnow().isoformat(), carousel_id))
        
        conn.commit()
        conn.close()
    
    def create_carousel_slide(self, carousel_id, template_id, slide_number, replacements, image_url=None):
        """Create a carousel slide"""
        slide_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO carousel_slides (id, carousel_id, template_id, slide_number, image_url, replacements)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (slide_id, carousel_id, template_id, slide_number, image_url, replacements))
        
        conn.commit()
        conn.close()
        return slide_id
    
    def get_carousel_slides(self, carousel_id):
        """Get all slides for a carousel"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM carousel_slides WHERE carousel_id = ? ORDER BY slide_number
        ''', (carousel_id,))
        
        slides = cursor.fetchall()
        conn.close()
        
        result = []
        for slide in slides:
            result.append({
                'id': slide[0],
                'carousel_id': slide[1],
                'template_id': slide[2],
                'slide_number': slide[3],
                'image_url': slide[4],
                'replacements': slide[5],
                'created_at': slide[6]
            })
        
        return result
    
    def update_slide_image_url(self, slide_id, image_url):
        """Update slide image URL"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE carousel_slides SET image_url = ? WHERE id = ?
        ''', (image_url, slide_id))
        
        conn.commit()
        conn.close()

# Global database instance
db = Database()

