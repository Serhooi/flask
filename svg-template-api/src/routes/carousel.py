from flask import Blueprint, jsonify, request, send_from_directory
import os
import uuid
import json
from datetime import datetime
import threading
import time
from src.complete_svg_processor import CompleteSVGProcessor

carousel_bp = Blueprint('carousel', __name__)

# In-memory storage for carousel data (in production, use Redis or database)
CAROUSEL_STORAGE = {}
CAROUSEL_STATUS = {}

def generate_carousel_async(carousel_id, carousel_data):
    """Background task to generate carousel slides"""
    try:
        CAROUSEL_STATUS[carousel_id] = "processing"
        
        processor = CompleteSVGProcessor()
        slides = []
        
        for i, slide_data in enumerate(carousel_data['slides']):
            # Load the appropriate template
            template_id = slide_data['templateId']
            svg_file = "post(9).svg"  # For now, using the same template
            
            # Process the slide
            result = processor.process_svg_complete(
                svg_file=svg_file,
                replacements=slide_data['replacements'],
                canvas_width=carousel_data.get('canvas_width', 1080)
            )
            
            if result['success']:
                slide_url = f"https://api.yoursite.com/images/carousel-{carousel_id}-slide-{i+1}.png"
                slides.append({
                    "slide_number": i + 1,
                    "template_id": template_id,
                    "url": slide_url,
                    "status": "completed"
                })
            else:
                slides.append({
                    "slide_number": i + 1,
                    "template_id": template_id,
                    "url": None,
                    "status": "failed",
                    "error": result.get('error', 'Unknown error')
                })
        
        # Update carousel data
        CAROUSEL_STORAGE[carousel_id]['slides'] = slides
        CAROUSEL_STORAGE[carousel_id]['status'] = "completed"
        CAROUSEL_STORAGE[carousel_id]['completed_at'] = datetime.utcnow().isoformat()
        CAROUSEL_STATUS[carousel_id] = "completed"
        
    except Exception as e:
        CAROUSEL_STATUS[carousel_id] = "failed"
        CAROUSEL_STORAGE[carousel_id]['status'] = "failed"
        CAROUSEL_STORAGE[carousel_id]['error'] = str(e)

@carousel_bp.route('/carousel', methods=['POST'])
def create_carousel():
    """Create a new carousel"""
    
    data = request.get_json()
    
    # Validate required fields
    if not data or 'name' not in data:
        return jsonify({
            "success": False,
            "error": "Missing required field: name"
        }), 400
    
    # Generate unique carousel ID
    carousel_id = str(uuid.uuid4())
    
    # Store carousel data
    carousel_data = {
        "id": carousel_id,
        "name": data['name'],
        "status": "created",
        "created_at": datetime.utcnow().isoformat(),
        "slides": [],
        "canvas_width": data.get('canvas_width', 1080)
    }
    
    CAROUSEL_STORAGE[carousel_id] = carousel_data
    CAROUSEL_STATUS[carousel_id] = "created"
    
    return jsonify({
        "success": True,
        "carousel_id": carousel_id,
        "status": "created",
        "message": "Carousel created successfully"
    })

@carousel_bp.route('/carousel/<carousel_id>/generate', methods=['POST'])
def generate_carousel(carousel_id):
    """Start carousel generation process"""
    
    if carousel_id not in CAROUSEL_STORAGE:
        return jsonify({
            "success": False,
            "error": "Carousel not found"
        }), 404
    
    data = request.get_json()
    
    # Validate slides data
    if not data or 'slides' not in data or not data['slides']:
        return jsonify({
            "success": False,
            "error": "Missing or empty slides data"
        }), 400
    
    # Validate slide structure
    for i, slide in enumerate(data['slides']):
        if 'templateId' not in slide or 'replacements' not in slide:
            return jsonify({
                "success": False,
                "error": f"Slide {i+1} missing required fields: templateId, replacements"
            }), 400
    
    # Update carousel with slides data
    CAROUSEL_STORAGE[carousel_id]['slides_data'] = data['slides']
    CAROUSEL_STORAGE[carousel_id]['canvas_width'] = data.get('canvas_width', 1080)
    CAROUSEL_STORAGE[carousel_id]['status'] = "generating"
    CAROUSEL_STATUS[carousel_id] = "generating"
    
    # Start background generation
    thread = threading.Thread(
        target=generate_carousel_async,
        args=(carousel_id, CAROUSEL_STORAGE[carousel_id])
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "carousel_id": carousel_id,
        "status": "generating",
        "message": "Carousel generation started",
        "estimated_time": f"{len(data['slides']) * 2} seconds"
    })

