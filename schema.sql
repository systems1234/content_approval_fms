-- Content FMS — BigQuery schema (dataset: mis-gempundit.Content_FMS)
--
-- Two tables. Both are append-only: a row is never updated or deleted, and the
-- current state of anything is the newest row for its key. Writes go through
-- parameterised DML (not the streaming API) so a write is readable immediately
-- after it lands.

-- ---------------------------------------------------------------------------
-- Users. Sign-in is Google Workspace SSO only; a row here is what grants access.
-- Newest row per user_id wins, so a role change or deactivation is an INSERT.
--
-- role:
--   admin     -- everything, plus user management
--   approver  -- reviews and decides (Vivek)
--   writer    -- receives allocations and rewrites content (Kirti)
--   viewer    -- read-only
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `mis-gempundit.Content_FMS.Users` (
  user_id       INT64    NOT NULL,
  username      STRING   NOT NULL,
  email         STRING   NOT NULL,
  password_hash STRING,              -- legacy column, unused (SSO only)
  role          STRING   NOT NULL,
  is_active     BOOL     NOT NULL,
  created_at    DATETIME NOT NULL,
  updated_at    DATETIME NOT NULL
);

-- ---------------------------------------------------------------------------
-- The workflow. One row per state transition, oldest to newest; an item's
-- current state is its newest row, and its other fields are folded forward from
-- whichever earlier row last set them.
--
-- action:
--   KEYWORDS_READY     the AI finished keyword research (informational)
--   DRAFT_RECEIVED     the AI's draft arrived and is waiting on the approver
--   APPROVED           approver accepted the draft
--   ALLOCATED          handed to a writer (always written with APPROVED)
--   SUBMITTED          writer submitted a version
--   REWRITE_REQUESTED  approver sent it back to the same writer
--   COMPLETED          approver gave final confirmation        (terminal)
--   REJECTED           approver killed the AI draft outright   (terminal)
--   DELETED            an admin cancelled the request          (terminal)
--
-- source_payload keeps the AI's original row verbatim as JSON, so however many
-- columns that table ends up with, nothing is lost and nothing here needs to
-- change to accept them.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `mis-gempundit.Content_FMS.Content_Approval_Workflow` (
  event_id          STRING   NOT NULL,
  timestamp         DATETIME NOT NULL,   -- IST, naive
  unique_key        STRING   NOT NULL,
  category          STRING,
  action            STRING   NOT NULL,
  actor_user_id     INT64,
  actor_email       STRING,
  assignee_user_id  INT64,
  assignee_email    STRING,
  content_text      STRING,
  content_url       STRING,
  word_count        INT64,
  search_keywords   STRING,
  search_volume     INT64,
  comment           STRING,
  revision_number   INT64,
  source_row_id     STRING,
  source_payload    STRING               -- JSON of the AI row, as delivered
);

-- If you already have Content_Approval_Workflow without the last two columns:
-- ALTER TABLE `mis-gempundit.Content_FMS.Content_Approval_Workflow`
--   ADD COLUMN IF NOT EXISTS source_row_id STRING,
--   ADD COLUMN IF NOT EXISTS source_payload STRING;
