-- Cross-check the numbers shown on /dashboard, /approvals, /my-tasks against
-- BigQuery directly. Run each block in BigQuery Studio (or `bq query
-- --use_legacy_sql=false`) and compare against what the app renders for the
-- same moment in time -- they should always match, because the app computes
-- these from the exact same rows (see app/bigquery_store.py: records(),
-- workflow_items(), and the metrics dict built in app/routes_bigquery.py
-- dashboard()).

-- ---------------------------------------------------------------------
-- 1) Legacy 7-stage content records: latest row per Unique_Key across all
--    stage tables, then the same status buckets the dashboard counts.
-- ---------------------------------------------------------------------
WITH all_stage_rows AS (
  SELECT *, 'Seed_File' AS source_table FROM `mis-gempundit.Content_FMS.Seed_File`
  UNION ALL
  SELECT *, 'Content_Planning' FROM `mis-gempundit.Content_FMS.Content_Planning`
  UNION ALL
  SELECT *, 'Content_Creation' FROM `mis-gempundit.Content_FMS.Content_Creation`
  UNION ALL
  SELECT *, 'Content_Review_and_Approval' FROM `mis-gempundit.Content_FMS.Content_Review_and_Approval`
  UNION ALL
  SELECT *, 'Content_Audit' FROM `mis-gempundit.Content_FMS.Content_Audit`
  UNION ALL
  SELECT *, 'Content_Publishing' FROM `mis-gempundit.Content_FMS.Content_Publishing`
  UNION ALL
  SELECT *, 'Content_Distribution' FROM `mis-gempundit.Content_FMS.Content_Distribution`
),
latest_per_key AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY Unique_Key ORDER BY Timestamp DESC) AS rn
  FROM all_stage_rows
  WHERE Unique_Key IS NOT NULL
),
current_state AS (
  SELECT
    Unique_Key,
    source_table,
    LOWER(COALESCE(Approval, '')) AS approval,
    CASE
      WHEN LOWER(COALESCE(Approval, '')) = 'approved' THEN 'audit_passed'
      WHEN LOWER(COALESCE(Approval, '')) = 'rejected' THEN 'audit_failed'
      WHEN LOWER(COALESCE(Approval, '')) = 'pending'  THEN 'under_audit'
      ELSE CASE source_table
        WHEN 'Seed_File' THEN 'assigned'
        WHEN 'Content_Planning' THEN 'in_progress'
        WHEN 'Content_Creation' THEN 'in_progress'
        WHEN 'Content_Review_and_Approval' THEN 'under_audit'
        WHEN 'Content_Audit' THEN 'under_audit'
        WHEN 'Content_Publishing' THEN 'audit_passed'
        WHEN 'Content_Distribution' THEN 'audit_passed'
      END
    END AS status
  FROM latest_per_key
  WHERE rn = 1
)
SELECT
  COUNT(*) AS total_records,
  COUNTIF(status IN ('assigned', 'in_progress')) AS total_pending,     -- must equal dashboard "Pending"
  COUNTIF(status = 'under_audit') AS under_audit,                      -- must equal dashboard "Under Review"
  COUNTIF(status = 'audit_passed') AS completed_count                  -- must equal dashboard "Published"
FROM current_state;

-- ---------------------------------------------------------------------
-- 2) Approval workflow: latest event per Unique_Key, bucketed the same
--    way as WorkflowItem / the "Approval Workflow" tiles on /dashboard.
-- ---------------------------------------------------------------------
WITH latest_event AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY unique_key ORDER BY timestamp DESC) AS rn
  FROM `mis-gempundit.Content_FMS.Content_Approval_Workflow`
)
SELECT
  COUNTIF(action IN ('DRAFT_RECEIVED', 'SUBMITTED')) AS pending_approval, -- "Pending Approval" tile
  COUNTIF(action NOT IN ('COMPLETED', 'DELETED')) AS in_progress,        -- "In Progress (loop)" tile
  COUNTIF(action = 'COMPLETED') AS completed,                            -- "Completed" tile
  COUNTIF(action = 'DELETED') AS deleted
FROM latest_event
WHERE rn = 1;

-- ---------------------------------------------------------------------
-- 3) Per-user "My Tasks" count (what a given doer sees on /my-tasks):
--    replace @user_email below.
-- ---------------------------------------------------------------------
WITH latest_event AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY unique_key ORDER BY timestamp DESC) AS rn
  FROM `mis-gempundit.Content_FMS.Content_Approval_Workflow`
),
-- assignee_email isn't necessarily set on the latest row (e.g. SUBMITTED
-- doesn't repeat it) -- carry it forward the same way WorkflowItem does.
carried_assignee AS (
  SELECT unique_key, assignee_email,
         ROW_NUMBER() OVER (PARTITION BY unique_key ORDER BY timestamp DESC) AS rn
  FROM `mis-gempundit.Content_FMS.Content_Approval_Workflow`
  WHERE assignee_email IS NOT NULL
)
SELECT COUNT(*) AS my_tasks
FROM latest_event le
JOIN carried_assignee ca ON ca.unique_key = le.unique_key AND ca.rn = 1
WHERE le.rn = 1
  AND le.action IN ('ALLOCATED', 'REWRITE_REQUESTED')
  AND ca.assignee_email = @user_email;
