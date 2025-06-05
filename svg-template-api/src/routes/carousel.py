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
        
        processor = CompleteSVGProcessor()
        
        for slide in slides:
            try:
                # Get template from database
                template = db.get_template_by_id(slide['template_id'])
                if not template:
                    continue
                
                # Parse replacements
                replacements = json.loads(slide['replacements']) if slide['replacements'] else {}
                
                # Process the slide using SVG content from database
                result = processor.process_svg_content(
                    svg_content=template['svg_content'],
                    replacements=replacements,
                    canvas_width=1080
                )
                
                if result['success']:
                    # Generate permanent URL for the slide
                    slide_url = f"https://svg-template-api.onrender.com/api/carousel/{carousel_id}/slide/{slide['slide_number']}.png"
                    
                    # Update slide with image URL
                    db.update_slide_image_url(slide['id'], slide_url)
                    
                else:
                    print(f"Failed to process slide {slide['slide_number']}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"Error processing slide {slide['slide_number']}: {str(e)}")
                continue
        
        # Update carousel status
        db.update_carousel_status(carousel_id, "completed")
        PROCESSING_STATUS[carousel_id] = "completed"
        
    except Exception as e:
        print(f"Error in generate_carousel_async: {str(e)}")
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
        # This would serve the actual generated image file
        # For now, return a placeholder response
        return jsonify({
            "message": f"Slide {slide_number} for carousel {carousel_id}",
            "note": "Image serving not implemented yet"
        })
        
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

