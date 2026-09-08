# Gempundit CRM

A Flask-based CRM system implementing a full task assignment and audit workflow using Tailwind CSS and ready for Google Cloud deployment.

## Features

- **User Login** (Flask-Login) with pre-created users (no self-signup)
- **Task Workflow**: Assigned → In Progress → Completed → Under Audit → Passed/Failed → Cancelled
- **Automatic Auditor Assignment** on completion
- **Audit Trail**: Detailed logs of every status change with timestamps and user notes
- **Revision Tracking**: Count of audit failures and new plan dates
- **Role-Based Access**: Assignee, Auditor, Manager, Admin dashboards
- **Notifications** (email or in-app) for assignment and audit events
- **Responsive UI**: Tailwind CSS for rapid styling
- **Database**: Flask-SQLAlchemy with migrations (SQLite locally, Cloud SQL in production)
- **Deployment**: Dockerized, deployable to Google Cloud Run with Cloud SQL and Secret Manager

## Project Structure

```
flask_crm/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── forms.py
│   ├── templates/
│   └── static/
├── migrations/
├── Dockerfile
├── requirements.txt
├── tailwind.config.js
├── postcss.config.js
├── package.json
└── README.md
```

## Local Development

1. **Clone repo and create venv**
   ```bash
   git clone <repo-url>
   cd flask_crm
   python -m venv crm_env
   source crm_env/bin/activate    # Linux/Mac
   .\crm_env\Scripts\Activate.ps1  # Windows PowerShell
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node & build Tailwind CSS**
   ```bash
   npm install
   npm run build:css
   ```

4. **Initialize database & migrations**
   ```bash
   flask db init
   flask db migrate -m "Initial schema"
   flask db upgrade
   ```

5. **Create admin user**
   ```bash
   flask shell
   >>> from app import db
   >>> from app.models import User
   >>> u = User(email='admin@crm.com', username='admin', role='admin')
   >>> u.set_password('AdminPass123')
   >>> db.session.add(u); db.session.commit()
   ```

6. **Run development server**
   ```bash
   flask run
   ```

## Configuration

- **Environment Variables**
   - `SECRET_KEY` (pin in `.env` or export in shell)
   - `BIGQUERY_PROJECT` (default: `mis-gempundit`)
   - `BIGQUERY_DATASET` (default: `Content_FMS`)
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (service-account JSON stored as a secret)
   - `GCS_BUCKET` (reserved for durable upload integration)

- **Tailwind**: Modify `tailwind.config.js` for additional paths

### BigQuery Users Table

Create the authentication table once in BigQuery using [bigquery_users.sql](bigquery_users.sql).
The existing workflow tables are read and joined by `Unique_Key`. New workflow
events are appended to the relevant stage table.

## Deploy to Vercel

Vercel can run the Flask web handler through `api/index.py`. Before deploying,
configure external services because Vercel's filesystem is temporary:

1. Push this repository to GitHub and import it into Vercel.
2. In Vercel project settings, add these environment variables for Production:
   - `SECRET_KEY`: a long random value
   - `BIGQUERY_PROJECT`: `mis-gempundit`
   - `BIGQUERY_DATASET`: `Content_FMS`
   - `BIGQUERY_USERS_TABLE`: `Users`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`: the complete service-account JSON
   - `GCS_BUCKET`: your Google Cloud Storage bucket name
   - `FLASK_ENV`: `production`
3. Deploy the project. Vercel uses `vercel.json` and the Python dependencies in `requirements.txt`.
4. No database migration is required. Run [bigquery_users.sql](bigquery_users.sql)
   once in BigQuery, then create the first admin with:
   ```powershell
   .\\.venv\\Scripts\\python.exe create_bigquery_admin.py
   ```

The Vercel service account must have BigQuery Job User, BigQuery Data Editor,
and Storage Object Admin permissions. Never commit the service-account JSON or
password files; enter them only as encrypted Vercel environment variables.

## Deployment to Google Cloud

1. **Build Docker image**
   ```bash
   docker build -t gcr.io/<PROJECT_ID>/flask-crm:latest .
   ```
2. **Push to Artifact Registry**
   ```bash
   docker push gcr.io/<PROJECT_ID>/flask-crm:latest
   ```
3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy flask-crm-service \
     --image gcr.io/<PROJECT_ID>/flask-crm:latest \
     --platform managed \
     --region us-central1 \
     --add-cloudsql-instances <PROJECT_ID>:us-central1:crm-db \
     --set-env-vars SECRET_KEY=<SECRET_KEY>,DATABASE_URL=<CLOUD_SQL_URI> \
     --allow-unauthenticated
   ```
4. **Run migrations via Cloud Run Job**
   ```bash
   gcloud run jobs execute migrate-job --region us-central1 --wait
   ```

## Prompt for Claude AI

Use the following prompt in Claude AI to generate code scaffolding, models, routes, and deployment scripts for this project:

<details>
<summary>Best Claude AI Prompt</summary>

```
Build a Flask-based Task Assignment & Audit CRM with the following specifications:
- Use Flask, Flask-Login, Flask-SQLAlchemy, Flask-Migrate, and python-fsm for workflow states.
- Implement a login-only page; no self-signup. Users are pre-created by admin.
- Define User model with roles: assignee, auditor, manager, admin. Use PBKDF2 for password hashing.
- Create Task model with fields: title, description, created_by, assigned_to, auditor, plan_date, completed_date, audit_date, revision_count, audit_notes, status (FSM), created_at, updated_at.
- Configure FSM states: assigned→in_progress→completed→under_audit→(audit_passed|audit_failed)→cancelled.
- Auto-assign auditor randomly on task completion.
- Log all status changes in TaskLog with action, previous, new status, user, notes, timestamp.
- Build HTML templates using Jinja2 and Tailwind CSS: login.html, dashboard.html, create_task.html, task_detail.html, audit_dashboard.html, base.html.
- Add forms with Flask-WTF for login, task creation, status updates, and audit actions.
- Provide routes in Blueprint: login, logout, dashboard, create_task, task_detail (with POST for actions), audit_dashboard.
- Use SQLite locally and prepare for Cloud SQL (via DATABASE_URL env var) in production.
- Dockerize the app, include Tailwind build step, and write a Dockerfile with non-root user, collect static, and gunicorn.
- Provide cloudbuild.yaml for CI/CD: build image, push to Artifact Registry, run migrations, deploy to Cloud Run with Cloud SQL instance.
- Include instructions in README.md for local dev and Google Cloud deployment.
```

</details>
