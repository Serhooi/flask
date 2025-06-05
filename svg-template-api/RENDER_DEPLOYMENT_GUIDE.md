# 🚀 Render.com Deployment Guide

## Quick Deploy Steps

### 1. Prepare GitHub Repository

```bash
# Create new repository on GitHub
# Upload these files to repository root:
├── src/
│   ├── main.py
│   ├── complete_svg_processor.py
│   ├── database_init.py
│   ├── models/
│   ├── routes/
│   └── static/
├── requirements.txt
└── README.md
```

### 2. Create Render Service

1. Go to [render.com](https://render.com)
2. Sign up/Login with GitHub
3. Click **"New"** → **"Web Service"**
4. Select your repository

### 3. Configure Service

**Basic Settings:**
- **Name:** `svg-template-api`
- **Language:** `Python 3`
- **Branch:** `main`
- **Root Directory:** (leave empty)

**Build & Deploy:**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python src/main.py`

**Instance:**
- **Instance Type:** `Free` (for testing) or `Starter` (for production)

### 4. Environment Variables

Click **"Advanced"** and add:

```
FLASK_ENV=production
PORT=5000
```

### 5. Deploy

1. Click **"Create Web Service"**
2. Wait for build to complete (5-10 minutes)
3. Your API will be available at: `https://your-service-name.onrender.com`

## 🔧 Post-Deployment

### Test Your API

```bash
# Health check
curl https://your-service-name.onrender.com/api/health

# Get templates
curl https://your-service-name.onrender.com/api/templates/flyers
```

### Access Admin Panel

1. Go to: `https://your-service-name.onrender.com`
2. Click **"Admin Panel"** tab
3. Upload your SVG templates
4. Test carousel creation

## 🎯 Integration with Your React App

Update your React app to use the new API:

```javascript
const API_BASE = 'https://your-service-name.onrender.com/api';

// Get templates
const templates = await fetch(`${API_BASE}/templates/flyers`);

// Create carousel
const carousel = await fetch(`${API_BASE}/carousel`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  },
  body: JSON.stringify(carouselData)
});
```

## 🚨 Troubleshooting

### Build Fails
- Check `requirements.txt` is in repository root
- Verify Python version compatibility
- Check for syntax errors in code

### Service Won't Start
- Verify `python src/main.py` command
- Check environment variables
- Review build logs in Render dashboard

### Database Issues
- Database auto-initializes on first run
- Check file permissions
- Verify SQLite is working

### API Not Responding
- Check service status in Render dashboard
- Verify CORS settings
- Test with curl commands

## 🎊 Success!

Your SVG Template API is now live and ready for production use!

**Next Steps:**
1. Upload your SVG templates via admin panel
2. Test carousel creation
3. Integrate with your React application
4. Monitor performance and usage