@carousel_bp.route('/carousel/<carousel_id>/slides')
def get_carousel_slides(carousel_id):
    """Get carousel slides and their URLs"""
    
    if carousel_id not in CAROUSEL_STORAGE:
        return jsonify({
            "success": False,
            "error": "Carousel not found"
        }), 404
    
    carousel = CAROUSEL_STORAGE[carousel_id]
    status = CAROUSEL_STATUS.get(carousel_id, "unknown")
    
    response = {
        "success": True,
        "carousel_id": carousel_id,
        "name": carousel['name'],
        "status": status,
        "created_at": carousel['created_at'],
        "slides": carousel.get('slides', []),
        "total_slides": len(carousel.get('slides', []))
    }
    
    if status == "completed":
        response['completed_at'] = carousel.get('completed_at')
    elif status == "failed":
        response['error'] = carousel.get('error')
    
    return jsonify(response)

@carousel_bp.route('/carousel/<carousel_id>/status')
def get_carousel_status(carousel_id):
    """Get carousel generation status"""
    
    if carousel_id not in CAROUSEL_STORAGE:
        return jsonify({
            "success": False,
            "error": "Carousel not found"
        }), 404
    
    carousel = CAROUSEL_STORAGE[carousel_id]
    status = CAROUSEL_STATUS.get(carousel_id, "unknown")
    
    response = {
        "success": True,
        "carousel_id": carousel_id,
        "status": status,
        "created_at": carousel['created_at']
    }
    
    if status == "generating":
        # Calculate progress based on completed slides
        total_slides = len(carousel.get('slides_data', []))
        completed_slides = len([s for s in carousel.get('slides', []) if s.get('status') == 'completed'])
        response['progress'] = {
            "completed": completed_slides,
            "total": total_slides,
            "percentage": int((completed_slides / total_slides) * 100) if total_slides > 0 else 0
        }
    elif status == "completed":
        response['completed_at'] = carousel.get('completed_at')
        response['slides_count'] = len(carousel.get('slides', []))
    elif status == "failed":
        response['error'] = carousel.get('error')
    
    return jsonify(response)

@carousel_bp.route('/carousel/<carousel_id>')
def get_carousel_details(carousel_id):
    """Get full carousel details"""
    
    if carousel_id not in CAROUSEL_STORAGE:
        return jsonify({
            "success": False,
            "error": "Carousel not found"
        }), 404
    
    carousel = CAROUSEL_STORAGE[carousel_id]
    status = CAROUSEL_STATUS.get(carousel_id, "unknown")
    
    return jsonify({
        "success": True,
        "carousel": {
            **carousel,
            "status": status
        }
    })

@carousel_bp.route('/carousels')
def list_carousels():
    """List all carousels"""
    
    carousels = []
    for carousel_id, carousel_data in CAROUSEL_STORAGE.items():
        status = CAROUSEL_STATUS.get(carousel_id, "unknown")
        carousels.append({
            "id": carousel_id,
            "name": carousel_data['name'],
            "status": status,
            "created_at": carousel_data['created_at'],
            "slides_count": len(carousel_data.get('slides', []))
        })
    
    return jsonify({
        "success": True,
        "carousels": carousels,
        "total": len(carousels)
    })

