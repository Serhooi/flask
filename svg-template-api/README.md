# 🎨 SVG Template API - Complete System

## 🚀 Features
- ✅ **Template Previews** - Generate previews for all templates
- ✅ **Address Line Wrapping** - Automatically splits address into 3 lines
- ✅ **Perfect Headshot Cropping** - Object-fit: cover effect for circular containers
- ✅ **Logo Aspect Ratio** - Maintains proportions without stretching
- ✅ **Clean Photo Templates** - Removed artifacts and unwanted elements

## 📋 API Endpoints

### Templates
- `GET /api/templates/all-previews` - Get all templates with preview images
- `GET /api/templates/{id}/preview` - Generate preview for specific template

### Carousel Generation
- `POST /api/carousel` - Create new carousel
- `POST /api/carousel/{id}/generate` - Start generation
- `GET /api/carousel/{id}/slides` - Get generated slides

## 🛠️ Deployment

### Render.com
1. Connect your GitHub repository
2. Select "Web Service"
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python app.py`

### Environment Variables
- `PYTHON_VERSION`: `3.11.0`

## 🧪 Testing
- Health check: `GET /health`
- Should return: `{"status": "healthy", "version": "1.2.0-with-previews"}`

## 📝 Template Data Format

### Main Template
```json
{
  "templateId": "main-template",
  "replacements": {
    "dyno.date": "AUGUST 15 2028",
    "dyno.time": "6PM - 10PM",
    "dyno.propertyaddress": "789 Paradise Estate Boulevard, Beverly Hills, CA 90210",
    "dyno.price": "$28,500,000",
    "dyno.bedrooms": "11",
    "dyno.bathrooms": "15",
    "dyno.propertyfeatures": "infinity pool, wine cellar, home theater",
    "dyno.name": "Victoria Sterling",
    "dyno.phone": "+1 555 888 9999",
    "dyno.email": "victoria.sterling@luxuryrealty.com",
    "dyno.propertyimage": "https://example.com/property.jpg",
    "dyno.logo": "https://example.com/logo.png",
    "dyno.agentheadshot": "https://example.com/agent.jpg"
  }
}
```

### Photo Template
```json
{
  "templateId": "photo-template",
  "replacements": {
    "dyno.propertyimage": "https://example.com/interior.jpg"
  }
}
```

## 🎯 Fixed Issues
- ✅ Address now properly wraps to 3 lines
- ✅ Headshot fills circular container without distortion
- ✅ Logo maintains aspect ratio
- ✅ Photo template artifacts removed
- ✅ Template previews work correctly

Built with Flask, Pillow, and CairoSVG 🚀
