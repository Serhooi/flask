from flask import Blueprint, jsonify, request, send_from_directory
import os
import uuid
import json
from datetime import datetime
import threading
import time
from src.complete_svg_processor import CompleteSVGProcessor
from src.models.database import db

carousel_bp = Blueprint('carousel', __name__)

# In-memory storage for processing status (in production, use Redis)
PROCESSING_STATUS = {}

def process_svg_with_empty_field_handling(svg_content, replacements):
    """Process SVG content with proper empty field handling"""
    try:
        # Import the processor
        from src.complete_svg_processor import CompleteSVGProcessor
        
        # Create processor instance
        processor = CompleteSVGProcessor(svg_content)
        
        # Process each replacement with empty field logic
        for field, value in replacements.items():
            if field.startswith('dyno.'):
                dyno_field = field[5:]  # Remove 'dyno.' prefix
                
                # 🔥 EMPTY FIELD HANDLING LOGIC
                if not value or str(value).strip() == "":
                    print(f"📝 Field {dyno_field} is empty - leaving blank")
                    processor.replace_text(dyno_field, "")
                else:
                    # Process non-empty fields normally
                    if dyno_field in processor.dyno_elements:
                        element_type = processor.dyno_elements[dyno_field]['type']
                        
                        if element_type == 'text':
                            processor.replace_text(dyno_field, str(value))
                        elif element_type == 'image' and os.path.exists(str(value)):
                            processor.replace_image(dyno_field, str(value))
        
        return {
            'success': True,
            'svg_content': processor.processed_svg,
            'dyno_fields_found': len(processor.dyno_elements)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'svg_content': svg_content  # Return original on error
        }

def generate_carousel_async(carousel_id):
    """Background task to generate carousel slides"""
    try:
        PROCESSING_STATUS[carousel_id] = "processing"
        
        # Get carousel from database
        carousel = db.get_carousel(carousel_id)
        if not carousel:
            PROCESSING_STATUS[carousel_id] = "failed"
            return
        
        # Get slides for this carousel
        slides = db.get_carousel_slides(carousel_id)
        if not slides:
            PROCESSING_STATUS[carousel_id] = "failed"
            return
        
        for slide in slides:
            try:
                # Get template from database
                template = db.get_template_by_id(slide['template_id'])
                if not template:
                    continue
                
                # Parse replacements
                replacements = json.loads(slide['replacements']) if slide['replacements'] else {}
                
                # 🔥 USE NEW EMPTY FIELD HANDLING FUNCTION
                result = process_svg_with_empty_field_handling(
                    svg_content=template['svg_content'],
                    replacements=replacements
                )
                
                if result['success']:
                    # Generate permanent URL for the slide
                    slide_url = f"https://svg-template-api.onrender.com/api/carousel/{carousel_id}/slide/{slide['slide_number']}.png"
                    
                    # Update slide with image URL
                    db.update_slide_image_url(slide['id'], slide_url)
                    
                    print(f"✅ Processed slide {slide['slide_number']} with {result['dyno_fields_found']} dynamic fields")
                    
                else:
                    print(f"❌ Failed to process slide {slide['slide_number']}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Error processing slide {slide['slide_number']}: {str(e)}")
                continue
        
        # Update carousel status
        db.update_carousel_status(carousel_id, "completed")
        PROCESSING_STATUS[carousel_id] = "completed"
        
    except Exception as e:
        print(f"❌ Error in generate_carousel_async: {str(e)}")
        db.update_carousel_status(carousel_id, "failed")
        PROCESSING_STATUS[carousel_id] = "failed"

