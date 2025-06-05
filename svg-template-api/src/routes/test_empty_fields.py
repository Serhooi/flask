# Simple endpoint to test SVG processing with empty fields
@carousel_bp.route('/carousel/test-empty-fields', methods=['POST'])
def test_empty_fields():
    """Test endpoint for empty field handling"""
    try:
        data = request.get_json()
        
        if not data or 'template_id' not in data:
            return jsonify({"error": "template_id is required"}), 400
        
        # Get template from database
        template = db.get_template_by_id(data['template_id'])
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Get replacements (can include empty fields)
        replacements = data.get('replacements', {})
        
        # Process with empty field handling
        result = process_svg_with_empty_field_handling(
            svg_content=template['svg_content'],
            replacements=replacements
        )
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "SVG processed successfully",
                "dyno_fields_found": result['dyno_fields_found'],
                "processed_svg_length": len(result['svg_content']),
                "empty_fields_handled": True
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Test failed: {str(e)}"
        }), 500

