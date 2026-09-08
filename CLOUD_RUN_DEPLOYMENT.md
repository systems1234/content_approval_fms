# Complete Cloud Run Deployment Guide - Flask CRM

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Initial GCP Setup](#step-1-initial-gcp-setup)
- [Step 2: Create Artifact Registry](#step-2-create-artifact-registry)
- [Step 3: Setup Cloud SQL PostgreSQL](#step-3-setup-cloud-sql-postgresql)
- [Step 4: Configure Secret Manager](#step-4-configure-secret-manager)
- [Step 5: Create Cloud Storage](#step-5-create-cloud-storage)
- [Step 6: Setup Service Accounts & IAM](#step-6-setup-service-accounts--iam)
- [Step 7: Build & Deploy](#step-7-build--deploy)
- [Step 8: Run Database Migrations](#step-8-run-database-migrations)
- [Step 9: Create Admin User](#step-9-create-admin-user)
- [Step 10: Verify Deployment](#step-10-verify-deployment)
- [Continuous Deployment](#continuous-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides a complete, step-by-step workflow to deploy the Flask CRM application to Google Cloud Run using:

- **Google Cloud Build** - CI/CD pipeline for building Docker images
- **Artifact Registry** - Secure Docker image storage
- **Cloud SQL (PostgreSQL)** - Managed database service
- **Secret Manager** - Secure credential storage
- **Cloud Run** - Fully managed serverless container platform
- **Cloud Run Jobs** - Database migrations and admin user creation
- **Cloud Storage** - File uploads storage

---

## Prerequisites

### 1. Google Cloud Account
- Active GCP account with billing enabled
- Project owner or editor permissions

### 2. Local Environment
```bash
# Install gcloud CLI (if not installed)
# macOS
brew install --cask google-cloud-sdk

# Windows
# Download from: https://cloud.google.com/sdk/docs/install

# Linux
curl https://sdk.cloud.google.com | bash

# Verify installation
gcloud --version
```

### 3. Authentication
```bash
# Login to GCP
gcloud auth login

# Set application default credentials
gcloud auth application-default login
```

---

## Step 1: Initial GCP Setup

### 1.1 Set Environment Variables
```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="flask-crm-service"

# Set project
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION

# Verify configuration
gcloud config list
```

### 1.2 Enable Required APIs
```bash
# Enable all required Google Cloud APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

### 1.3 Set Resource Configuration
```bash
# Application configuration
export REPOSITORY="flask-crm-repo"
export IMAGE_NAME="flask-crm"
export DB_INSTANCE="flask-crm-db"
export DB_NAME="crm_db"
export DB_USER="crm_user"
export UPLOAD_BUCKET="${PROJECT_ID}-flask-crm-uploads"
```

---

## Step 2: Create Artifact Registry

### 2.1 Create Docker Repository
```bash
# Create Artifact Registry repository
gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=$REGION \
  --description="Flask CRM Docker images" \
  --immutable-tags \
  --async

# Wait for creation to complete
gcloud artifacts repositories describe $REPOSITORY \
  --location=$REGION

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### 2.2 Verify Repository
```bash
# List repositories
gcloud artifacts repositories list --location=$REGION

# Get repository details
gcloud artifacts repositories describe $REPOSITORY \
  --location=$REGION \
  --format="table(name,format,createTime)"
```

---

## Step 3: Setup Cloud SQL PostgreSQL

### 3.1 Create PostgreSQL Instance
```bash
# Generate strong database password
export DB_PASSWORD=$(openssl rand -base64 32)
echo "Database Password: $DB_PASSWORD"
# IMPORTANT: Save this password securely!

# Create Cloud SQL PostgreSQL instance
gcloud sql instances create $DB_INSTANCE \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password="$DB_PASSWORD" \
  --database-flags=max_connections=100 \
  --storage-type=SSD \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --retained-backups-count=7 \
  --retained-transaction-log-days=7 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=4 \
  --assign-ip \
  --no-deletion-protection

# Wait for instance creation (takes 5-10 minutes)
gcloud sql operations list \
  --instance=$DB_INSTANCE \
  --filter="status:RUNNING" \
  --format="table(name,operationType,status)"
```

### 3.2 Create Database and User
```bash
# Create database
gcloud sql databases create $DB_NAME \
  --instance=$DB_INSTANCE

# Generate user password
export DB_USER_PASSWORD=$(openssl rand -base64 32)
echo "DB User Password: $DB_USER_PASSWORD"
# IMPORTANT: Save this password securely!

# Create database user
gcloud sql users create $DB_USER \
  --instance=$DB_INSTANCE \
  --password="$DB_USER_PASSWORD"

# List databases
gcloud sql databases list --instance=$DB_INSTANCE

# List users
gcloud sql users list --instance=$DB_INSTANCE
```

### 3.3 Get Connection Information
```bash
# Get connection name
export CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE \
  --format='value(connectionName)')

echo "Connection Name: $CONNECTION_NAME"

# Construct DATABASE_URL for Cloud Run
export DATABASE_URL="postgresql://${DB_USER}:${DB_USER_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

echo "DATABASE_URL: $DATABASE_URL"
```

### 3.4 Test Connection (Optional)
```bash
# Install Cloud SQL Proxy for local testing
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Start proxy in background
./cloud_sql_proxy -instances=${CONNECTION_NAME}=tcp:5432 &

# Test connection with psql
psql "postgresql://${DB_USER}:${DB_USER_PASSWORD}@localhost:5432/${DB_NAME}"

# Stop proxy when done
pkill cloud_sql_proxy
```

---

## Step 4: Configure Secret Manager

### 4.1 Create Secrets
```bash
# Generate Flask secret key
export SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
echo "Flask Secret Key: $SECRET_KEY"
# IMPORTANT: Save this securely!

# Create SECRET_KEY secret
echo -n "$SECRET_KEY" | gcloud secrets create flask-crm-secret-key \
  --data-file=- \
  --replication-policy="automatic" \
  --labels="app=flask-crm,env=production"

# Create DATABASE_URL secret
echo -n "$DATABASE_URL" | gcloud secrets create flask-crm-database-url \
  --data-file=- \
  --replication-policy="automatic" \
  --labels="app=flask-crm,env=production"

# Generate admin password
export ADMIN_PASSWORD=$(openssl rand -base64 32)
echo "Admin Password: $ADMIN_PASSWORD"
# IMPORTANT: Save this password - you'll use it to login!

# Create ADMIN_PASSWORD secret
echo -n "$ADMIN_PASSWORD" | gcloud secrets create flask-crm-admin-password \
  --data-file=- \
  --replication-policy="automatic" \
  --labels="app=flask-crm,env=production,type=admin"
```

### 4.2 Verify Secrets
```bash
# List all secrets
gcloud secrets list --filter="labels.app=flask-crm"

# Verify secret exists (without showing value)
gcloud secrets describe flask-crm-secret-key
gcloud secrets describe flask-crm-database-url
gcloud secrets describe flask-crm-admin-password
```

### 4.3 Add Additional Secrets (Optional)
```bash
# Create manager, auditor, user passwords for default users
echo -n "manager123" | gcloud secrets create flask-crm-manager-password --data-file=-
echo -n "auditor123" | gcloud secrets create flask-crm-auditor-password --data-file=-
echo -n "user123" | gcloud secrets create flask-crm-user-password --data-file=-
```

---

## Step 5: Create Cloud Storage

### 5.1 Create Upload Bucket
```bash
# Create bucket for file uploads
gsutil mb -p $PROJECT_ID \
  -c STANDARD \
  -l $REGION \
  -b on \
  gs://$UPLOAD_BUCKET/

# Set bucket lifecycle (delete files older than 90 days - optional)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://$UPLOAD_BUCKET/
rm lifecycle.json

# Enable versioning (optional)
gsutil versioning set on gs://$UPLOAD_BUCKET/
```

### 5.2 Configure Bucket Permissions
```bash
# Make bucket private (default)
gsutil iam ch allUsers:objectViewer gs://$UPLOAD_BUCKET/

# We'll grant Cloud Run service account access later
```

---

## Step 6: Setup Service Accounts & IAM

### 6.1 Create Service Account for Cloud Run
```bash
# Create service account
gcloud iam service-accounts create flask-crm-sa \
  --display-name="Flask CRM Service Account" \
  --description="Service account for Flask CRM Cloud Run service"

# Get service account email
export SERVICE_ACCOUNT="flask-crm-sa@${PROJECT_ID}.iam.gserviceaccount.com"
echo "Service Account: $SERVICE_ACCOUNT"
```

### 6.2 Grant IAM Permissions
```bash
# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudsql.client"

# Grant Secret Manager Secret Accessor role
gcloud secrets add-iam-policy-binding flask-crm-secret-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding flask-crm-database-url \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding flask-crm-admin-password \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

# Grant Storage Object Admin for uploads bucket
gsutil iam ch \
  "serviceAccount:${SERVICE_ACCOUNT}:objectAdmin" \
  gs://$UPLOAD_BUCKET/

# Grant Cloud Run Invoker (for health checks)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.invoker"

# Grant Logging Write
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/logging.logWriter"
```

### 6.3 Grant Cloud Build Permissions
```bash
# Get Cloud Build service account
export CLOUD_BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

# Grant Cloud Run Admin (to deploy)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/run.admin"

# Grant Service Account User (to act as service account)
gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/iam.serviceAccountUser"

# Grant Cloud SQL Admin (for migrations)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/cloudsql.admin"

# Grant Secret Accessor (for build process)
gcloud secrets add-iam-policy-binding flask-crm-secret-key \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding flask-crm-database-url \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding flask-crm-admin-password \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 7: Build & Deploy

### 7.1 Prepare Local Repository
```bash
# Navigate to project directory
cd /path/to/content_approval_fms

# Ensure you have latest code
git status
git pull origin main
```

### 7.2 Build Image Using Cloud Build
```bash
# Submit build to Cloud Build
gcloud builds submit \
  --config=cloudbuild-cloudrun.yaml \
  --substitutions=_REGION=$REGION,_REPOSITORY=$REPOSITORY,_SERVICE_NAME=$SERVICE_NAME,_CLOUDSQL_INSTANCE=$DB_INSTANCE,_SERVICE_ACCOUNT=$SERVICE_ACCOUNT,_UPLOAD_BUCKET=$UPLOAD_BUCKET \
  --timeout=30m

# Monitor build progress
gcloud builds list --limit=5

# Get build logs (if build ID is abc123)
gcloud builds log <BUILD_ID> --stream
```

### 7.3 Manual Build (Alternative)
If you prefer to build and deploy manually:

```bash
# Build image locally
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest .

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=$SERVICE_ACCOUNT \
  --set-cloudsql-instances=$CONNECTION_NAME \
  --set-secrets=SECRET_KEY=flask-crm-secret-key:latest,DATABASE_URL=flask-crm-database-url:latest \
  --memory=1Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=10 \
  --port=8080 \
  --timeout=300s \
  --concurrency=80 \
  --execution-environment=gen2 \
  --session-affinity \
  --add-volume=name=uploads,type=cloud-storage,bucket=$UPLOAD_BUCKET \
  --add-volume-mount=volume=uploads,mount-path=/app/uploads
```

### 7.4 Verify Deployment
```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test endpoint
curl -I $SERVICE_URL
```

---

## Step 8: Run Database Migrations

### 8.1 Create Migration Job
```bash
# Create Cloud Run Job for migrations
gcloud run jobs create flask-crm-migrate \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest \
  --region=$REGION \
  --set-cloudsql-instances=$CONNECTION_NAME \
  --set-secrets=SECRET_KEY=flask-crm-secret-key:latest,DATABASE_URL=flask-crm-database-url:latest \
  --service-account=$SERVICE_ACCOUNT \
  --max-retries=3 \
  --task-timeout=600s \
  --cpu=1 \
  --memory=512Mi \
  --command=python \
  --args="migrate_db.py"
```

### 8.2 Execute Migration
```bash
# Run migration job
gcloud run jobs execute flask-crm-migrate \
  --region=$REGION \
  --wait

# View migration logs
gcloud run jobs executions describe \
  $(gcloud run jobs executions list \
    --job=flask-crm-migrate \
    --region=$REGION \
    --limit=1 \
    --format='value(name)') \
  --region=$REGION

# Get detailed logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=flask-crm-migrate" \
  --limit=50 \
  --format=json
```

### 8.3 Verify Migration
```bash
# Connect to Cloud SQL and check tables
gcloud sql connect $DB_INSTANCE --user=$DB_USER

# In PostgreSQL shell:
# \c crm_db
# \dt
# SELECT COUNT(*) FROM users;
# \q
```

---

## Step 9: Create Admin User

### 9.1 Create Admin User Job
```bash
# Create Cloud Run Job for admin user creation
gcloud run jobs create flask-crm-create-admin \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest \
  --region=$REGION \
  --set-cloudsql-instances=$CONNECTION_NAME \
  --set-secrets=SECRET_KEY=flask-crm-secret-key:latest,DATABASE_URL=flask-crm-database-url:latest,ADMIN_PASSWORD=flask-crm-admin-password:latest \
  --service-account=$SERVICE_ACCOUNT \
  --max-retries=1 \
  --task-timeout=300s \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="ADMIN_USERNAME=admin,ADMIN_EMAIL=admin@example.com" \
  --command=python \
  --args="create_admin.py"
```

### 9.2 Execute Admin Creation
```bash
# Run admin user creation job
gcloud run jobs execute flask-crm-create-admin \
  --region=$REGION \
  --wait

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=flask-crm-create-admin" \
  --limit=50 \
  --format="table(timestamp,jsonPayload.message)"
```

### 9.3 Get Admin Credentials
```bash
# Retrieve admin password from Secret Manager
gcloud secrets versions access latest --secret="flask-crm-admin-password"

echo "Admin Login Credentials:"
echo "  URL: $SERVICE_URL"
echo "  Username: admin"
echo "  Password: [Retrieved from Secret Manager above]"
```

---

## Step 10: Verify Deployment

### 10.1 Health Check
```bash
# Test health endpoint
curl -I $SERVICE_URL/

# Check service status
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="table(status.conditions[].type,status.conditions[].status)"
```

### 10.2 Login Test
```bash
# Open in browser
echo "Open this URL in your browser: $SERVICE_URL"

# Or use curl to test login
curl -X POST $SERVICE_URL/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=$ADMIN_PASSWORD" \
  -c cookies.txt \
  -L

# Test authenticated endpoint
curl -b cookies.txt $SERVICE_URL/dashboard
rm cookies.txt
```

### 10.3 View Logs
```bash
# Stream Cloud Run logs
gcloud run services logs tail $SERVICE_NAME \
  --region=$REGION

# Read recent logs
gcloud run services logs read $SERVICE_NAME \
  --region=$REGION \
  --limit=100
```

### 10.4 Monitor Performance
```bash
# Get service metrics
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="table(status.traffic[].revisionName,status.traffic[].percent,status.traffic[].latestRevision)"

# View Cloud Run dashboard
echo "Cloud Run Console: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}"
```

---

## Continuous Deployment

### Option A: GitHub Integration

#### 1. Connect GitHub Repository
```bash
# Install Cloud Build GitHub app
# Visit: https://github.com/apps/google-cloud-build

# Create build trigger
gcloud builds triggers create github \
  --repo-name="your-repo-name" \
  --repo-owner="your-github-username" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild-cloudrun.yaml" \
  --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME},_CLOUDSQL_INSTANCE=${DB_INSTANCE},_SERVICE_ACCOUNT=${SERVICE_ACCOUNT},_UPLOAD_BUCKET=${UPLOAD_BUCKET}" \
  --description="Deploy Flask CRM on push to main"
```

#### 2. Test Trigger
```bash
# Manual trigger run
gcloud builds triggers run flask-crm-deploy \
  --branch=main

# List triggers
gcloud builds triggers list
```

### Option B: Cloud Source Repositories

```bash
# Create repository
gcloud source repos create flask-crm

# Add remote
git remote add google https://source.developers.google.com/p/${PROJECT_ID}/r/flask-crm

# Push code
git push google main

# Create trigger
gcloud builds triggers create cloud-source-repositories \
  --repo="flask-crm" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild-cloudrun.yaml"
```

### Option C: Manual Deployment Script

Create a deployment script `deploy.sh`:

```bash
#!/bin/bash
set -e

echo "Deploying Flask CRM to Cloud Run..."

# Submit build
gcloud builds submit \
  --config=cloudbuild-cloudrun.yaml \
  --substitutions=_REGION=$REGION,_REPOSITORY=$REPOSITORY,_SERVICE_NAME=$SERVICE_NAME,_CLOUDSQL_INSTANCE=$DB_INSTANCE,_SERVICE_ACCOUNT=$SERVICE_ACCOUNT,_UPLOAD_BUCKET=$UPLOAD_BUCKET

echo "Deployment complete!"
echo "Service URL: $(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')"
```

Make executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Monitoring & Maintenance

### Monitoring Setup

```bash
# Create uptime check
gcloud monitoring uptime create \
  flask-crm-uptime-check \
  --display-name="Flask CRM Uptime" \
  --resource-type=url \
  --http-check-url="${SERVICE_URL}/" \
  --check-interval=60s

# Create alerting policy (requires monitoring workspace)
# Visit: https://console.cloud.google.com/monitoring/alerting
```

### View Logs

```bash
# Application logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
  --limit=50 \
  --format=json

# Error logs only
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND severity>=ERROR" \
  --limit=20
```

### Database Backups

```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=$DB_INSTANCE \
  --description="Manual backup before update"

# List backups
gcloud sql backups list --instance=$DB_INSTANCE

# Restore from backup (if needed)
gcloud sql backups restore <BACKUP_ID> \
  --backup-instance=$DB_INSTANCE \
  --backup-id=<BACKUP_ID>
```

### Update Service

```bash
# Update service with new image
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest

# Update environment variables
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --set-env-vars="NEW_VAR=value"

# Update resource limits
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=20
```

### Rollback

```bash
# List revisions
gcloud run revisions list \
  --service=$SERVICE_NAME \
  --region=$REGION

# Rollback to previous revision
gcloud run services update-traffic $SERVICE_NAME \
  --region=$REGION \
  --to-revisions=<PREVIOUS_REVISION>=100
```

---

## Troubleshooting

### Common Issues

#### 1. Build Fails

**Problem**: Cloud Build timeout or image build error

**Solution**:
```bash
# Increase timeout
gcloud builds submit --timeout=45m ...

# Check build logs
gcloud builds log <BUILD_ID>

# Manual local build test
docker build -t test .
```

#### 2. Database Connection Fails

**Problem**: Cloud Run cannot connect to Cloud SQL

**Solutions**:
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe $DB_INSTANCE

# Check connection name
gcloud sql instances describe $DB_INSTANCE --format='value(connectionName)'

# Verify service account has cloudsql.client role
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:${SERVICE_ACCOUNT}"

# Test connection from Cloud Shell
gcloud sql connect $DB_INSTANCE --user=$DB_USER
```

#### 3. Secrets Not Accessible

**Problem**: Secret Manager secrets cannot be read

**Solutions**:
```bash
# Verify secret exists
gcloud secrets list

# Check IAM permissions
gcloud secrets get-iam-policy flask-crm-secret-key

# Grant access
gcloud secrets add-iam-policy-binding flask-crm-secret-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

#### 4. Service Crashes or Restarts

**Problem**: Cloud Run service keeps restarting

**Solutions**:
```bash
# Check logs for errors
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=100

# Check service status
gcloud run services describe $SERVICE_NAME --region=$REGION

# Increase memory
gcloud run services update $SERVICE_NAME --region=$REGION --memory=2Gi

# Check health endpoint
curl -I $SERVICE_URL/
```

#### 5. Migration Job Fails

**Problem**: Database migration job execution fails

**Solutions**:
```bash
# View job execution logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=flask-crm-migrate" --limit=100

# Re-run migration
gcloud run jobs execute flask-crm-migrate --region=$REGION --wait

# Manual migration using Cloud SQL Proxy
./cloud_sql_proxy -instances=${CONNECTION_NAME}=tcp:5432 &
python migrate_db.py
```

#### 6. File Uploads Not Working

**Problem**: Uploaded files are not saved or accessible

**Solutions**:
```bash
# Check bucket permissions
gsutil iam get gs://$UPLOAD_BUCKET/

# Verify volume mount
gcloud run services describe $SERVICE_NAME --region=$REGION --format="yaml(spec.template.spec.volumes)"

# Test bucket access
gsutil ls gs://$UPLOAD_BUCKET/
```

### Debug Commands

```bash
# Execute command in Cloud Run job
gcloud run jobs execute flask-crm-migrate \
  --region=$REGION \
  --command=/bin/bash \
  --args="-c,python --version && ls -la" \
  --wait

# Get service configuration
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format=yaml > service-config.yaml

# Test locally with production config
docker run -it \
  -e SECRET_KEY=$SECRET_KEY \
  -e DATABASE_URL="sqlite:///test.db" \
  -p 8080:8080 \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest
```

---

## Cost Optimization

### Reduce Costs

```bash
# Use smaller Cloud SQL tier
gcloud sql instances patch $DB_INSTANCE \
  --tier=db-f1-micro

# Reduce minimum instances to 0 (adds cold start delay)
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --min-instances=0

# Set up budget alerts
gcloud billing budgets create \
  --billing-account=<BILLING_ACCOUNT_ID> \
  --display-name="Flask CRM Budget" \
  --budget-amount=100USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90
```

### Monitor Costs

```bash
# View Cloud Run pricing
echo "https://cloud.google.com/run/pricing"

# Export billing data
gcloud billing accounts list
```

---

## Security Best Practices

### Enable Additional Security Features

```bash
# Require authentication (remove --allow-unauthenticated)
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --no-allow-unauthenticated

# Enable VPC Connector (for private access)
gcloud compute networks vpc-access connectors create flask-crm-connector \
  --region=$REGION \
  --network=default \
  --range=10.8.0.0/28

gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --vpc-connector=flask-crm-connector \
  --vpc-egress=private-ranges-only

# Enable Binary Authorization
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --binary-authorization=default

# Set up Cloud Armor (DDoS protection)
# Requires Load Balancer - see Cloud Run documentation
```

### Rotate Secrets

```bash
# Create new version of secret
echo -n "new-secret-value" | gcloud secrets versions add flask-crm-secret-key --data-file=-

# Cloud Run will automatically use latest version
# Or pin to specific version:
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --set-secrets=SECRET_KEY=flask-crm-secret-key:2
```

---

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)

---

## Support

For issues:
1. Check logs with `gcloud run services logs read`
2. Review [Troubleshooting](#troubleshooting) section
3. Consult GCP documentation
4. File issues on GitHub repository

---

**Last Updated**: 2025
**Version**: 2.0
**Cloud Run Generation**: 2nd generation
