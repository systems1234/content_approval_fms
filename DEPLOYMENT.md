# Deployment Guide - TaskFlow CRM

Complete deployment instructions for both local development and Google Cloud Platform.

## Table of Contents
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Google Cloud Platform Deployment](#google-cloud-platform-deployment)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Python 3.9 or higher
- Node.js 16 or higher
- Git

### Step-by-Step Setup

#### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd content_approval_fms
```

#### 2. Create Virtual Environment
**Windows:**
```bash
python -m venv crm_env
.\crm_env\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv crm_env
source crm_env/bin/activate
```

#### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Install Node Dependencies & Build Tailwind CSS
```bash
npm install
npm run build:css
```

#### 5. Set Up Environment Variables
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=sqlite:///crm.db
FLASK_APP=run.py
FLASK_ENV=development
```

#### 6. Initialize Database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

#### 7. Seed Demo Data (Optional)
```bash
python seed_data.py
```

This creates demo users:
- **Admin**: `admin` / `admin123`
- **Manager**: `manager` / `manager123`
- **Auditor**: `auditor` / `auditor123`
- **Assignee**: `user` / `user123`

#### 8. Run Development Server
```bash
flask run
```

Visit: http://localhost:5000

---

## Docker Deployment

### Using Docker Compose (Recommended for Development)

#### 1. Build and Start Services
```bash
docker-compose up --build
```

This starts:
- Flask application on port 5000
- PostgreSQL database on port 5432

#### 2. Access Application
Visit: http://localhost:5000

#### 3. Stop Services
```bash
docker-compose down
```

#### 4. Reset Database (if needed)
```bash
docker-compose down -v
docker-compose up --build
```

### Using Docker Standalone

#### 1. Build Image
```bash
docker build -t flask-crm:latest .
```

#### 2. Run Container
```bash
docker run -d \
  -p 5000:8080 \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=sqlite:///crm.db \
  --name flask-crm \
  flask-crm:latest
```

---

## Google Cloud Platform Deployment

### Prerequisites
- Google Cloud Account
- gcloud CLI installed and configured
- Billing enabled on your GCP project

### Step 1: Set Up GCP Project

```bash
# Set project ID
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

### Step 2: Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create crm-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=STRONG_PASSWORD_HERE

# Create database
gcloud sql databases create crm_db --instance=crm-db

# Create user
gcloud sql users create crm_user \
  --instance=crm-db \
  --password=STRONG_PASSWORD_HERE
```

### Step 3: Store Secrets in Secret Manager

```bash
# Create secret for SECRET_KEY
echo -n "your-super-secret-key-change-this" | \
  gcloud secrets create flask-crm-secret --data-file=-

# Grant Cloud Run access to secret
gcloud secrets add-iam-policy-binding flask-crm-secret \
  --member=serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### Step 4: Build and Deploy

#### Option A: Using Cloud Build (Automated CI/CD)

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_CLOUDSQL_INSTANCE=crm-db,_DATABASE_URL="postgresql://crm_user:PASSWORD@/crm_db?host=/cloudsql/$PROJECT_ID:us-central1:crm-db"
```

#### Option B: Manual Deployment

```bash
# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/flask-crm

# Deploy to Cloud Run
gcloud run deploy flask-crm-service \
  --image gcr.io/$PROJECT_ID/flask-crm \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances $PROJECT_ID:us-central1:crm-db \
  --set-env-vars DATABASE_URL="postgresql://crm_user:PASSWORD@/crm_db?host=/cloudsql/$PROJECT_ID:us-central1:crm-db" \
  --set-secrets=SECRET_KEY=flask-crm-secret:latest \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 1 \
  --port 8080
```

### Step 5: Run Database Migrations

```bash
# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe flask-crm-service \
  --region us-central1 \
  --format 'value(status.url)')

# Run migrations using Cloud Run Jobs (recommended)
gcloud run jobs create migrate-job \
  --image gcr.io/$PROJECT_ID/flask-crm \
  --region us-central1 \
  --add-cloudsql-instances $PROJECT_ID:us-central1:crm-db \
  --set-env-vars DATABASE_URL="postgresql://crm_user:PASSWORD@/crm_db?host=/cloudsql/$PROJECT_ID:us-central1:crm-db" \
  --set-secrets=SECRET_KEY=flask-crm-secret:latest \
  --command "flask" \
  --args "db,upgrade"

# Execute migration job
gcloud run jobs execute migrate-job --region us-central1 --wait
```

### Step 6: Create Admin User

```bash
# Connect to Cloud SQL
gcloud sql connect crm-db --user=crm_user

# In PostgreSQL shell, or use Cloud Run job to execute seed_data.py
# Or manually via Flask shell in a Cloud Run job
```

### Step 7: Set Up Continuous Deployment (Optional)

#### Connect Cloud Build to GitHub/GitLab

```bash
# Create Cloud Build trigger
gcloud builds triggers create github \
  --repo-name=your-repo \
  --repo-owner=your-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `your-secret-key-here` |
| `DATABASE_URL` | Database connection string | `sqlite:///crm.db` or `postgresql://...` |
| `FLASK_APP` | Entry point for Flask | `run.py` |
| `FLASK_ENV` | Environment mode | `development` or `production` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `5000` |
| `TASKS_PER_PAGE` | Pagination limit | `10` |

---

## Troubleshooting

### Common Issues

#### 1. Tailwind CSS Not Building
```bash
# Ensure Node modules are installed
npm install

# Build CSS manually
npm run build:css

# Watch for changes during development
npm run watch:css
```

#### 2. Database Migration Errors
```bash
# Reset migrations
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

#### 3. Cloud SQL Connection Issues
```bash
# Verify instance is running
gcloud sql instances describe crm-db

# Check Cloud SQL proxy connection
cloud_sql_proxy -instances=$PROJECT_ID:us-central1:crm-db=tcp:5432
```

#### 4. Static Files Not Loading in Production
Ensure Tailwind CSS is built before Docker image creation. The Dockerfile handles this automatically.

#### 5. Permission Denied Errors
```bash
# Ensure proper permissions
chmod +x seed_data.py
chmod +x run.py
```

### Logs and Monitoring

#### Local Development
```bash
flask run --debug
```

#### Docker
```bash
docker-compose logs -f web
```

#### Google Cloud Run
```bash
# View logs
gcloud run services logs read flask-crm-service --region us-central1 --limit 50

# Stream logs
gcloud run services logs tail flask-crm-service --region us-central1
```

---

## Performance Optimization

### For Production Deployment

1. **Use PostgreSQL instead of SQLite**
   ```env
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```

2. **Enable connection pooling**
   - Configure in Cloud SQL settings
   - Use pgBouncer for high-traffic scenarios

3. **Scale Cloud Run instances**
   ```bash
   gcloud run services update flask-crm-service \
     --min-instances=2 \
     --max-instances=20 \
     --region us-central1
   ```

4. **Add CDN for static files**
   - Use Cloud CDN or similar service
   - Configure proper caching headers

5. **Monitor with Cloud Monitoring**
   ```bash
   # Enable monitoring
   gcloud monitoring dashboards create --config-from-file=dashboard.yaml
   ```

---

## Security Best Practices

1. **Always use strong SECRET_KEY in production**
2. **Use Secret Manager for sensitive data**
3. **Enable HTTPS (automatic with Cloud Run)**
4. **Regular security updates**
   ```bash
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```
5. **Implement rate limiting** (future enhancement)
6. **Regular database backups**
   ```bash
   gcloud sql backups create --instance=crm-db
   ```

---

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

---

## Support

For issues and questions:
1. Check this deployment guide
2. Review application logs
3. Check GitHub issues
4. Create a new issue with detailed information

---

**Last Updated**: 2024
**Version**: 1.0
