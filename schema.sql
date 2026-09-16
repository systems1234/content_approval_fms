-- ===========================================================================
-- Content FMS — BigQuery schema.  Dataset: mis-gempundit.Content_FMS
-- Everything lives here. No Postgres, no local DB, no file store.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. AI_Content_Queue — what stage 1 produces.
--
-- The automation writes one row here per piece of content it has researched
-- and drafted. This app only ever READS it: a row is picked up when its
-- unique_key has no rows in Content_Approval_Workflow yet, so the automation
-- never has to be told what has already been taken.
--
-- status lets the automation hold a row back: only READY (or NULL) is pulled.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `mis-gempundit.Content_FMS.AI_Content_Queue` (
  unique_key          STRING   NOT NULL,  -- CNT-YYYY-NNNN, the key everything joins on
  generated_at        DATETIME NOT NULL,  -- when the AI finished this row (IST)
  status              STRING,             -- READY | HOLD | SKIPPED  (NULL = READY)

  -- what to write about
  category            STRING,             -- Gemstones, Rudraksha, Astrology, Yantra...
  gemstone_name       STRING,             -- Blue Sapphire, Emerald, 5 Mukhi Rudraksha...
  search_term         STRING,             -- the head keyword
  secondary_keywords  STRING,             -- comma separated
  search_volume       INT64,              -- monthly SV for the head keyword
  keyword_difficulty  INT64,              -- 0-100
  intent              STRING,             -- Informational | Commercial | Transactional | Navigational
  content_type        STRING,             -- Blog | Product tab | Category page | FAQ | Landing page
  language            STRING,             -- en, hi
  priority            STRING,             -- High | Medium | Low
  planned_date        DATE,               -- when it should be live

  -- where it goes
  target_url          STRING,             -- page to update; NULL means a new page
  meta_title          STRING,
  meta_description    STRING,

  -- what the AI wrote
  ai_draft            STRING,             -- the draft itself
  ai_draft_url        STRING,             -- or a Google Doc holding it
  word_count          INT64,
  ai_model            STRING,             -- which model produced it
  ai_confidence       FLOAT64,            -- 0-1, the model's own score
  research_notes      STRING              -- sources, SERP observations, anything useful
);

-- ---------------------------------------------------------------------------
-- 2. Users — who can act, and as what.
-- Append-only: newest row per user_id wins, so a role change is an INSERT.
--   admin | approver (Vivek) | writer (Kirti) | viewer
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `mis-gempundit.Content_FMS.Users` (
  user_id       INT64    NOT NULL,
  username      STRING   NOT NULL,
  email         STRING   NOT NULL,
  password_hash STRING,              -- legacy, unused
  role          STRING   NOT NULL,
  is_active     BOOL     NOT NULL,
  created_at    DATETIME NOT NULL,
  updated_at    DATETIME NOT NULL
);

-- ---------------------------------------------------------------------------
-- 3. Content_Approval_Workflow — one row per state change, never updated.
-- An item's current state is its newest row; its other fields are folded
-- forward from whichever earlier row last set them.
--
--   DRAFT_RECEIVED     pulled in from AI_Content_Queue, waiting on Vivek
--   APPROVED           Vivek accepted the draft
--   ALLOCATED          handed to Kirti (always written with APPROVED)
--   SUBMITTED          Kirti submitted a revision
--   REWRITE_REQUESTED  Vivek sent it back
--   COMPLETED          Vivek signed it off              (terminal)
--   REJECTED           Vivek killed the AI draft        (terminal)
--   DELETED            an admin cancelled the request   (terminal)
--   KEYWORDS_READY     optional: research done, draft still coming
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
  source_payload    STRING               -- the AI_Content_Queue row as JSON
);

-- If your workflow table predates the last two columns:
-- ALTER TABLE `mis-gempundit.Content_FMS.Content_Approval_Workflow`
--   ADD COLUMN IF NOT EXISTS source_row_id STRING,
--   ADD COLUMN IF NOT EXISTS source_payload STRING;

-- ---------------------------------------------------------------------------
-- 4. Reporting view — current state of everything, one row per item, joined
--    back to the seed row. Point Looker Studio at this, not at the raw table.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `mis-gempundit.Content_FMS.vw_Content_Status` AS
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (
           PARTITION BY unique_key ORDER BY timestamp DESC, event_id DESC) AS rn
  FROM `mis-gempundit.Content_FMS.Content_Approval_Workflow`
),
folded AS (
  SELECT
    unique_key,
    MIN(timestamp) AS first_seen,
    MAX(timestamp) AS last_change,
    MAX(COALESCE(revision_number, 0)) AS revisions,
    COUNTIF(action = 'REWRITE_REQUESTED') AS rewrites,
    ARRAY_AGG(NULLIF(assignee_email, '') IGNORE NULLS
              ORDER BY timestamp DESC LIMIT 1)[SAFE_OFFSET(0)] AS writer_email,
    ARRAY_AGG(NULLIF(content_url, '') IGNORE NULLS
              ORDER BY timestamp DESC LIMIT 1)[SAFE_OFFSET(0)] AS content_url,
    ARRAY_AGG(word_count IGNORE NULLS
              ORDER BY timestamp DESC LIMIT 1)[SAFE_OFFSET(0)] AS word_count
  FROM `mis-gempundit.Content_FMS.Content_Approval_Workflow`
  GROUP BY unique_key
)
SELECT
  f.unique_key,
  q.category, q.gemstone_name, q.search_term, q.search_volume,
  q.keyword_difficulty, q.intent, q.content_type, q.priority,
  q.planned_date, q.target_url,
  r.action AS stage,
  f.writer_email, f.content_url, f.word_count, f.revisions, f.rewrites,
  f.first_seen, f.last_change,
  DATETIME_DIFF(f.last_change, f.first_seen, HOUR) AS hours_in_flight,
  r.action IN ('COMPLETED', 'REJECTED', 'DELETED') AS is_closed
FROM folded f
JOIN ranked r ON r.unique_key = f.unique_key AND r.rn = 1
LEFT JOIN `mis-gempundit.Content_FMS.AI_Content_Queue` q
       ON q.unique_key = f.unique_key;
