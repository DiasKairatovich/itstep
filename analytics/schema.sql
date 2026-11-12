-- Общая схема аналитики: её читают и Node (server/analytics.js), и Python (analytics/db.py).

CREATE TABLE IF NOT EXISTS conversations (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id        TEXT    NOT NULL,
  channel           TEXT    NOT NULL,              -- website | telegram
  started_at        TEXT    NOT NULL,              -- ISO-8601, UTC
  rating            INTEGER,                       -- 1..5, NULL пока нет оценки
  handed_to_manager INTEGER NOT NULL DEFAULT 0,
  lead_created      INTEGER NOT NULL DEFAULT 0,
  is_test           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT    NOT NULL,                -- user | assistant
  text            TEXT    NOT NULL,
  created_at      TEXT    NOT NULL,
  is_fallback     INTEGER NOT NULL DEFAULT 0,      -- «ответа нет в базе знаний»
  tokens_in       INTEGER,
  tokens_out      INTEGER,
  cost_usd        REAL                             -- NULL, пока в prices.json нет цены
);

CREATE TABLE IF NOT EXISTS conversation_analysis (
  conversation_id INTEGER PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
  topic           TEXT,
  intent          TEXT,
  sentiment       TEXT,
  not_resolved    INTEGER,
  short_reason    TEXT,
  model           TEXT,
  tokens_in       INTEGER,
  tokens_out      INTEGER,
  cost_usd        REAL,
  analyzed_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_started ON conversations(started_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created      ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_analysis_conversation ON conversation_analysis(conversation_id);

CREATE TABLE IF NOT EXISTS knowledge_gaps (
  rank        INTEGER PRIMARY KEY,
  gap_title   TEXT    NOT NULL,
  count       INTEGER NOT NULL,
  example_1   TEXT    NOT NULL,
  example_2   TEXT    NOT NULL,
  updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_results (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  run_label   TEXT    NOT NULL,                -- before | after
  question_id INTEGER NOT NULL,
  "group"     TEXT    NOT NULL,                -- known | gap
  answer      TEXT    NOT NULL,
  verdict     TEXT    NOT NULL,                -- ok | partial | fail
  reason      TEXT    NOT NULL,
  created_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_results_label ON eval_results(run_label);

