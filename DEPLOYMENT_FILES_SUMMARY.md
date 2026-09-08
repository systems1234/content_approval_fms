# Cloud Run Deployment Files Summary

## Overview
Complete set of files for deploying Flask CRM to Google Cloud Run with full automation, security, and best practices.

---

## Files Created

### 1. **cloudbuild-cloudrun.yaml** ⭐ Main Build Configuration
**Purpose**: Automated CI/CD pipeline for Google Cloud Build

**What it does**:
- Builds Docker image from source code
- Pushes image to Artifact Registry (with commit SHA and latest tags)
- Creates/updates Cloud Run Jobs for migrations and admin user creation
- Executes database migrations automatically
- Deploys to Cloud Run with all configurations
- Runs health checks to verify deployment
- Uses substitution variables for flexibility

**Key Features**:
- Multi-step build process
- Cloud SQL integration
- Secret Manager integration
- Cloud Storage volume mounting
- Automatic rollback on failure
- Comprehensive logging

**Usage**:
```bash
gcloud builds submit \
  --config=cloudbuild-cloudrun.yaml \
  --substitutions=_REGION=us-central1,_REPOSITORY=flask-crm-repo
```

---

### 2. **migrate_db.py** ⭐ Database Migration Script
**Purpose**: Handles database schema migrations in Cloud Run Jobs

**What it does**:
- Creates Flask application context
- Tests database connectivity
- Initializes migrations folder if needed
- Creates initial migration if no migrations exist
- Runs all pending migrations
- Verifies critical tables exist
- Comprehensive error logging

**Key Features**:
- Automatic initialization
- Connection validation
- Schema verification
- Detailed logging with timestamps
- Error handling and rollback
- Idempotent (safe to run multiple times)

**Usage**:
```bash
# As Cloud Run Job (automatic)
gcloud run jobs execute flask-crm-migrate --region=us-central1 --wait

# Local testing
python migrate_db.py
```

---

### 3. **create_admin.py** ⭐ Admin User Creation Script
**Purpose**: Creates admin user with secure credentials in Cloud Run Jobs

**What it does**:
- Creates admin user from environment variables
- Checks for existing users (prevents duplicates)
- Promotes existing users to admin if needed
- Creates default users (optional)
- Verifies user creation
- Lists all database users

**Key Features**:
- Password strength validation
- Duplicate detection
- User role promotion
- Optional default users creation
- Comprehensive verification
- Detailed logging

**Environment Variables**:
- `ADMIN_USERNAME` (default: admin)
- `ADMIN_EMAIL` (default: admin@example.com)
- `ADMIN_PASSWORD` (required, from Secret Manager)
- `CREATE_DEFAULT_USERS` (optional: true/false)

**Usage**:
```bash
# As Cloud Run Job (automatic)
gcloud run jobs execute flask-crm-create-admin --region=us-central1 --wait

# Local testing
export ADMIN_PASSWORD="your-secure-password"
python create_admin.py
```

---

### 4. **CLOUD_RUN_DEPLOYMENT.md** 📚 Complete Deployment Guide
**Purpose**: Step-by-step instructions for manual deployment

**Contents**:
- **Prerequisites**: Required tools and accounts
- **10 Detailed Steps**:
  1. Initial GCP Setup (project config, API enablement)
  2. Artifact Registry creation
  3. Cloud SQL PostgreSQL setup
  4. Secret Manager configuration
  5. Cloud Storage bucket creation
  6. IAM and service accounts
  7. Build and deploy
  8. Database migrations
  9. Admin user creation
  10. Deployment verification
- **Continuous Deployment**: GitHub, Cloud Source Repos, manual triggers
- **Monitoring & Maintenance**: Logs, backups, updates, rollbacks
- **Troubleshooting**: Common issues and solutions
- **Security Best Practices**: Additional security features

**Use Cases**:
- First-time deployment
- Manual deployment workflow
- Understanding deployment architecture
- Troubleshooting reference
- Team onboarding

---

### 5. **QUICK_DEPLOY.sh** 🚀 Automated Deployment Script
**Purpose**: One-command deployment automation

**What it does**:
- Validates configuration
- Enables all required GCP APIs
- Creates Artifact Registry repository
- Creates Cloud SQL PostgreSQL instance
- Creates database and user
- Generates and stores secrets
- Creates Cloud Storage bucket
- Sets up IAM permissions
- Builds and deploys application
- Verifies deployment
- Outputs all credentials

