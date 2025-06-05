from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime
import base64
import io
from PIL import Image
import cairosvg

# Import database
from src.models.database import db

admin_bp = Blueprint('admin', __name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
PREVIEW_FOLDER = 'previews'
ALLOWED_EXTENSIONS = {'svg'}

# Ensure upload directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PREVIEW_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_preview_from_svg(svg_content, template_id):
    """Generate PNG preview from SVG content"""
    try:
        # Convert SVG to PNG using cairosvg
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            output_width=400,  # Preview width
            output_height=600  # Preview height
        )
        
        # Save preview file
        preview_filename = f"{template_id}_preview.png"
        preview_path = os.path.join(PREVIEW_FOLDER, preview_filename)
        
        with open(preview_path, 'wb') as f:
            f.write(png_data)
        
        # Return URL path
        return f"/api/admin/preview/{preview_filename}"
        
    except Exception as e:
        print(f"Error generating preview: {e}")
        return None

@admin_bp.route('/admin/upload-template', methods=['POST'])
def upload_template():
    """Upload a new SVG template"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only SVG files are allowed"}), 400
        
        # Get form data
        name = request.form.get('name')
        category = request.form.get('category')
        template_type = request.form.get('template_type', 'main')
        
        if not name or not category:
            return jsonify({"error": "Name and category are required"}), 400
        
        # Read SVG content
        svg_content = file.read().decode('utf-8')
        
        # Generate preview
        template_id = str(uuid.uuid4())
        preview_url = generate_preview_from_svg(svg_content, template_id)
        
        # Save to database
        db.create_template(
            name=name,
            category=category,
            template_type=template_type,
            svg_content=svg_content,
            preview_url=preview_url
        )
        
        return jsonify({
            "success": True,
            "template_id": template_id,
            "message": "Template uploaded successfully",
            "preview_url": preview_url
        })
        
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@admin_bp.route('/admin/templates', methods=['GET'])
def get_admin_templates():
    """Get all templates for admin management"""
    try:
        category = request.args.get('category')
        template_type = request.args.get('template_type')
        
        templates = db.get_templates(category=category, template_type=template_type)
        
        # Format for admin interface
        result = []
        for template in templates:
            result.append({
                "id": template['id'],
                "name": template['name'],
                "category": template['category'],
                "template_type": template['template_type'],
                "preview_url": template['preview_url'],
                "created_at": template['created_at'],
                "updated_at": template['updated_at'],
                "svg_size": len(template['svg_content']) if template['svg_content'] else 0
            })
        
        return jsonify({
            "templates": result,
            "total": len(result)
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get templates: {str(e)}"}), 500

@admin_bp.route('/admin/templates/<template_id>', methods=['GET'])
def get_admin_template(template_id):
    """Get specific template with full SVG content"""
    try:
        template = db.get_template_by_id(template_id)
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        return jsonify({
            "template": template
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get template: {str(e)}"}), 500

@admin_bp.route('/admin/templates/<template_id>', methods=['PUT'])
def update_admin_template(template_id):
    """Update template"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get current template
        template = db.get_template_by_id(template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Update fields
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'category' in data:
            update_data['category'] = data['category']
        if 'template_type' in data:
            update_data['template_type'] = data['template_type']
        if 'svg_content' in data:
            update_data['svg_content'] = data['svg_content']
            # Regenerate preview if SVG content changed
            preview_url = generate_preview_from_svg(data['svg_content'], template_id)
            if preview_url:
                update_data['preview_url'] = preview_url
        
        # Update in database
        db.update_template(template_id, **update_data)
        
        return jsonify({
            "success": True,
            "message": "Template updated successfully"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to update template: {str(e)}"}), 500

@admin_bp.route('/admin/templates/<template_id>', methods=['DELETE'])
def delete_admin_template(template_id):
    """Delete template"""
    try:
        # Check if template exists
        template = db.get_template_by_id(template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Delete from database
        db.delete_template(template_id)
        
        # Try to delete preview file
        if template['preview_url']:
            try:
                preview_filename = template['preview_url'].split('/')[-1]
                preview_path = os.path.join(PREVIEW_FOLDER, preview_filename)
                if os.path.exists(preview_path):
                    os.remove(preview_path)
            except:
                pass  # Don't fail if preview deletion fails
        
        return jsonify({
            "success": True,
            "message": "Template deleted successfully"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete template: {str(e)}"}), 500

@admin_bp.route('/admin/preview/<filename>')
def serve_preview(filename):
    """Serve preview images"""
    try:
        preview_path = os.path.join(PREVIEW_FOLDER, filename)
        if os.path.exists(preview_path):
            return send_file(preview_path, mimetype='image/png')
        else:
            return jsonify({"error": "Preview not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to serve preview: {str(e)}"}), 500

@admin_bp.route('/admin/categories', methods=['GET'])
def get_categories():
    """Get all available categories"""
    try:
        templates = db.get_templates()
        categories = list(set(template['category'] for template in templates))
        categories.sort()
        
        return jsonify({
            "categories": categories
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get categories: {str(e)}"}), 500

@admin_bp.route('/admin/regenerate-preview/<template_id>', methods=['POST'])
def regenerate_preview(template_id):
    """Regenerate preview for a template"""
    try:
        template = db.get_template_by_id(template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Generate new preview
        preview_url = generate_preview_from_svg(template['svg_content'], template_id)
        
        if preview_url:
            # Update database
            db.update_template(template_id, preview_url=preview_url)
            
            return jsonify({
                "success": True,
                "preview_url": preview_url,
                "message": "Preview regenerated successfully"
            })
        else:
            return jsonify({"error": "Failed to generate preview"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Failed to regenerate preview: {str(e)}"}), 500

@admin_bp.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get admin statistics"""
    try:
        templates = db.get_templates()
        
        # Count by category
        category_counts = {}
        type_counts = {}
        
        for template in templates:
            category = template['category']
            template_type = template['template_type']
            
            category_counts[category] = category_counts.get(category, 0) + 1
            type_counts[template_type] = type_counts.get(template_type, 0) + 1
        
        return jsonify({
            "total_templates": len(templates),
            "categories": category_counts,
            "template_types": type_counts,
            "database_path": db.db_path
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500

