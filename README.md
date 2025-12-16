# Yieldera Automated Visualization System

🗺️ **Production-ready automated cartographic system for agricultural intelligence platforms**

Transform manual GEE → ArcMap workflows into automated, publication-quality map generation with real-time progress tracking and multiple export formats.

## 🚀 Quick Start for Render Deployment

### Prerequisites
- [Render.com](https://render.com) account
- Google Earth Engine service account
- AWS S3 bucket (optional, for enhanced storage)

### 1. Deploy to Render

#### Backend API Service
1. Connect this repository to Render
2. Create a new **Web Service**
3. Configure:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: `Python 3.11`
   - **Region**: Choose closest to your users

#### Worker Service  
1. Create another **Web Service** for the worker
2. Configure:
   - **Build Command**: `pip install -r backend/requirements.txt` 
   - **Start Command**: `celery -A backend.celery_app worker --loglevel=info`
   - **Environment**: `Python 3.11`

#### Database
1. Create **PostgreSQL** database in Render
2. Copy the `DATABASE_URL` from Render dashboard

#### Redis
1. Create **Redis** instance in Render  
2. Copy the `REDIS_URL` from Render dashboard

### 2. Environment Variables

Set these in your Render services:

```bash
# Database
DATABASE_URL=<from_render_postgresql>
REDIS_URL=<from_render_redis>

# Google Earth Engine
GOOGLE_APPLICATION_CREDENTIALS_JSON=<paste_service_account_json>

# Storage (optional)
AWS_ACCESS_KEY_ID=<your_aws_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret>
AWS_S3_BUCKET=yieldera-visualizations
AWS_REGION=us-east-1

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_WORKERS=4
VISUALIZATION_STORAGE_PATH=/tmp/visualizations
```

### 3. Frontend Deployment

#### Option A: Render Static Site
1. Create **Static Site** in Render
2. Configure:
   - **Build Command**: `npm run build`
   - **Publish Directory**: `dist`

#### Option B: Integrate with existing Yieldera frontend
Copy the React components from `frontend/` into your existing application.

## 📁 Project Structure

```
yieldera-automated-visualization/
├── backend/                    # FastAPI backend service
│   ├── main.py                # Main application entry
│   ├── celery_app.py          # Celery configuration
│   ├── models.py              # Database models  
│   ├── visualization/         # Core visualization modules
│   ├── api/                   # API endpoints
│   └── requirements.txt       # Python dependencies
├── frontend/                   # React frontend components
│   ├── src/                   # Source components
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Build configuration
├── docs/                      # Documentation
├── scripts/                   # Deployment scripts
└── README.md                  # This file
```

## 🎯 Features

### For End Users
- **One-click Analysis**: Select region → Generate professional map
- **Real-time Progress**: Live updates during processing
- **Multiple Formats**: Export PNG, PDF, SVG, GeoTIFF
- **Preset Regions**: Quick analysis for common areas
- **Publication Quality**: Professional cartographic output

### For Developers  
- **Scalable Architecture**: Render auto-scaling
- **Background Processing**: Celery job queue
- **Database Tracking**: PostgreSQL for job management
- **API Integration**: RESTful endpoints + WebSocket updates
- **Monitoring Ready**: Built-in health checks and metrics

## 🔧 Technical Architecture

```
User Interface (React)
    ↓ HTTP/WebSocket
Render Load Balancer
    ↓
FastAPI Application (Auto-scaled)
    ↓
Celery Workers (Background jobs)
    ↓
Google Earth Engine → Cartographic Engine → PostgreSQL + Storage
```

## 📊 API Endpoints

```bash
# Start visualization job
POST /api/v1/visualization/generate
{
  "region_name": "Zimbabwe", 
  "geometry": {...},
  "start_date": "2025-11-01",
  "end_date": "2025-12-15"
}

# Check job status
GET /api/v1/visualization/jobs/{job_id}/status

# Export results
POST /api/v1/visualization/export
{
  "job_id": "...",
  "format": "png",
  "resolution": 300
}

# WebSocket for real-time updates
WS /ws/visualization-jobs/{job_id}
```

## 🎨 Cartographic Output

Produces professional maps matching ArcMap quality:
- ✅ Drought risk color schemes
- ✅ Professional legends and scale bars
- ✅ Title blocks with data attribution
- ✅ North arrows and grid references
- ✅ Statistical summaries
- ✅ Export-ready at 300+ DPI

## 🔐 Security

- ✅ Environment-based configuration
- ✅ Database connection encryption
- ✅ Rate limiting on API endpoints
- ✅ Input validation and sanitization
- ✅ Error handling without data exposure

## 📈 Monitoring

Built-in health checks and metrics:
- `/health` - Service health
- `/metrics` - Prometheus metrics
- Database connection monitoring
- GEE authentication status
- Worker queue monitoring

## 🚀 Performance

- **Concurrent Processing**: Multiple analysis jobs
- **Caching**: Results caching for similar regions
- **Auto-scaling**: Render handles traffic spikes
- **Optimized Storage**: Automatic cleanup policies

## 📞 Support

For technical support or customization requests:
- 📧 Contact: Kudzai Munyukwa (Yieldera)
- 🔗 Platform: [yieldera.com](https://yieldera.com)

---

**Built for Agricultural Intelligence** | **Powered by Google Earth Engine** | **Deployed on Render**