**Key Features**:
- Colored console output
- Progress tracking
- Error handling
- Idempotent operations (safe to re-run)
- Password file generation
- Final verification

**Usage**:
```bash
# Set configuration
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Make executable
chmod +x QUICK_DEPLOY.sh

# Run deployment
./QUICK_DEPLOY.sh
```

**Output Files**:
- `.db_password.txt` - Database root password
- `.db_user_password.txt` - Database user password
- `.admin_password.txt` - Admin login password

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐      ┌────────────────────┐            │
│  │   Cloud Build   │──────▶│ Artifact Registry│            │
│  │   (CI/CD)       │      │  (Docker Images)   │            │
│  └─────────────────┘      └────────────────────┘            │
│           │                         │                        │
│           │                         ▼                        │
│           │               ┌────────────────────┐            │
│           │               │    Cloud Run       │            │
│           │               │  (Web Service)     │◀───Users   │
│           │               └────────────────────┘            │
│           │                    │         │                  │
│           │                    │         │                  │
│           ▼                    ▼         ▼                  │
│  ┌──────────────────┐   ┌──────────┐  ┌────────────┐      │
│  │ Cloud Run Jobs   │   │ Cloud SQL│  │  Secret    │      │
│  │ - Migration      │───▶│(PostgreSQL)│◀─│ Manager    │      │
│  │ - Admin Creation │   └──────────┘  └────────────┘      │
│  └──────────────────┘                                      │
│                              │                              │
│                              ▼                              │
│                    ┌────────────────────┐                  │
│                    │  Cloud Storage     │                  │
│                    │  (File Uploads)    │                  │
│                    └────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Workflows

### Option 1: Automated CI/CD (Recommended)
**Trigger**: Push to main branch
**Process**: Automatic via Cloud Build trigger

```bash
git push origin main
# Cloud Build automatically:
# 1. Builds image
# 2. Runs tests
# 3. Pushes to Artifact Registry
# 4. Runs migrations
# 5. Deploys to Cloud Run
# 6. Creates admin user
# 7. Verifies deployment
```

### Option 2: Manual Deployment with Cloud Build
**Trigger**: Manual command
**Process**: Use cloudbuild-cloudrun.yaml

```bash
gcloud builds submit \
  --config=cloudbuild-cloudrun.yaml \
  --substitutions=_REGION=us-central1
```

### Option 3: Quick Deploy Script
**Trigger**: Manual script execution
**Process**: Automated setup and deployment

```bash
export PROJECT_ID="my-project"
./QUICK_DEPLOY.sh
```

### Option 4: Step-by-Step Manual
**Trigger**: Manual commands
**Process**: Follow CLOUD_RUN_DEPLOYMENT.md guide

```bash
# Follow each step in the guide
# Useful for learning or custom setups
```

---

## Environment Variables & Secrets

### Secrets in Secret Manager
| Secret Name | Description | Used By |
|------------|-------------|---------|
| `flask-crm-secret-key` | Flask session secret | Cloud Run Service, Jobs |
| `flask-crm-database-url` | PostgreSQL connection string | Cloud Run Service, Jobs |
| `flask-crm-admin-password` | Admin user password | Admin Creation Job |

### Environment Variables (Optional)
| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USERNAME` | admin | Admin username |
| `ADMIN_EMAIL` | admin@example.com | Admin email |
| `CREATE_DEFAULT_USERS` | false | Create manager/auditor/user |

---

## Resource Configuration

### Cloud Run Service
```yaml
Resource Limits:
  Memory: 1Gi
  CPU: 2
  Min Instances: 1
  Max Instances: 10
  Timeout: 300s
  Concurrency: 80

Features:
  - 2nd generation execution environment
  - Session affinity enabled
  - CPU throttling enabled
  - Cloud SQL connection via Unix socket
  - Secret Manager integration
  - Cloud Storage volume mount
```

### Cloud SQL
```yaml
Instance:
  Version: PostgreSQL 15
  Tier: db-f1-micro (upgradable)
  Storage: 10GB SSD (auto-increase)
  Backups: Daily at 3:00 AM
  Retention: 7 days
  Connection: Private via Cloud Run
```

### Artifact Registry
```yaml
Repository:
  Format: Docker
  Location: Regional
  Features:
    - Immutable tags
    - Vulnerability scanning
    - Access control via IAM
