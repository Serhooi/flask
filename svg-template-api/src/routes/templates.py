from flask import Blueprint, request, jsonify
import os
from src.models.database import db

templates_bp = Blueprint('templates', __name__)

@templates_bp.route('/templates/flyers')
def get_flyer_templates():
    """Get all flyer templates organized by category"""
    try:
        # Optional category filter
        category = request.args.get('category')
        
        # Get templates from database
        templates = db.get_templates(category=category)
        
        # Filter only flyer templates (exclude quick-posts)
        flyer_templates = [t for t in templates if t['category'] != 'quick-post']
        
        # Format for API response
        formatted_templates = []
        for template in flyer_templates:
            formatted_templates.append({
                "id": template['id'],
                "name": template['name'],
                "category": template['category'],
                "preview_url": template['preview_url'],
                "template_type": "flyer",
                "template_role": template['template_type'],  # main or photo
                "created_at": template['created_at']
            })
        
        # Group by category
        categories = {}
        for template in formatted_templates:
            cat = template['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(template)
        
        return jsonify({
            "success": True,
            "templates": formatted_templates,
            "categories": categories,
            "total": len(formatted_templates)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get flyer templates: {str(e)}"
        }), 500

@templates_bp.route('/templates/quick-posts')
def get_quick_post_templates():
    """Get all quick post templates"""
    try:
        # Get quick-post templates from database
        templates = db.get_templates(category='quick-post')
        
        # Format for API response
        formatted_templates = []
        for template in templates:
            formatted_templates.append({
                "id": template['id'],
                "name": template['name'],
                "category": template['category'],
                "preview_url": template['preview_url'],
                "template_type": "quick-post",
                "created_at": template['created_at']
            })
        
        return jsonify({
            "success": True,
            "templates": formatted_templates,
            "total": len(formatted_templates)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get quick post templates: {str(e)}"
        }), 500

@templates_bp.route('/templates/<template_id>')
def get_template_details(template_id):
    """Get detailed information about a specific template"""
    try:
        # Get template from database
        template = db.get_template_by_id(template_id)
        
        if not template:
            return jsonify({
                "success": False,
                "error": "Template not found"
            }), 404
        
        # Add additional details for the specific template
        template_details = {
            "id": template['id'],
            "name": template['name'],
            "category": template['category'],
            "preview_url": template['preview_url'],
            "template_type": "flyer" if template['category'] != 'quick-post' else "quick-post",
            "template_role": template['template_type'],
            "created_at": template['created_at'],
            "updated_at": template['updated_at'],
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
        }
        
        return jsonify({
            "success": True,
            "template": template_details
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get template details: {str(e)}"
        }), 500

@templates_bp.route('/templates/<template_id>/preview')
def get_template_preview(template_id):
    """Get template preview image"""
    try:
        template = db.get_template_by_id(template_id)
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        if template['preview_url']:
            # Redirect to the actual preview URL
            from flask import redirect
            return redirect(template['preview_url'])
        else:
            return jsonify({"error": "Preview not available"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to get preview: {str(e)}"}), 500

@templates_bp.route('/templates/categories')
def get_template_categories():
    """Get all available template categories"""
    try:
        # Get all templates to count by category
        templates = db.get_templates()
        
        # Count templates by category
        category_counts = {}
        for template in templates:
            category = template['category']
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        
        # Define category information
        category_info = {
            "open-house": {
                "name": "Open House",
                "description": "Templates for open house events"
            },
            "sold": {
                "name": "Sold",
                "description": "Templates for sold properties"
            },
            "for-rent": {
                "name": "For Rent",
                "description": "Templates for rental properties"
            },
            "lease": {
                "name": "Lease",
                "description": "Templates for lease properties"
            },
            "quick-post": {
                "name": "Quick Posts",
                "description": "Templates for quick social media posts"
            }
        }
        
        # Build categories response
        categories = []
        for category_id, count in category_counts.items():
            info = category_info.get(category_id, {
                "name": category_id.title(),
                "description": f"Templates for {category_id}"
            })
            
            categories.append({
                "id": category_id,
                "name": info["name"],
                "description": info["description"],
                "template_count": count
            })
        
        return jsonify({
            "success": True,
            "categories": categories,
            "total": len(categories)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get categories: {str(e)}"
        }), 500


@templates_bp.route('/templates/carousel-sets')
def get_carousel_template_sets():
    """Get carousel template sets (main + photo pairs) for React integration"""
    try:
        # Get all templates
        templates = db.get_templates()
        
        # Group templates by base name and category
        grouped = {}
        
        for template in templates:
            # Skip quick-post templates
            if template['category'] == 'quick-post':
                continue
                
            base_name = template['name']
            if base_name.endswith(' - Main') or base_name.endswith(' - Photo'):
                base_name = base_name.replace(' - Main', '').replace(' - Photo', '')
            
            key = f"{template['category']}-{base_name}"
            
            if key not in grouped:
                grouped[key] = {
                    'base_name': base_name,
                    'category': template['category'],
                    'main_template': None,
                    'photo_template': None
                }
            
            if template['template_type'] == 'main':
                grouped[key]['main_template'] = template
            elif template['template_type'] == 'photo':
                grouped[key]['photo_template'] = template
        
        # Build carousel sets (only complete pairs)
        carousel_sets = []
        for key, group in grouped.items():
            if group['main_template'] and group['photo_template']:
                carousel_sets.append({
                    'id': f"carousel-{group['main_template']['id']}-{group['photo_template']['id']}",
                    'name': group['base_name'],
                    'category': group['category'],
                    'main_template_id': group['main_template']['id'],
                    'photo_template_id': group['photo_template']['id'],
                    'preview_url': group['main_template']['preview_url'],
                    'template_type': 'carousel',
                    'created_at': group['main_template']['created_at']
                })
        
        # Group by category for easier React integration
        categories = {}
        for carousel_set in carousel_sets:
            cat = carousel_set['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(carousel_set)
        
        return jsonify({
            "success": True,
            "carousel_sets": carousel_sets,
            "categories": categories,
            "total": len(carousel_sets)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get carousel template sets: {str(e)}"
        }), 500

@templates_bp.route('/templates/carousel-sets/<carousel_set_id>')
def get_carousel_set_details(carousel_set_id):
    """Get detailed information about a specific carousel template set"""
    try:
        # Parse carousel set ID
        if not carousel_set_id.startswith('carousel-'):
            return jsonify({
                "success": False,
                "error": "Invalid carousel set ID"
            }), 400
        
        parts = carousel_set_id.replace('carousel-', '').split('-')
        if len(parts) < 2:
            return jsonify({
                "success": False,
                "error": "Invalid carousel set ID format"
            }), 400
        
        main_template_id = parts[0]
        photo_template_id = parts[1]
        
        # Get both templates
        main_template = db.get_template_by_id(main_template_id)
        photo_template = db.get_template_by_id(photo_template_id)
        
        if not main_template or not photo_template:
            return jsonify({
                "success": False,
                "error": "Carousel template set not found"
            }), 404
        
        carousel_set_details = {
            "id": carousel_set_id,
            "name": main_template['name'].replace(' - Main', ''),
            "category": main_template['category'],
            "main_template_id": main_template_id,
            "photo_template_id": photo_template_id,
            "preview_url": main_template['preview_url'],
            "template_type": "carousel",
            "created_at": main_template['created_at'],
            "updated_at": main_template['updated_at'],
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
            "supported_formats": ["PNG"],
            "max_carousel_slides": 10
        }
        
        return jsonify({
            "success": True,
            "carousel_set": carousel_set_details
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get carousel set details: {str(e)}"
        }), 500