@carousel_bp.route('/carousel', methods=['POST'])
def create_carousel():
    """Create a new carousel"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({"error": "Carousel name is required"}), 400
        
        if 'slides' not in data or not data['slides']:
            return jsonify({"error": "At least one slide is required"}), 400
        
        # Create carousel in database
        carousel_id = db.create_carousel(data['name'])
        
        # Create slides
        for i, slide_data in enumerate(data['slides']):
            if 'templateId' not in slide_data:
                return jsonify({"error": f"Template ID is required for slide {i+1}"}), 400
            
            # Verify template exists
            template = db.get_template_by_id(slide_data['templateId'])
            if not template:
                return jsonify({"error": f"Template {slide_data['templateId']} not found"}), 404
            
            # Create slide in database
            replacements_json = json.dumps(slide_data.get('replacements', {}))
            db.create_carousel_slide(
                carousel_id=carousel_id,
                template_id=slide_data['templateId'],
                slide_number=i + 1,
                replacements=replacements_json
            )
        
        return jsonify({
            "success": True,
            "carousel_id": carousel_id,
            "message": "Carousel created successfully",
            "slides_count": len(data['slides'])
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to create carousel: {str(e)}"}), 500

@carousel_bp.route('/carousel/<carousel_id>/generate', methods=['POST'])
def generate_carousel(carousel_id):
    """Start carousel generation process"""
    try:
        # Check if carousel exists
        carousel = db.get_carousel(carousel_id)
        if not carousel:
            return jsonify({"error": "Carousel not found"}), 404
        
        # Check if already processing
        if carousel_id in PROCESSING_STATUS and PROCESSING_STATUS[carousel_id] == "processing":
            return jsonify({
                "success": True,
                "message": "Carousel generation already in progress",
                "status": "processing"
            })
        
        # Update status to processing
        db.update_carousel_status(carousel_id, "processing")
        
        # Start background generation
        thread = threading.Thread(target=generate_carousel_async, args=(carousel_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Carousel generation started",
            "carousel_id": carousel_id,
            "status": "processing"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to start generation: {str(e)}"}), 500

@carousel_bp.route('/carousel/<carousel_id>/slides', methods=['GET'])
def get_carousel_slides(carousel_id):
    """Get carousel slides with URLs"""
    try:
        # Check if carousel exists
        carousel = db.get_carousel(carousel_id)
        if not carousel:
            return jsonify({"error": "Carousel not found"}), 404
        
        # Get slides from database
        slides = db.get_carousel_slides(carousel_id)
        
        # Format response
        formatted_slides = []
        for slide in slides:
            template = db.get_template_by_id(slide['template_id'])
            
            formatted_slides.append({
                "slide_number": slide['slide_number'],
                "template_id": slide['template_id'],
                "template_name": template['name'] if template else "Unknown",
                "url": slide['image_url'],
                "status": "completed" if slide['image_url'] else "pending",
                "created_at": slide['created_at']
            })
        
        return jsonify({
            "success": True,
            "carousel_id": carousel_id,
            "carousel_name": carousel['name'],
            "status": carousel['status'],
            "slides": formatted_slides,
            "total_slides": len(formatted_slides)
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get slides: {str(e)}"}), 500

@carousel_bp.route('/carousel/<carousel_id>/status', methods=['GET'])
def get_carousel_status(carousel_id):
    """Get carousel generation status"""
    try:
        # Check if carousel exists
        carousel = db.get_carousel(carousel_id)
        if not carousel:
            return jsonify({"error": "Carousel not found"}), 404
        
        # Get processing status
        processing_status = PROCESSING_STATUS.get(carousel_id, carousel['status'])
        
        # Get slides count
        slides = db.get_carousel_slides(carousel_id)
        completed_slides = len([s for s in slides if s['image_url']])
        
        return jsonify({
            "success": True,
            "carousel_id": carousel_id,
            "status": processing_status,
            "total_slides": len(slides),
            "completed_slides": completed_slides,
            "progress": (completed_slides / len(slides) * 100) if slides else 0,
            "created_at": carousel['created_at'],
            "updated_at": carousel['updated_at']
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get status: {str(e)}"}), 500

@carousel_bp.route('/carousel/<carousel_id>', methods=['GET'])
def get_carousel_details(carousel_id):
    """Get detailed carousel information"""
    try:
        # Check if carousel exists
        carousel = db.get_carousel(carousel_id)
        if not carousel:
            return jsonify({"error": "Carousel not found"}), 404
        
        # Get slides
        slides = db.get_carousel_slides(carousel_id)
        
        # Format slides with template information
        formatted_slides = []
        for slide in slides:
            template = db.get_template_by_id(slide['template_id'])
            replacements = json.loads(slide['replacements']) if slide['replacements'] else {}
            
            formatted_slides.append({
                "slide_number": slide['slide_number'],
                "template_id": slide['template_id'],
                "template_name": template['name'] if template else "Unknown",
                "template_category": template['category'] if template else "Unknown",
                "replacements": replacements,
                "url": slide['image_url'],
                "status": "completed" if slide['image_url'] else "pending"
            })
        
        return jsonify({
            "success": True,
            "carousel": {
                "id": carousel['id'],
                "name": carousel['name'],
                "status": carousel['status'],
                "created_at": carousel['created_at'],
                "updated_at": carousel['updated_at'],
                "slides": formatted_slides,
                "total_slides": len(formatted_slides)
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get carousel details: {str(e)}"}), 500

@carousel_bp.route('/carousel/<carousel_id>/slide/<int:slide_number>.png')
def serve_slide_image(carousel_id, slide_number):
    """Serve generated slide image"""
    try:
        # Get slide from database
        slides = db.get_carousel_slides(carousel_id)
        target_slide = None
        
        for slide in slides:
            if slide['slide_number'] == slide_number:
                target_slide = slide
                break
        
        if not target_slide:
            return jsonify({"error": "Slide not found"}), 404
        
        if not target_slide['image_url']:
            return jsonify({"error": "Slide not generated yet"}), 404
        
        # Check if image file exists
        image_path = f"src/static/carousel_images/{carousel_id}_slide_{slide_number}.png"
        
        if os.path.exists(image_path):
            return send_from_directory(
                os.path.dirname(os.path.abspath(image_path)),
                os.path.basename(image_path),
                mimetype='image/png'
            )
        else:
            # Generate image if it doesn't exist
            carousel = db.get_carousel(carousel_id)
            if not carousel:
                return jsonify({"error": "Carousel not found"}), 404
            
            # Get template
            template = db.get_template_by_id(target_slide['template_id'])
            if not template:
                return jsonify({"error": "Template not found"}), 404
            
            # Process SVG with replacements
            replacements = json.loads(target_slide['replacements']) if target_slide['replacements'] else {}
            
            # Use the SVG processor to generate image
            from src.complete_svg_processor import CompleteSVGProcessor
            processor = CompleteSVGProcessor()
            
            # Process SVG content
            processed_svg = processor.process_svg(template['svg_content'], replacements)
            
            # Convert to PNG
            from src.routes.admin import generate_preview_from_svg
            
            # Create carousel images directory if it doesn't exist
            os.makedirs("src/static/carousel_images", exist_ok=True)
            
            # Generate PNG from processed SVG
            import cairosvg
            from PIL import Image
            import io
            
            try:
                # Convert SVG to PNG
                png_data = cairosvg.svg2png(bytestring=processed_svg.encode('utf-8'))
                
                # Save to file
                with open(image_path, 'wb') as f:
                    f.write(png_data)
                
                # Return the image
                return send_from_directory(
                    os.path.dirname(os.path.abspath(image_path)),
                    os.path.basename(image_path),
                    mimetype='image/png'
                )
                
            except Exception as svg_error:
                # Fallback: create a simple placeholder image
                from PIL import Image, ImageDraw, ImageFont
                
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                except:
                    font = ImageFont.load_default()
                
                text = f"Slide {slide_number}\nCarousel: {carousel_id}\nGeneration Error"
                draw.text((50, 250), text, fill='black', font=font)
                
                img.save(image_path)
                
                return send_from_directory(
                    os.path.dirname(os.path.abspath(image_path)),
                    os.path.basename(image_path),
                    mimetype='image/png'
                )
        
    except Exception as e:
        return jsonify({"error": f"Failed to serve image: {str(e)}"}), 500

@carousel_bp.route('/carousels', methods=['GET'])
def list_carousels():
    """List all carousels"""
    try:
        # This would get all carousels from database
        # For now, return empty list
        return jsonify({
            "success": True,
            "carousels": [],
            "total": 0,
            "message": "Carousel listing not implemented yet"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to list carousels: {str(e)}"}), 500


@carousel_bp.route('/carousel/simple', methods=['POST'])
def create_simple_carousel():
    """Create carousel using carousel template set (simplified for React integration)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['carousel_set_id', 'name', 'property_data']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400
        
        carousel_set_id = data['carousel_set_id']
        carousel_name = data['name']
        property_data = data['property_data']
        property_images = data.get('property_images', [])
        
        # Parse carousel set ID to get template IDs
        if not carousel_set_id.startswith('carousel-'):
            return jsonify({"error": "Invalid carousel set ID"}), 400
        
        parts = carousel_set_id.replace('carousel-', '').split('-')
        if len(parts) < 2:
            return jsonify({"error": "Invalid carousel set ID format"}), 400
        
        main_template_id = parts[0]
        photo_template_id = parts[1]
        
        # Verify templates exist
        main_template = db.get_template_by_id(main_template_id)
        photo_template = db.get_template_by_id(photo_template_id)
        
        if not main_template or not photo_template:
            return jsonify({"error": "Carousel template set not found"}), 404
        
        # Create carousel in database
        carousel_id = db.create_carousel(carousel_name)
        
        # Create slides
        slides_created = 0
        
        # Slide 1: Main template with all property data
        main_replacements = property_data.copy()
        if property_images:
            main_replacements['dyno.propertyImage'] = property_images[0]
        
        db.create_carousel_slide(
            carousel_id=carousel_id,
            template_id=main_template_id,
            slide_number=1,
            replacements=json.dumps(main_replacements)
        )
        slides_created += 1
        
        # Additional slides: Photo template with different property images
        for i, image_url in enumerate(property_images[1:], start=2):
            photo_replacements = {
                'dyno.propertyImage': image_url
            }
            
            db.create_carousel_slide(
                carousel_id=carousel_id,
                template_id=photo_template_id,
                slide_number=i,
                replacements=json.dumps(photo_replacements)
            )
            slides_created += 1
        
        return jsonify({
            "success": True,
            "carousel_id": carousel_id,
            "slides_count": slides_created,
            "main_template_id": main_template_id,
            "photo_template_id": photo_template_id,
            "message": f"Carousel created with {slides_created} slides"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to create simple carousel: {str(e)}"}), 500

@carousel_bp.route('/carousel/from-template-set', methods=['POST'])
def create_carousel_from_template_set():
    """Create carousel from template set with automatic main/photo logic"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Required fields
        if 'template_set_name' not in data or 'category' not in data:
            return jsonify({"error": "template_set_name and category are required"}), 400
        
        template_set_name = data['template_set_name']
        category = data['category']
        carousel_name = data.get('name', f"{template_set_name} Carousel")
        property_data = data.get('property_data', {})
        property_images = data.get('property_images', [])
        
        # Find matching main and photo templates
        main_template_name = f"{template_set_name} - Main"
        photo_template_name = f"{template_set_name} - Photo"
        
        templates = db.get_templates(category=category)
        main_template = None
        photo_template = None
        
        for template in templates:
            if template['name'] == main_template_name and template['template_type'] == 'main':
                main_template = template
            elif template['name'] == photo_template_name and template['template_type'] == 'photo':
                photo_template = template
        
        if not main_template or not photo_template:
            return jsonify({
                "error": f"Template set '{template_set_name}' not found in category '{category}'"
            }), 404
        
        # Create carousel
        carousel_id = db.create_carousel(carousel_name)
        
        # Create slides
        slides_created = 0
        
        # Slide 1: Main template
        main_replacements = property_data.copy()
        if property_images:
            main_replacements['dyno.propertyImage'] = property_images[0]
        
        db.create_carousel_slide(
            carousel_id=carousel_id,
            template_id=main_template['id'],
            slide_number=1,
            replacements=json.dumps(main_replacements)
        )
        slides_created += 1
        
        # Additional slides: Photo template
        for i, image_url in enumerate(property_images[1:], start=2):
            photo_replacements = {
                'dyno.propertyImage': image_url
            }
            
            db.create_carousel_slide(
                carousel_id=carousel_id,
                template_id=photo_template['id'],
                slide_number=i,
                replacements=json.dumps(photo_replacements)
            )
            slides_created += 1
        
        return jsonify({
            "success": True,
            "carousel_id": carousel_id,
            "slides_count": slides_created,
            "main_template_id": main_template['id'],
            "photo_template_id": photo_template['id'],
            "template_set_name": template_set_name
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to create carousel from template set: {str(e)}"}), 500

