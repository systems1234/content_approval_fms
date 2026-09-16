#!/usr/bin/env bash
# Run from the repo root, once, before copying the new files in.
# Everything below is either dead (no route reaches it) or replaced.
set -euo pipefail

git rm -r --quiet --ignore-unmatch \
  README.md README_UPDATED.md QUICKSTART.md FEATURES.md PROJECT_SUMMARY.md \
  DEPLOYMENT.md DEPLOYMENT_FILES_SUMMARY.md CLOUD_RUN_DEPLOYMENT.md \
  FMS_COMPLETED.md FMS_IMPLEMENTATION_STATUS.md LOGO_UPDATE_SUMMARY.md \
  migrations \
  package.json package-lock.json postcss.config.js tailwind.config.js \
  app/static/src app/static/css/output.css app/static/css/custom.css \
  app/forms.py app/routes_bigquery.py app/bigquery_store.py \
  app/templates/dashboard.html app/templates/dashboard_bigquery.html \
  app/templates/create_task.html app/templates/task_detail.html \
  app/templates/reports.html app/templates/audit_dashboard.html \
  app/templates/content_detail_bigquery.html app/templates/create_content_bigquery.html \
  app/templates/users.html app/templates/users_bigquery.html \
  app/templates/create_user.html app/templates/update_password.html \
  app/templates/workflow_list.html app/templates/workflow_detail.html \
  app/templates/login.html app/templates/base.html \
  app/templates/admin \
  add_document_fields.py fix_permissions_now.py fix_template.py \
  migrate_tasklog_fields.py create_bigquery_admin.py \
  bigquery_users.sql content_approval_workflow.sql kpi_validation.sql \
  Dockerfile .dockerignore .gcloudignore deploy.sh setup.sh setup.bat \
  pyproject.toml uploads

echo "Old files staged for deletion. Now copy the new tree over and commit."
