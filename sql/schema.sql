CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id UUID PRIMARY KEY,
  source_name TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('RUNNING', 'PASS', 'FAIL')),
  extraction_count INTEGER NOT NULL DEFAULT 0,
  staging_count INTEGER NOT NULL DEFAULT 0,
  accepted_count INTEGER NOT NULL DEFAULT 0,
  rejected_count INTEGER NOT NULL DEFAULT 0,
  inserted_count INTEGER NOT NULL DEFAULT 0,
  updated_count INTEGER NOT NULL DEFAULT 0,
  duplicate_count INTEGER NOT NULL DEFAULT 0,
  load_failure_count INTEGER NOT NULL DEFAULT 0,
  destination_unique_count INTEGER NOT NULL DEFAULT 0,
  reconciliation_details TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS staging_posts (
  staging_id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
  source_id INTEGER NOT NULL,
  raw_payload JSONB NOT NULL,
  extracted_at TIMESTAMPTZ NOT NULL,
  validation_status TEXT NOT NULL CHECK (validation_status IN ('pending', 'valid', 'rejected')),
  processing_status TEXT NOT NULL CHECK (processing_status IN ('staged', 'loaded', 'complete', 'failed')),
  UNIQUE (run_id, source_id)
);
CREATE INDEX IF NOT EXISTS idx_staging_run_status ON staging_posts(run_id, validation_status);

CREATE TABLE IF NOT EXISTS rejected_records (
  rejection_id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
  source_id INTEGER,
  reason TEXT NOT NULL,
  details TEXT NOT NULL,
  rejected_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rejections_run ON rejected_records(run_id);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL CHECK (user_id > 0),
  title TEXT NOT NULL CHECK (length(trim(title)) > 0),
  body TEXT NOT NULL CHECK (length(trim(body)) > 0),
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
