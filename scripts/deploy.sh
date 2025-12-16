#!/bin/bash

# =====================================
# Yieldera Automated Visualization System
# Render Deployment Script
# =====================================

set -e

echo "🚀 Starting Yieldera Visualization System deployment setup..."
echo "======================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check requirements
print_step "Checking system requirements..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    print_error "Node.js version 18+ required. Found version: $(node --version)"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3.11+ is not installed. Please install Python first."
    exit 1
fi

print_success "System requirements check passed"

# Install backend dependencies
print_step "Installing backend dependencies..."
cd backend
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    print_success "Backend dependencies installed"
else
    print_error "requirements.txt not found in backend directory"
    exit 1
fi

cd ..

# Install frontend dependencies
print_step "Installing frontend dependencies..."
cd frontend
if [ -f "package.json" ]; then
    npm install
    print_success "Frontend dependencies installed"
else
    print_error "package.json not found in frontend directory"
    exit 1
fi

cd ..

# Validate configuration files
print_step "Validating configuration files..."

required_files=(
    "backend/main.py"
    "backend/config.py" 
    "backend/models.py"
    "backend/celery_app.py"
    "frontend/package.json"
    "frontend/vite.config.js"
    "render.yaml"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        exit 1
    fi
done

print_success "All configuration files found"

# Test backend startup
print_step "Testing backend startup..."
cd backend
python3 -c "
import sys
sys.path.append('.')
try:
    from main import app
    print('✅ Backend imports successfully')
except Exception as e:
    print(f'❌ Backend import failed: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Backend startup test passed"
else
    print_error "Backend startup test failed"
    exit 1
fi

cd ..

# Test frontend build
print_step "Testing frontend build..."
cd frontend
npm run build

if [ $? -eq 0 ]; then
    print_success "Frontend build test passed"
else
    print_error "Frontend build test failed"
    exit 1
fi

cd ..

# Create environment template
print_step "Creating environment configuration template..."

cat > .env.example << 'EOF'
# =====================================
# Yieldera Visualization System - Environment Variables
# Copy this to .env and update with your actual values
# =====================================

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database (Render will provide this)
DATABASE_URL=postgresql://username:password@hostname:port/database

# Redis (Render will provide this)
REDIS_URL=redis://hostname:port

# Google Earth Engine (REQUIRED - Get from Google Cloud Console)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project",...}

# Storage
VISUALIZATION_STORAGE_PATH=/tmp/visualizations

# Performance
MAX_WORKERS=2
WORKER_CONCURRENCY=1

# Rate limiting
RATE_LIMIT_PER_MINUTE=60

# Cleanup
CLEANUP_DAYS=7

# AWS S3 (Optional - for enhanced file storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=yieldera-visualizations
AWS_REGION=us-east-1

# Frontend
VITE_API_BASE_URL=/api/v1
EOF

print_success "Environment template created (.env.example)"

# Create deployment checklist
print_step "Creating deployment checklist..."

cat > DEPLOYMENT_CHECKLIST.md << 'EOF'
# 🚀 Yieldera Visualization System - Deployment Checklist

## Pre-Deployment Requirements

### 1. Google Earth Engine Setup
- [ ] Create Google Cloud Project
- [ ] Enable Earth Engine API
- [ ] Create Service Account with Earth Engine permissions
- [ ] Download service account JSON key
- [ ] Test authentication with: `earthengine authenticate --service_account`

### 2. Render Account Setup
- [ ] Create Render account at https://render.com
- [ ] Connect GitHub repository
- [ ] Have credit card ready for paid plans (if needed)

## Deployment Steps

### 1. Fork/Upload Repository
- [ ] Fork this repository to your GitHub account
- [ ] Or upload as new repository

### 2. Deploy on Render

#### Option A: Automatic Deployment (Recommended)
1. [ ] Go to Render Dashboard
2. [ ] Click "New" → "Blueprint"
3. [ ] Connect your repository
4. [ ] Render will read `render.yaml` and create all services

#### Option B: Manual Service Creation
1. [ ] Create PostgreSQL database
2. [ ] Create Redis instance  
3. [ ] Create Web Service for API
4. [ ] Create Worker Service for Celery
5. [ ] Create Static Site for Frontend

### 3. Configure Environment Variables

Set these in each service:

#### API Service & Worker Service:
- [ ] `GOOGLE_APPLICATION_CREDENTIALS_JSON` - Your GEE service account JSON
- [ ] `DATABASE_URL` - Auto-provided by Render PostgreSQL
- [ ] `REDIS_URL` - Auto-provided by Render Redis
- [ ] `ENVIRONMENT=production`
- [ ] `LOG_LEVEL=INFO`

#### Optional (for S3 storage):
- [ ] `AWS_ACCESS_KEY_ID`
- [ ] `AWS_SECRET_ACCESS_KEY` 
- [ ] `AWS_S3_BUCKET`

### 4. Deploy Services
- [ ] Deploy database first
- [ ] Deploy Redis
- [ ] Deploy API service
- [ ] Deploy worker service
- [ ] Deploy frontend

### 5. Test Deployment
- [ ] Visit frontend URL
- [ ] Test API health check: `<api-url>/api/health`
- [ ] Try creating a visualization
- [ ] Verify WebSocket connections work
- [ ] Check logs for errors

## Post-Deployment

### 1. Monitoring Setup
- [ ] Set up Render log monitoring
- [ ] Configure health check alerts
- [ ] Monitor resource usage

### 2. Domain Configuration (Optional)
- [ ] Configure custom domain
- [ ] Set up SSL certificate
- [ ] Update CORS settings

### 3. Performance Optimization
- [ ] Monitor response times
- [ ] Adjust worker concurrency if needed
- [ ] Set up auto-scaling if needed

## Troubleshooting

### Common Issues:
1. **GEE Authentication Fails**: Check service account JSON format
2. **Database Connection Errors**: Verify DATABASE_URL format
3. **Worker Not Processing**: Check Redis connection and Celery logs
4. **Frontend Build Fails**: Check Node.js version (needs 18+)
5. **WebSocket Errors**: Verify backend URL in frontend config

### Getting Help:
- Check Render logs: Dashboard → Service → Logs
- API health check: `GET /api/health`
- API diagnostics: `GET /api/diagnostics/earth-engine`
EOF

print_success "Deployment checklist created (DEPLOYMENT_CHECKLIST.md)"

# Create quick start guide
print_step "Creating quick start guide..."

cat > QUICK_START.md << 'EOF'
# ⚡ Quick Start Guide - Yieldera Visualization System

## What This System Does

Transform your manual GEE → ArcMap workflow into automated, publication-quality map generation:

- **Input**: Draw area on map + select dates
- **Output**: Professional agricultural risk maps in seconds
- **Features**: Real-time progress, multiple export formats, automated analysis

## 5-Minute Setup on Render

### 1. Get Google Earth Engine Credentials
```bash
# Go to: https://console.cloud.google.com/
# Create new project → Enable Earth Engine API → Create Service Account
# Download JSON key file
```

### 2. Deploy to Render
1. Go to https://render.com
2. Click "New" → "Blueprint" 
3. Connect this GitHub repo
4. Paste your GEE JSON into `GOOGLE_APPLICATION_CREDENTIALS_JSON`
5. Click "Deploy"

### 3. Test Your System
- Visit your frontend URL
- Draw an area on Zimbabwe
- Set dates: 2025-11-01 to 2025-12-15
- Click "Generate Visualization"
- Watch real-time progress
- Download professional map

## API Usage Examples

### Start Analysis
```bash
curl -X POST https://your-api.onrender.com/api/v1/visualization/generate \
  -H "Content-Type: application/json" \
  -d '{
    "region_name": "Zimbabwe",
    "geometry": {"type": "Polygon", "coordinates": [...]},
    "start_date": "2025-11-01", 
    "end_date": "2025-12-15",
    "analysis_type": "anomaly"
  }'
```

### Check Progress  
```bash
curl https://your-api.onrender.com/api/v1/visualization/jobs/{job_id}/status
```

### Export Results
```bash
curl -X POST https://your-api.onrender.com/api/v1/visualization/export \
  -H "Content-Type: application/json" \
  -d '{"job_id": "...", "format": "png", "resolution": 300}'
```

## Integration with Existing Yieldera

### React Component Integration
```jsx
import AutomatedVisualizationModule from './components/VisualizationModule';

function YielderaApp() {
  return (
    <div>
      {/* Your existing components */}
      <AutomatedVisualizationModule apiBaseUrl="/api/v1" />
    </div>
  );
}
```

### API Integration
```javascript
const generateMap = async (region, startDate, endDate) => {
  const response = await fetch('/api/v1/visualization/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ region_name: region, start_date: startDate, end_date: endDate })
  });
  return response.json();
};
```

## Business Impact

### Before (Manual Process):
1. Run GEE script manually ⏱️ 15-30 minutes
2. Export GeoTIFFs ⏱️ 5-10 minutes  
3. Open ArcMap ⏱️ 5 minutes
4. Create visualization ⏱️ 20-45 minutes
5. Export and format ⏱️ 10 minutes
**Total: 55-90 minutes per analysis**

### After (Automated System):
1. Draw area + click generate ⏱️ 30 seconds
2. Wait for processing ⏱️ 2-5 minutes
3. Download professional map ⏱️ 10 seconds
**Total: 3-6 minutes per analysis**

### ROI Calculation:
- **Time Savings**: 85-95% reduction
- **Quality**: Consistent, professional output
- **Scalability**: Handle multiple concurrent requests
- **Client Service**: Real-time delivery vs. next-day turnaround

## Production Considerations

### Performance Tuning:
- Scale workers based on demand
- Use S3 for file storage at scale
- Implement result caching
- Monitor Earth Engine quotas

### Security:
- Rotate GEE service account keys
- Enable HTTPS
- Set up rate limiting
- Monitor access logs

### Maintenance:
- Regular dependency updates
- Database cleanup (automated)
- Log rotation
- Performance monitoring
EOF

print_success "Quick start guide created (QUICK_START.md)"

# Final summary
echo ""
echo "======================================================================"
print_success "🎉 Deployment setup completed successfully!"
echo ""
echo "📁 Files created:"
echo "   └── .env.example (Environment template)"
echo "   └── DEPLOYMENT_CHECKLIST.md (Step-by-step deployment guide)"
echo "   └── QUICK_START.md (5-minute setup guide)"
echo ""
echo "🚀 Next Steps:"
echo "   1. Set up Google Earth Engine service account"
echo "   2. Push code to GitHub repository"
echo "   3. Deploy to Render using render.yaml"
echo "   4. Configure environment variables"
echo "   5. Test your deployment"
echo ""
echo "📖 See DEPLOYMENT_CHECKLIST.md for detailed instructions"
echo "⚡ See QUICK_START.md for rapid deployment"
echo "======================================================================"
