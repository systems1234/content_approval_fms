#!/usr/bin/env bash
# ============================================================================
# Content-FMS -- one-shot deploy to Cloud Run, run from Google Cloud Shell.
#
# Usage:
#   cd Content-FMS-main
#   chmod +x deploy.sh
#   PROJECT_ID=mis-gempundit REGION=asia-south1 \
#     GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=yyy \
#     ./deploy.sh
#
# Everything below has a sane default except GOOGLE_CLIENT_ID/SECRET --
# leave those unset to deploy with SSO disabled (password login only) and
# wire them up later with a second run of this script.
#
# The app itself is stateless: no Cloud SQL, no server-side sessions --
# it talks to BigQuery directly, so this script does NOT provision a
# database or run schema migrations against one. It does make sure the
# BigQuery dataset/tables the app expects exist.
# ============================================================================
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-south1}"
SERVICE_NAME="${SERVICE_NAME:-content-approval-fms}"
BIGQUERY_DATASET="${BIGQUERY_DATASET:-Content_FMS}"
BIGQUERY_USERS_TABLE="${BIGQUERY_USERS_TABLE:-Users}"
GOOGLE_WORKSPACE_DOMAIN="${GOOGLE_WORKSPACE_DOMAIN:-gempundit.com}"
GCS_BUCKET="${GCS_BUCKET:-}"                     # optional: for file uploads
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"         # optional: enables Google SSO
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}" # optional: enables Google SSO
SECRET_KEY="${SECRET_KEY:-}"                     # optional: generated if unset
WORKFLOW_API_KEY="${WORKFLOW_API_KEY:-}"         # optional: generated if unset

if [ -z "$PROJECT_ID" ]; then
  echo "PROJECT_ID is not set and 'gcloud config get-value project' returned nothing." >&2
  echo "Run: gcloud config set project <your-project-id>   or pass PROJECT_ID=... ./deploy.sh" >&2
  exit 1
fi

echo "==> Project: $PROJECT_ID   Region: $REGION   Service: $SERVICE_NAME"
gcloud config set project "$PROJECT_ID" >/dev/null

echo "==> Enabling required APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

echo "==> Ensuring the BigQuery dataset and tables exist"
bq --project_id="$PROJECT_ID" mk --dataset --location=US "${PROJECT_ID}:${BIGQUERY_DATASET}" 2>/dev/null \
  && echo "    created dataset ${BIGQUERY_DATASET}" \
  || echo "    dataset ${BIGQUERY_DATASET} already exists"
bq --project_id="$PROJECT_ID" query --use_legacy_sql=false < bigquery_users.sql
bq --project_id="$PROJECT_ID" query --use_legacy_sql=false < content_approval_workflow.sql
echo "    Users + Content_Approval_Workflow tables ready"
echo "    NOTE: the legacy stage tables (Seed_File, Content_Planning, Content_Creation,"
echo "    Content_Review_and_Approval, Content_Audit, Content_Publishing,"
echo "    Content_Distribution) are assumed to already exist from the original setup."

create_or_update_secret() {
  local name="$1" value="$2"
  if [ -z "$value" ]; then return 0; fi
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- >/dev/null
    echo "    updated secret $name"
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic >/dev/null
    echo "    created secret $name"
  fi
}

echo "==> Syncing secrets (Secret Manager)"
[ -z "$SECRET_KEY" ] && SECRET_KEY="$(openssl rand -hex 32)"
create_or_update_secret content-fms-secret-key "$SECRET_KEY"

[ -z "$WORKFLOW_API_KEY" ] && WORKFLOW_API_KEY="$(openssl rand -hex 24)"
create_or_update_secret content-fms-workflow-api-key "$WORKFLOW_API_KEY"

SECRETS_FLAG="SECRET_KEY=content-fms-secret-key:latest,WORKFLOW_API_KEY=content-fms-workflow-api-key:latest"
if [ -n "$GOOGLE_CLIENT_ID" ]; then
  create_or_update_secret content-fms-google-client-id "$GOOGLE_CLIENT_ID"
  SECRETS_FLAG="${SECRETS_FLAG},GOOGLE_CLIENT_ID=content-fms-google-client-id:latest"
fi
if [ -n "$GOOGLE_CLIENT_SECRET" ]; then
  create_or_update_secret content-fms-google-client-secret "$GOOGLE_CLIENT_SECRET"
  SECRETS_FLAG="${SECRETS_FLAG},GOOGLE_CLIENT_SECRET=content-fms-google-client-secret:latest"
fi

ENV_VARS="FLASK_ENV=production,BIGQUERY_PROJECT=${PROJECT_ID},BIGQUERY_DATASET=${BIGQUERY_DATASET},BIGQUERY_USERS_TABLE=${BIGQUERY_USERS_TABLE},GOOGLE_WORKSPACE_DOMAIN=${GOOGLE_WORKSPACE_DOMAIN}"
[ -n "$GCS_BUCKET" ] && ENV_VARS="${ENV_VARS},GCS_BUCKET=${GCS_BUCKET}"

echo "==> Building (Tailwind CSS + the Flask image via Dockerfile) and deploying to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "$ENV_VARS" \
  --set-secrets "$SECRETS_FLAG"

echo "==> Granting the Cloud Run runtime service account BigQuery access"
SERVICE_ACCOUNT="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(spec.template.spec.serviceAccountName)')"
if [ -z "$SERVICE_ACCOUNT" ]; then
  PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
  SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" --role="roles/bigquery.dataEditor" --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" --role="roles/bigquery.jobUser" --quiet >/dev/null
if [ -n "$GCS_BUCKET" ]; then
  gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" --role="roles/storage.objectAdmin" --quiet >/dev/null
fi

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

echo ""
echo "============================================================================"
echo " Deployed:  $SERVICE_URL"
echo "============================================================================"
if [ -n "$GOOGLE_CLIENT_ID" ]; then
  echo " Google SSO is ON. In the Google Cloud Console -> APIs & Services ->"
  echo " Credentials -> this OAuth client, make sure this is an authorized"
  echo " redirect URI:"
  echo "   ${SERVICE_URL}/login/google/callback"
else
  echo " Google SSO is OFF (no GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET given)."
  echo " Re-run with those two env vars set to turn it on."
fi
echo ""
echo " Webhook API key for the external keyword-search / content-writer API"
echo " (POST to ${SERVICE_URL}/api/workflow/keyword-search and .../content-draft"
echo " with header 'X-API-Key: <this>'):"
echo "   $WORKFLOW_API_KEY"
echo ""
echo " If no admin user exists yet, create one now (needs BigQuery write access"
echo " from this Cloud Shell session):"
echo "   BIGQUERY_PROJECT=$PROJECT_ID BIGQUERY_DATASET=$BIGQUERY_DATASET python3 create_bigquery_admin.py"
echo "============================================================================"
