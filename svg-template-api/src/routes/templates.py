from flask import Blueprint, jsonify, request
import os

templates_bp = Blueprint('templates', __name__)

# Mock template data - in production this would come from database
FLYER_TEMPLATES = [
    {
        "id": "modern-open-house-main",
        "name": "Modern Open House - Main",
        "category": "open-house",
        "preview_url": "https://api.yoursite.com/previews/modern-open-house-main.png",
        "template_type": "flyer",
        "template_role": "main",
        "svg_file": "post(9).svg"
    },
    {
        "id": "modern-open-house-photo",
        "name": "Modern Open House - Photo",
        "category": "open-house", 
        "preview_url": "https://api.yoursite.com/previews/modern-open-house-photo.png",
        "template_type": "flyer",
        "template_role": "photo",
        "svg_file": "post(9).svg"
    },
    {
        "id": "luxury-sold-main",
        "name": "Luxury Sold - Main",
        "category": "sold",
        "preview_url": "https://api.yoursite.com/previews/luxury-sold-main.png",
        "template_type": "flyer",
        "template_role": "main",
        "svg_file": "post(9).svg"
    },
    {
        "id": "luxury-sold-photo",
        "name": "Luxury Sold - Photo", 
        "category": "sold",
        "preview_url": "https://api.yoursite.com/previews/luxury-sold-photo.png",
        "template_type": "flyer",
        "template_role": "photo",
        "svg_file": "post(9).svg"
    },
    {
        "id": "rental-listing-main",
        "name": "For Rent - Main",
        "category": "for-rent",
        "preview_url": "https://api.yoursite.com/previews/rental-listing-main.png", 
        "template_type": "flyer",
        "template_role": "main",
        "svg_file": "post(9).svg"
    },
    {
        "id": "rental-listing-photo",
        "name": "For Rent - Photo",
        "category": "for-rent",
        "preview_url": "https://api.yoursite.com/previews/rental-listing-photo.png",
        "template_type": "flyer", 
        "template_role": "photo",
        "svg_file": "post(9).svg"
    },
    {
        "id": "lease-commercial-main",
        "name": "Commercial Lease - Main",
        "category": "lease",
        "preview_url": "https://api.yoursite.com/previews/lease-commercial-main.png",
        "template_type": "flyer",
        "template_role": "main", 
        "svg_file": "post(9).svg"
    },
    {
        "id": "lease-commercial-photo",
        "name": "Commercial Lease - Photo",
        "category": "lease",
        "preview_url": "https://api.yoursite.com/previews/lease-commercial-photo.png",
        "template_type": "flyer",
        "template_role": "photo",
        "svg_file": "post(9).svg"
    }
]

QUICK_POST_TEMPLATES = [
    {
        "id": "quick-just-listed",
        "name": "Just Listed",
        "category": "quick-post",
        "preview_url": "https://api.yoursite.com/previews/quick-just-listed.png",
        "template_type": "quick-post",
        "svg_file": "post(9).svg"
    },
    {
        "id": "quick-price-reduced",
        "name": "Price Reduced", 
        "category": "quick-post",
        "preview_url": "https://api.yoursite.com/previews/quick-price-reduced.png",
        "template_type": "quick-post",
        "svg_file": "post(9).svg"
    },
    {
        "id": "quick-under-contract",
        "name": "Under Contract",
        "category": "quick-post", 
        "preview_url": "https://api.yoursite.com/previews/quick-under-contract.png",
        "template_type": "quick-post",
        "svg_file": "post(9).svg"
    },
    {
        "id": "quick-coming-soon",
        "name": "Coming Soon",
        "category": "quick-post",
        "preview_url": "https://api.yoursite.com/previews/quick-coming-soon.png", 
        "template_type": "quick-post",
        "svg_file": "post(9).svg"
    }
]

@templates_bp.route('/templates/flyers')
def get_flyer_templates():
    """Get all flyer templates organized by category"""
    
    # Optional category filter
    category = request.args.get('category')
    templates = FLYER_TEMPLATES
    
    if category:
        templates = [t for t in templates if t['category'] == category]
    
    # Group by category
    categories = {}
    for template in templates:
        cat = template['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)
    
    return jsonify({
        "success": True,
        "templates": templates,
        "categories": categories,
        "total": len(templates)
    })

@templates_bp.route('/templates/quick-posts')
def get_quick_post_templates():
    """Get all quick post templates"""
    
    return jsonify({
        "success": True,
        "templates": QUICK_POST_TEMPLATES,
        "total": len(QUICK_POST_TEMPLATES)
    })

@templates_bp.route('/templates/<template_id>')
def get_template_details(template_id):
    """Get detailed information about a specific template"""
    
    # Search in both flyer and quick post templates
    all_templates = FLYER_TEMPLATES + QUICK_POST_TEMPLATES
    template = next((t for t in all_templates if t['id'] == template_id), None)
    
    if not template:
        return jsonify({
            "success": False,
            "error": "Template not found"
        }), 404
    
    # Add additional details for the specific template
    template_details = template.copy()
    template_details.update({
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
        ],
        "supported_formats": ["PNG", "SVG"],
        "max_carousel_slides": 10
    })
    
    return jsonify({
        "success": True,
        "template": template_details
    })

@templates_bp.route('/templates/categories')
def get_template_categories():
    """Get all available template categories"""
    
    categories = [
        {
            "id": "open-house",
            "name": "Open House",
            "description": "Templates for open house events",
            "flyer_count": len([t for t in FLYER_TEMPLATES if t['category'] == 'open-house'])
        },
        {
            "id": "sold", 
            "name": "Sold",
            "description": "Templates for sold properties",
            "flyer_count": len([t for t in FLYER_TEMPLATES if t['category'] == 'sold'])
        },
        {
            "id": "for-rent",
            "name": "For Rent", 
            "description": "Templates for rental properties",
            "flyer_count": len([t for t in FLYER_TEMPLATES if t['category'] == 'for-rent'])
        },
        {
            "id": "lease",
            "name": "Lease",
            "description": "Templates for lease properties", 
            "flyer_count": len([t for t in FLYER_TEMPLATES if t['category'] == 'lease'])
        },
        {
            "id": "quick-post",
            "name": "Quick Posts",
            "description": "Templates for quick social media posts",
            "template_count": len(QUICK_POST_TEMPLATES)
        }
    ]
    
    return jsonify({
        "success": True,
        "categories": categories,
        "total": len(categories)
    })