```

---

## Security Features

### Implemented Security
✅ Secret Manager for credentials
✅ IAM service accounts with least privilege
✅ Private Cloud SQL connections
✅ HTTPS by default (Cloud Run)
✅ Non-root Docker user
✅ Immutable container tags
✅ Automated security updates
✅ Cloud Storage private access
✅ Audit logging enabled

### Additional Security (Optional)
- VPC Connector for private networking
- Binary Authorization for image verification
- Cloud Armor for DDoS protection
- Cloud CDN with signed URLs
- Identity-Aware Proxy (IAP)

---

## Cost Estimation

### Monthly Costs (Approximate)
| Service | Configuration | Est. Cost |
|---------|--------------|-----------|
| Cloud Run | 1-10 instances, 1Gi RAM | $5-50 |
| Cloud SQL | db-f1-micro | $7-15 |
| Cloud Storage | 10GB | $0.20 |
| Artifact Registry | 5GB | $0.10 |
| Secret Manager | 3 secrets | $0.06 |
| **Total** | | **~$12-65/month** |

**Notes**:
- Costs scale with usage
- Free tier available for new GCP accounts
- Use db-f1-micro for development
- Upgrade to db-g1-small for production

---

## Monitoring & Logging

### Cloud Run Logs
```bash
# Stream logs
gcloud run services logs tail flask-crm-service --region=us-central1

# View recent logs
gcloud run services logs read flask-crm-service --region=us-central1 --limit=100

# Filter errors
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=50
```

### Metrics
- Request count
- Request latency (p50, p95, p99)
- Error rate
- Instance count
- Memory usage
- CPU utilization

### Alerts (Set up in Cloud Console)
- Service downtime
- High error rate
- Database connection failures
- High latency

---

## Maintenance Tasks

### Weekly
- Review Cloud Run logs for errors
- Check database backup status
- Monitor costs

### Monthly
- Update dependencies
- Review security advisories
- Rotate secrets
- Database performance tuning

### Quarterly
- Scale resource review
- Cost optimization
- Security audit
- Backup restore test

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Build fails | Check `gcloud builds log <BUILD_ID>` |
| Service crashes | Check `gcloud run services logs read` |
| DB connection fails | Verify Cloud SQL instance running |
| Secrets not accessible | Check IAM permissions |
| Migration fails | View job logs, re-run migration |
| 500 errors | Check application logs |
| Slow performance | Increase memory/CPU, check DB |

---

## Next Steps After Deployment

1. **Access Application**
   ```bash
   # Get URL
   gcloud run services describe flask-crm-service --region=us-central1 --format='value(status.url)'
   ```

2. **Login as Admin**
   - Username: admin
   - Password: (from `.admin_password.txt` or Secret Manager)

3. **Create Additional Users**
   - Use the admin panel
   - Or run create_admin.py with CREATE_DEFAULT_USERS=true

4. **Set Up Monitoring**
   - Cloud Monitoring dashboards
   - Uptime checks
   - Alert policies

5. **Configure Domain (Optional)**
   ```bash
   gcloud run services update flask-crm-service \
     --region=us-central1 \
     --domain=crm.yourdomain.com
   ```

6. **Enable Continuous Deployment**
   - Connect GitHub repository
   - Create Cloud Build trigger
   - Test automated deployments

---

## Support & Resources

### Documentation
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Cloud SQL Docs](https://cloud.google.com/sql/docs)
- [Secret Manager Docs](https://cloud.google.com/secret-manager/docs)

### Getting Help
1. Check CLOUD_RUN_DEPLOYMENT.md troubleshooting section
2. Review Cloud Run logs
3. Check GCP Status Dashboard
4. Create GitHub issue

### Useful Commands
```bash
# Service status
gcloud run services describe flask-crm-service --region=us-central1

# Database status
gcloud sql instances describe flask-crm-db

# List all resources
gcloud run services list
gcloud sql instances list
gcloud secrets list
gsutil ls
```

---

## File Checklist

Before deploying, ensure you have:

- [ ] `cloudbuild-cloudrun.yaml` - Build configuration
- [ ] `Dockerfile` - Container definition
- [ ] `.dockerignore` - Build exclusions
- [ ] `migrate_db.py` - Migration script
- [ ] `create_admin.py` - Admin creation script
- [ ] `requirements.txt` - Python dependencies
- [ ] `CLOUD_RUN_DEPLOYMENT.md` - Documentation
- [ ] `QUICK_DEPLOY.sh` - Automation script
- [ ] Application code in `app/` directory
- [ ] Database models in `app/models.py`
- [ ] Configuration in `config.py`

---

**Last Updated**: 2025
**Version**: 1.0
**Deployment Type**: Google Cloud Run (Fully Managed)
