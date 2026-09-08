-- Event-sourced approval workflow table.
-- One append-only row per state transition; current state of a piece of
-- content is the most recent row for its unique_key (see
-- BigQueryStore.workflow_state in app/bigquery_store.py).
--
-- action values (state machine):
--   DRAFT_RECEIVED     -- external API posted the auto-written draft (stage 1+2 done)
--   APPROVED           -- Vivek approved the draft, not yet allocated
--   ALLOCATED          -- content allocated to a doer
--   SUBMITTED          -- doer submitted an updated version
--   REWRITE_REQUESTED  -- Vivek sent it back to the doer for changes (loops to ALLOCATED)
--   COMPLETED          -- Vivek gave final confirmation (terminal)
--   DELETED            -- request cancelled/deleted (terminal)
CREATE TABLE IF NOT EXISTS `mis-gempundit.Content_FMS.Content_Approval_Workflow` (
  event_id STRING NOT NULL,
  timestamp DATETIME NOT NULL,
  unique_key STRING NOT NULL,
  category STRING,
  action STRING NOT NULL,
  actor_user_id INT64,
  actor_email STRING,
  assignee_user_id INT64,
  assignee_email STRING,
  content_text STRING,
  content_url STRING,
  word_count INT64,
  search_keywords STRING,
  search_volume INT64,
  comment STRING,
  revision_number INT64
);
