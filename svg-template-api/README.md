# 🎨 SVG Template API - Complete System

## 🌟 Overview

This is a complete SVG template processing system with database storage, admin panel, and full API integration. The system allows you to:

- **Upload SVG templates** via admin panel
- **Store templates** in SQLite database
- **Auto-generate previews** from SVG files
- **Create carousels** with multiple slides
- **Process templates** with dynamic data
- **Return permanent URLs** for generated images

## 🏗️ Architecture

### Database Schema

```sql
-- Templates table
CREATE TABLE templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    template_type TEXT NOT NULL,  -- 'main' or 'photo'
    svg_content TEXT NOT NULL,
    preview_url TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Carousels table
CREATE TABLE carousels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Carousel slides table
CREATE TABLE carousel_slides (
    id TEXT PRIMARY KEY,
    carousel_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL,
    image_url TEXT,
    replacements TEXT,  -- JSON string
    created_at TIMESTAMP
);
```

### System Components

1. **Flask API** - REST endpoints for all operations
2. **SQLite Database** - Template and carousel storage
3. **Admin Panel** - Web interface for template management
4. **SVG Processor** - Core processing engine
5. **Preview Generator** - Automatic PNG preview creation

## 📚 API Documentation

### Templates Endpoints

#### Get Flyer Templates
```http
GET /api/templates/flyers
```

**Response:**
```json
{
  "success": true,
  "templates": [
    {
      "id": "template-123",
      "name": "Modern Open House",
      "category": "open-house",
      "template_type": "flyer",
      "template_role": "main",
      "preview_url": "/api/admin/preview/template-123_preview.png"
    }
  ],
  "categories": {
    "open-house": [...],
    "sold": [...]
  }
}
```

#### Get Quick Post Templates
```http
GET /api/templates/quick-posts
```

#### Get Template Categories
```http
GET /api/templates/categories
```

#### Get Template Details
```http
GET /api/templates/{template_id}
```

### Carousel Endpoints

#### Create Carousel
```http
POST /api/carousel
Content-Type: application/json

{
  "name": "Property Carousel",
  "slides": [
    {
      "templateId": "main-template-id",
      "replacements": {
        "dyno.agentName": "John Smith",
        "dyno.price": "$750,000",
        "dyno.address": "123 Luxury Lane Beverly Hills, CA"
      }
    },
    {
      "templateId": "photo-template-id",
      "replacements": {
        "dyno.propertyImage": "https://example.com/photo.jpg"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "carousel_id": "carousel-456",
  "slides_count": 2
}
```

#### Generate Carousel
```http
POST /api/carousel/{carousel_id}/generate
```

#### Get Carousel Slides
```http
GET /api/carousel/{carousel_id}/slides
```

**Response:**
```json
{
  "success": true,
  "carousel_id": "carousel-456",
  "status": "completed",
  "slides": [
    {
      "slide_number": 1,
      "template_id": "main-template-id",
      "url": "https://your-domain.com/api/carousel/carousel-456/slide/1.png",
      "status": "completed"
    }
  ]
}
```

### Admin Endpoints

#### Upload Template
```http
POST /api/admin/upload-template
Content-Type: multipart/form-data

file: [SVG file]
name: "Template Name"
category: "open-house"
template_type: "main"
```

#### Get Admin Templates
```http
GET /api/admin/templates
```

#### Update Template
```http
PUT /api/admin/templates/{template_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "category": "sold"
}
```

#### Delete Template
```http
DELETE /api/admin/templates/{template_id}
```

#### Get System Stats
```http
GET /api/admin/stats
```

## 🔧 Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python src/database_init.py
```

### 3. Run Application

```bash
python src/main.py
```

The application will be available at `http://localhost:5000`

## 🌐 Deployment on Render.com

### 1. Prepare Repository

1. Create a new GitHub repository
2. Upload all files from `svg-template-api/` folder
3. Ensure `requirements.txt` is in the root

### 2. Create Render Service

1. Go to [Render.com](https://render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository

### 3. Configure Service

**Settings:**
- **Name:** `svg-template-api`
- **Language:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python src/main.py`
- **Instance Type:** `Free` (or higher for production)

### 4. Environment Variables

Set these environment variables in Render dashboard:

```
FLASK_ENV=production
PORT=5000
```

### 5. Deploy

Click "Create Web Service" and wait for deployment to complete.

## 🎯 Usage Examples

### React Integration

```javascript
// 1. Get available templates
const templates = await fetch('https://your-api.onrender.com/api/templates/flyers');

// 2. Create carousel
const carousel = await fetch('https://your-api.onrender.com/api/carousel', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  },
  body: JSON.stringify({
    name: "Property Carousel",
    slides: [
      {
        templateId: "open-house-main",
        replacements: {
          "dyno.agentName": "John Smith",
          "dyno.price": "$750,000"
        }
      }
    ]
  })
});

// 3. Start generation
await fetch(`https://your-api.onrender.com/api/carousel/${carouselId}/generate`, {
  method: 'POST'
});

// 4. Get results
const slides = await fetch(`https://your-api.onrender.com/api/carousel/${carouselId}/slides`);
```

### Admin Panel Usage

1. **Access Admin Panel:** Go to your deployed URL
2. **Click "Admin Panel" tab**
3. **Upload Templates:**
   - Drag & drop SVG files
   - Fill in template name and category
   - Select template type (main/photo)
   - Click upload

4. **Manage Templates:**
   - View all templates in "Templates" tab
   - Filter by category
   - Delete unwanted templates

## 🔍 Features

### ✅ Template Management
- Upload SVG files via web interface
- Auto-generate PNG previews
- Categorize templates (Open House, Sold, For Rent, Lease)
- Main/Photo template types for carousel logic

### ✅ SVG Processing
- Replace text fields (agent name, price, address, etc.)
- Replace images (property photos, logos, headshots)
- Auto-wrap long addresses to multiple lines
- Consistent spacing and positioning

### ✅ Carousel Creation
- Multi-slide carousels
- First slide: Main template with all info
- Additional slides: Photo templates with different images
- Permanent URLs for generated images

### ✅ Database Storage
- SQLite database for templates and carousels
- Persistent storage of all data
- Automatic database initialization

### ✅ Admin Interface
- Web-based admin panel
- Drag & drop file uploads
- Template preview generation
- System statistics

### ✅ API Integration
- RESTful API design
- JSON responses
- Error handling
- CORS support

## 🚀 Production Considerations

### Performance
- Use Redis for carousel processing status (instead of in-memory)
- Implement image caching
- Add database connection pooling

### Security
- Implement proper authentication
- Validate SVG files for security
- Add rate limiting
- Use HTTPS in production

### Scalability
- Move to PostgreSQL for larger datasets
- Implement background job queue (Celery)
- Add CDN for image serving
- Horizontal scaling with load balancer

## 📞 Support

For issues or questions:
1. Check the admin panel for system stats
2. Review API endpoint responses
3. Check application logs
4. Verify database connectivity

## 🎊 Success!

Your SVG Template API is now ready for production use with:
- ✅ Complete database system
- ✅ Admin panel for template management
- ✅ Full API integration
- ✅ Automatic preview generation
- ✅ Carousel creation workflow
- ✅ Ready for React integration

