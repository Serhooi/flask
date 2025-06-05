from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime
import base64
import io

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
        # Try to use cairosvg if available, otherwise create simple preview
        try:
            import cairosvg
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
            
        except ImportError:
            # Fallback: create simple text preview
            from PIL import Image, ImageDraw, ImageFont
            
            # Create simple preview image
            img = Image.new('RGB', (400, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            # Draw simple preview text
            draw.text((20, 20), "SVG Template", fill='black', font=font)
            draw.text((20, 50), f"ID: {template_id[:20]}...", fill='gray', font=font)
            draw.text((20, 80), "Preview not available", fill='gray', font=font)
            
            # Save preview file
            preview_filename = f"{template_id}_preview.png"
            preview_path = os.path.join(PREVIEW_FOLDER, preview_filename)
            img.save(preview_path)
            
            return f"/api/admin/preview/{preview_filename}"
        
    except Exception as e:
        print(f"Error generating preview: {e}")
        return None

@admin_bp.route('/admin/upload-template', methods=['POST'])
def upload_template():
    """Upload a new SVG template with optimization for large files"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file provided",
                "error_code": "NO_FILE"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected",
                "error_code": "NO_FILE_SELECTED"
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": "Only SVG files are allowed",
                "error_code": "INVALID_FILE_TYPE"
            }), 400
        
        # Get form data
        name = request.form.get('name')
        category = request.form.get('category')
        template_type = request.form.get('template_type', 'main')
        
        if not name or not category:
            return jsonify({
                "success": False,
                "error": "Name and category are required",
                "error_code": "MISSING_FIELDS"
            }), 400
        
        # ✅ READ SVG CONTENT WITH SIZE CHECK
        try:
            svg_content = file.read().decode('utf-8')
            file_size = len(svg_content.encode('utf-8'))
            
            # Log file size for debugging
            print(f"Processing SVG file: {file.filename}, Size: {file_size / 1024 / 1024:.2f}MB")
            
            if file_size > 25 * 1024 * 1024:  # 25MB limit for processing
                return jsonify({
                    "success": False,
                    "error": "SVG file too large for processing. Maximum 25MB.",
                    "error_code": "FILE_TOO_LARGE_PROCESSING"
                }), 413
                
        except UnicodeDecodeError:
            return jsonify({
                "success": False,
                "error": "Invalid SVG file encoding",
                "error_code": "INVALID_ENCODING"
            }), 400
        
        # ✅ OPTIMIZE SVG CONTENT
        optimized_svg = optimize_svg_content(svg_content)
        
        # Generate unique template ID
        template_id = f"{category}-{template_type}-{str(uuid.uuid4())[:8]}"
        
        # ✅ GENERATE PREVIEW WITH TIMEOUT
        try:
            preview_url = generate_preview_from_svg(optimized_svg, template_id)
        except Exception as e:
            print(f"Preview generation failed: {str(e)}")
            # Use fallback preview
            preview_url = f"/api/admin/preview/placeholder.png"
        
        # ✅ SAVE TO DATABASE WITH ERROR HANDLING
        try:
            template_id = db.create_template(
                name=name,
                category=category,
                template_type=template_type,
                svg_content=optimized_svg,
                preview_url=preview_url
            )
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Database error: {str(e)}",
                "error_code": "DATABASE_ERROR"
            }), 500
        
        return jsonify({
            "success": True,
            "template_id": template_id,
            "message": "Template uploaded successfully",
            "preview_url": preview_url,
            "original_size": f"{file_size / 1024 / 1024:.2f}MB",
            "optimized_size": f"{len(optimized_svg.encode('utf-8')) / 1024 / 1024:.2f}MB"
        })
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "error_code": "UPLOAD_FAILED"
        }), 500

def optimize_svg_content(svg_content):
    """Advanced SVG optimization to reduce file size"""
    try:
        import re
        
        # Basic SVG optimization
        optimized = svg_content
        
        # ✅ REMOVE COMMENTS AND METADATA
        optimized = re.sub(r'<!--.*?-->', '', optimized, flags=re.DOTALL)
        optimized = re.sub(r'<metadata>.*?</metadata>', '', optimized, flags=re.DOTALL)
        optimized = re.sub(r'<title>.*?</title>', '', optimized, flags=re.DOTALL)
        optimized = re.sub(r'<desc>.*?</desc>', '', optimized, flags=re.DOTALL)
        
        # ✅ REMOVE FIGMA-SPECIFIC ATTRIBUTES
        figma_attrs = [
            r'\s+figma:type="[^"]*"',
            r'\s+data-figma-[^=]*="[^"]*"',
            r'\s+figma-[^=]*="[^"]*"'
        ]
        for attr in figma_attrs:
            optimized = re.sub(attr, '', optimized)
        
        # ✅ OPTIMIZE WHITESPACE
        optimized = re.sub(r'\s+', ' ', optimized)
        optimized = re.sub(r'>\s+<', '><', optimized)
        optimized = re.sub(r'\s+/>', '/>', optimized)
        
        # ✅ REMOVE EMPTY ATTRIBUTES
        optimized = re.sub(r'\s+[a-zA-Z-]+=""', '', optimized)
        
        # ✅ OPTIMIZE NUMBERS (ROUND TO 2 DECIMAL PLACES)
        def round_numbers(match):
            try:
                num = float(match.group(1))
                return f"{num:.2f}" if num != int(num) else str(int(num))
            except:
                return match.group(1)
        
        # Round coordinates and dimensions
        optimized = re.sub(r'([+-]?\d+\.\d{3,})', round_numbers, optimized)
        
        # ✅ REMOVE UNUSED DEFINITIONS
        # Find all used IDs
        used_ids = set(re.findall(r'(?:url\(#|href="#)([^")]+)', optimized))
        
        # Remove unused defs
        def filter_defs(match):
            def_content = match.group(1)
            def_ids = re.findall(r'id="([^"]+)"', def_content)
            
            filtered_defs = []
            for def_match in re.finditer(r'<[^>]+id="([^"]+)"[^>]*>.*?</[^>]+>', def_content, re.DOTALL):
                def_id = def_match.group(1)
                if def_id in used_ids:
                    filtered_defs.append(def_match.group(0))
            
            if filtered_defs:
                return f'<defs>{"".join(filtered_defs)}</defs>'
            return ''
        
        optimized = re.sub(r'<defs>(.*?)</defs>', filter_defs, optimized, flags=re.DOTALL)
        
        # ✅ COMPRESS PATHS (BASIC)
        def compress_path(match):
            path = match.group(1)
            # Remove unnecessary spaces in path data
            path = re.sub(r'\s+', ' ', path)
            path = re.sub(r'([MLHVCSQTAZmlhvcsqtaz])\s+', r'\1', path)
            return f'd="{path.strip()}"'
        
        optimized = re.sub(r'd="([^"]+)"', compress_path, optimized)
        
        # ✅ FINAL CLEANUP
        optimized = optimized.strip()
        
        # Calculate compression ratio
        original_size = len(svg_content.encode('utf-8'))
        optimized_size = len(optimized.encode('utf-8'))
        compression_ratio = (1 - optimized_size / original_size) * 100
        
        print(f"SVG optimization: {original_size} → {optimized_size} bytes ({compression_ratio:.1f}% reduction)")
        
        return optimized
        
    except Exception as e:
        print(f"SVG optimization failed: {str(e)}")
        return svg_content  # Return original if optimization fails

def compress_svg_with_gzip(svg_content):
    """Compress SVG content using gzip for storage"""
    try:
        import gzip
        import base64
        
        # Compress with gzip
        compressed = gzip.compress(svg_content.encode('utf-8'))
        
        # Encode as base64 for storage
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        print(f"GZIP compression: {len(svg_content)} → {len(compressed)} bytes")
        
        return encoded
        
    except Exception as e:
        print(f"GZIP compression failed: {str(e)}")
        return svg_content

def decompress_svg_from_gzip(compressed_data):
    """Decompress SVG content from gzip storage"""
    try:
        import gzip
        import base64
        
        # Decode from base64
        compressed = base64.b64decode(compressed_data.encode('utf-8'))
        
        # Decompress with gzip
        decompressed = gzip.decompress(compressed).decode('utf-8')
        
        return decompressed
        
    except Exception as e:
        print(f"GZIP decompression failed: {str(e)}")
        return compressed_data

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
            "success": True,
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


@admin_bp.route('/admin/carousel-templates', methods=['GET'])
def get_carousel_templates():
    """Get carousel template sets (grouped main + photo templates)"""
    try:
        # Get all templates
        templates = db.get_templates()
        
        # Group templates by base name (removing " - Main" or " - Photo" suffix)
        grouped = {}
        
        for template in templates:
            base_name = template['name']
            if base_name.endswith(' - Main') or base_name.endswith(' - Photo'):
                base_name = base_name.replace(' - Main', '').replace(' - Photo', '')
            
            if base_name not in grouped:
                grouped[base_name] = {
                    'base_name': base_name,
                    'category': template['category'],
                    'main_template': None,
                    'photo_template': None
                }
            
            if template['template_type'] == 'main':
                grouped[base_name]['main_template'] = template
            elif template['template_type'] == 'photo':
                grouped[base_name]['photo_template'] = template
        
        # Filter to only complete sets (both main and photo)
        complete_sets = []
        for base_name, group in grouped.items():
            if group['main_template'] and group['photo_template']:
                complete_sets.append({
                    'id': f"carousel-{group['main_template']['id']}-{group['photo_template']['id']}",
                    'name': base_name,
                    'category': group['category'],
                    'main_template_id': group['main_template']['id'],
                    'photo_template_id': group['photo_template']['id'],
                    'main_preview_url': group['main_template']['preview_url'],
                    'photo_preview_url': group['photo_template']['preview_url'],
                    'created_at': group['main_template']['created_at']
                })
        
        return jsonify({
            "success": True,
            "carousel_templates": complete_sets,
            "total": len(complete_sets)
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get carousel templates: {str(e)}"}), 500

@admin_bp.route('/admin/carousel-templates/<carousel_template_id>', methods=['GET'])
def get_carousel_template_details(carousel_template_id):
    """Get detailed information about a carousel template set"""
    try:
        # Parse carousel template ID to get main and photo template IDs
        if not carousel_template_id.startswith('carousel-'):
            return jsonify({"error": "Invalid carousel template ID"}), 400
        
        parts = carousel_template_id.replace('carousel-', '').split('-')
        if len(parts) < 2:
            return jsonify({"error": "Invalid carousel template ID format"}), 400
        
        main_template_id = parts[0]
        photo_template_id = parts[1]
        
        # Get both templates
        main_template = db.get_template_by_id(main_template_id)
        photo_template = db.get_template_by_id(photo_template_id)
        
        if not main_template or not photo_template:
            return jsonify({"error": "Carousel template not found"}), 404
        
        return jsonify({
            "success": True,
            "carousel_template": {
                "id": carousel_template_id,
                "name": main_template['name'].replace(' - Main', ''),
                "category": main_template['category'],
                "main_template": main_template,
                "photo_template": photo_template,
                "dyno_fields": [
                    "dyno.date",
                    "dyno.time", 
                    "dyno.price",
                    "dyno.address",
                    "dyno.bedrooms",
                    "dyno.bathrooms",
                    "dyno.agentName",
                    "dyno.agentPhone",
                    "dyno.agentEmail",
                    "dyno.features",
                    "dyno.propertyImage",
                    "dyno.logo",
                    "dyno.agentHeadshot"
                ]
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get carousel template details: {str(e)}"}), 500




