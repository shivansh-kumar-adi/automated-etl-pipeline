# Automated ETL Pipeline

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Local-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00)
![Pydantic](https://img.shields.io/badge/Pydantic-2.x-E92063)
![Tests](https://img.shields.io/badge/unit_tests-18%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

A production-style, backend-only ETL system that extracts public post data, validates and transforms every record, preserves raw input for auditability, performs idempotent PostgreSQL UPSERTs, and proves each run with logs, run history, rejected-record details, and a machine-readable reconciliation report.

The project demonstrates reliability ideas used in larger data platforms without requiring paid services, API keys, Docker, Airflow, Kafka, or cloud infrastructure.

> **Data-source note:** JSONPlaceholder returns approximately 100 real posts. This project does not pretend that the endpoint contains 1,000 records or supports production pagination. A separate deterministic synthetic generator supplies larger datasets for testing and load simulation.

---

## Table of contents

- [What this project demonstrates](#what-this-project-demonstrates)
- [System context](#system-context)
- [Deployment topology](#deployment-topology)
- [Layered system design](#layered-system-design)
- [High-level architecture](#high-level-architecture)
- [End-to-end execution flow](#end-to-end-execution-flow)
- [Record-level data lineage](#record-level-data-lineage)
- [Component responsibilities](#component-responsibilities)
- [Database design](#database-design)
- [Data-quality decision flow](#data-quality-decision-flow)
- [Retry and failure-handling design](#retry-and-failure-handling-design)
- [Transaction and failure boundaries](#transaction-and-failure-boundaries)
- [Idempotency and update policy](#idempotency-and-update-policy)
- [Reconciliation model](#reconciliation-model)
- [Observability and audit trail](#observability-and-audit-trail)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Running the pipeline](#running-the-pipeline)
- [Testing](#testing)
- [Inspecting results](#inspecting-results)
- [Security](#security)
- [Design decisions and trade-offs](#design-decisions-and-trade-offs)
- [Known limitations](#known-limitations)
- [Future enhancements](#future-enhancements)
- [Interview talking points](#interview-talking-points)

---

## What this project demonstrates

| Engineering area | Implementation |
|---|---|
| Data ingestion | HTTP extraction from JSONPlaceholder and deterministic synthetic input |
| Reliability | Configurable timeout, selective retry, exponential backoff, and bounded attempts |
| Data quality | Strict Pydantic schema validation, text checks, identifier rules, and duplicate detection |
| Auditability | Raw JSONB staging, UUID run IDs, timestamps, rejected-record details, and run history |
| Data modeling | Separate staging, rejection, final, and pipeline-control tables |
| Idempotency | PostgreSQL primary key plus `INSERT ... ON CONFLICT DO UPDATE` |
| Transaction safety | SQLAlchemy transaction scopes with automatic rollback on failure |
| Reconciliation | Explicit source-to-destination count invariants and PASS/FAIL reports |
| Observability | Console logs, rotating file logs, CSV reports, and database run metadata |
| Testability | Mocked HTTP unit tests and opt-in isolated PostgreSQL integration tests |

## System context

This diagram shows the system boundary and the people or systems that interact with it.

```mermaid
flowchart LR
    Engineer([Developer / Data Engineer])
    API[JSONPlaceholder<br/>Public REST API]
    Generator[Deterministic<br/>Synthetic Generator]

    subgraph ETLSystem[Automated ETL Pipeline]
        CLI[Python CLI]
        Pipeline[ETL Orchestrator]
        Reports[CSV Reports]
        Logs[Rotating Logs]
    end

    PostgreSQL[(Local PostgreSQL)]

    Engineer -->|run and configure| CLI
    CLI --> Pipeline
    API -->|real JSON records| Pipeline
    Generator -->|test records| Pipeline
    Pipeline -->|staging, final data, history| PostgreSQL
    Pipeline --> Reports
    Pipeline --> Logs
    Engineer -->|inspect| PostgreSQL
    Engineer --> Reports
    Engineer --> Logs
```

The API and synthetic generator are intentionally separate sources. API records are real public records; generated records are explicitly labeled test data.

## Deployment topology

The project runs as a local batch application. There is no web server, frontend, message broker, or mandatory container layer.

```mermaid
flowchart TB
    subgraph Machine[Developer Workstation]
        direction LR

        subgraph PythonRuntime[Python 3.11+ Virtual Environment]
            CLI[Command-line scripts]
            APP[ETL application modules]
            CLI --> APP
        end

        subgraph FileSystem[Local File System]
            ENV[.env configuration]
            LOGS[logs/pipeline.log]
            REPORTS[reports/*.csv]
            TESTDATA[data/*.json]
        end

        DB[(Local PostgreSQL Server)]
    end

    INTERNET[(Public Internet)]
    API[JSONPlaceholder API]

    ENV -->|configuration| APP
    TESTDATA -->|optional generated input| APP
    APP -->|SQL over local TCP| DB
    APP --> LOGS
    APP --> REPORTS
    APP -->|HTTPS GET| INTERNET
    INTERNET --> API
```

This topology keeps the project inexpensive and reproducible. Only real API extraction requires internet access; synthetic runs and unit tests can execute offline once dependencies are installed.

## Layered system design

```mermaid
flowchart TB
    subgraph Interface[Interface Layer]
        RUN[run_pipeline.py]
        GEN[generate_test_data.py]
        LATEST[latest_run.py]
        RESET[reset_database.py]
    end

    subgraph Orchestration[Orchestration Layer]
        PIPE[pipeline.py<br/>run lifecycle and stage coordination]
    end

    subgraph Domain[Data Processing Layer]
        EXTRACT[extract.py]
        VALIDATE[validate.py]
        TRANSFORM[transform.py]
        RECONCILE[reconcile.py]
        SYNTHETIC[synthetic.py]
    end

    subgraph Persistence[Persistence and Output Layer]
        DATABASE[database.py]
        STAGING[staging.py]
        LOAD[load.py]
        REPORT[report.py]
        LOGGING[logging_config.py]
    end

    subgraph Infrastructure[Infrastructure]
        POSTGRES[(PostgreSQL)]
        FILES[(Logs and CSV files)]
        REMOTE[JSONPlaceholder]
    end

    Interface --> Orchestration
    Orchestration --> Domain
    Orchestration --> Persistence
    EXTRACT --> REMOTE
    Persistence --> POSTGRES
    REPORT --> FILES
    LOGGING --> FILES
```

The dependency direction stays simple: CLI scripts call orchestration; orchestration calls domain and persistence modules; infrastructure details do not leak into validation or transformation logic. This separation makes the pure data-quality rules easy to test without PostgreSQL.

## High-level architecture

```mermaid
flowchart LR
    subgraph Sources[Input Sources]
        API[JSONPlaceholder API]
        SYN[Synthetic Records]
    end

    subgraph Application[Python ETL Application]
        direction LR
        EXT[Extract<br/>Requests + Tenacity]
        VAL[Validate<br/>Pydantic]
        TRN[Transform<br/>Normalize schema and text]
        LOAD[Load<br/>SQLAlchemy + Psycopg]
        REC[Reconcile<br/>Count invariants]
        EXT --> VAL --> TRN --> LOAD --> REC
    end

    subgraph PostgreSQL[PostgreSQL Data Store]
        STG[(staging_posts<br/>raw JSONB)]
        REJ[(rejected_records)]
        FINAL[(posts<br/>curated data)]
        RUNS[(pipeline_runs<br/>audit history)]
    end

    subgraph Outputs[Operational Outputs]
        CSV[Reconciliation CSV]
        LOG[Console + rotating log]
    end

    API --> EXT
    SYN --> EXT
    EXT --> STG
    VAL -->|invalid or duplicate| REJ
    LOAD --> FINAL
    REC --> CSV
    Application --> RUNS
    Application --> LOG
    STG --> REC
    REJ --> REC
    FINAL --> REC
```

The code uses a **pipeline architecture** with focused modules rather than one large script. Database operations remain in persistence modules, validation remains in Pydantic models, and orchestration remains in `pipeline.py`.

## End-to-end execution flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Developer
    participant CLI as run_pipeline.py
    participant ORCH as pipeline.py
    participant API as JSONPlaceholder
    participant VAL as validate.py
    participant DB as PostgreSQL
    participant REC as reconcile.py
    participant OUT as Reports / Logs

    User->>CLI: --source jsonplaceholder
    CLI->>DB: initialize schema if needed
    CLI->>ORCH: start pipeline
    ORCH->>DB: create RUNNING history row
    ORCH->>API: GET /posts with timeout

    alt transient failure: timeout, connection, 429, or 5xx
        API--xORCH: transient error
        ORCH->>API: retry with exponential backoff
    else permanent 4xx or malformed response
        API--xORCH: permanent error
        ORCH->>DB: mark run FAIL
        ORCH->>OUT: write error log
    else successful response
        API-->>ORCH: JSON array
        ORCH->>DB: store raw records in staging_posts
        ORCH->>VAL: validate every record
        VAL-->>ORCH: accepted records + rejection details
        ORCH->>DB: write rejected_records
        ORCH->>DB: UPSERT transformed valid posts
        ORCH->>REC: compare all record counts
        REC-->>ORCH: PASS or FAIL + details
        ORCH->>DB: finalize pipeline_runs row
        ORCH->>OUT: write CSV report and final log
        ORCH-->>CLI: run ID, status, counts, report path
        CLI-->>User: terminal summary
    end
```

Every execution receives a UUID before processing begins. That run ID connects logs, staging records, rejections, history, and the reconciliation report.

## Record-level data lineage

Data lineage shows where one source record can travel and which evidence remains at each step.

```mermaid
flowchart LR
    SRC[Source record<br/>id, userId, title, body]
    META[Attach run ID and<br/>extraction timestamp]
    RAW[(Raw JSONB staging)]
    CHECK{Validation result}
    BAD[(Rejected record<br/>reason + details)]
    MAP[Transform<br/>userId to user_id<br/>normalize text]
    UPSERT{Destination ID exists?}
    INSERT[Insert new post<br/>set created_at]
    UPDATE[Update existing post<br/>preserve created_at]
    FINAL[(Curated posts table)]
    COUNTS[Run counters]
    REPORT[Reconciliation report]

    SRC --> META --> RAW
    META --> CHECK
    CHECK -->|invalid| BAD --> COUNTS
    CHECK -->|valid| MAP --> UPSERT
    UPSERT -->|no| INSERT --> FINAL
    UPSERT -->|yes| UPDATE --> FINAL
    RAW --> COUNTS
    FINAL --> COUNTS
    COUNTS --> REPORT
```

The staging row preserves source truth, the rejection row preserves quality evidence, and the final row represents the latest accepted business state. The shared run ID connects record-level evidence to the run-level report.

## Component responsibilities

| Module | Responsibility | Key behavior |
|---|---|---|
| `config.py` | Load and validate configuration | Reads `.env`; never hardcodes real credentials |
| `extract.py` | Retrieve source records | Timeouts, HTTP validation, bounded retries, response-shape checks |
| `validate.py` | Enforce input contract | Strict field types, required fields, positive IDs, non-empty text, duplicates |
| `transform.py` | Produce final schema | Whitespace normalization, renamed fields, ingestion timestamps |
| `staging.py` | Preserve raw input | JSONB payloads, validation state, processing state, rejection persistence |
| `load.py` | Maintain curated destination | Parameterized PostgreSQL UPSERT and destination counting |
| `reconcile.py` | Prove count consistency | Explicit invariants; returns calculated PASS or FAIL |
| `report.py` | Create machine-readable evidence | One CSV row per run with counts, status, and details |
| `logging_config.py` | Configure observability | Console and rotating file handlers with run IDs |
| `pipeline.py` | Coordinate the workflow | Run lifecycle, transactions, stage ordering, final status |

## Database design

```mermaid
erDiagram
    PIPELINE_RUNS ||--o{ STAGING_POSTS : records
    PIPELINE_RUNS ||--o{ REJECTED_RECORDS : explains

    PIPELINE_RUNS {
        uuid run_id PK
        text source_name
        timestamptz started_at
        timestamptz ended_at
        text status
        int extraction_count
        int staging_count
        int accepted_count
        int rejected_count
        int inserted_count
        int updated_count
        int duplicate_count
        int load_failure_count
        int destination_unique_count
        text reconciliation_details
    }

    STAGING_POSTS {
        bigint staging_id PK
        uuid run_id FK
        int source_id
        jsonb raw_payload
        timestamptz extracted_at
        text validation_status
        text processing_status
    }

    REJECTED_RECORDS {
        bigint rejection_id PK
        uuid run_id FK
        int source_id
        text reason
        text details
        timestamptz rejected_at
    }

    POSTS {
        int id PK
        int user_id
        text title
        text body
        timestamptz created_at
        timestamptz updated_at
    }
```

### Why four tables?

- `pipeline_runs` is the control plane: one row summarizes one execution.
- `staging_posts` is the audit layer: it preserves source payloads before cleanup.
- `rejected_records` is the data-quality evidence: it explains why records failed.
- `posts` is the curated destination: it contains only valid, normalized records.

`staging_posts` has a unique constraint on `(run_id, source_id)`. The final table has a primary key on the original source ID. These constraints protect both within-run staging and cross-run final loading.

## Data-quality decision flow

```mermaid
flowchart TD
    START([Incoming record]) --> OBJ{JSON object?}
    OBJ -->|No| REJECT[Create rejection]
    OBJ -->|Yes| REQUIRED{All required fields?}
    REQUIRED -->|No| REJECT
    REQUIRED -->|Yes| TYPES{Strict field types valid?}
    TYPES -->|No| REJECT
    TYPES -->|Yes| IDS{IDs are positive integers?}
    IDS -->|No| REJECT
    IDS -->|Yes| TEXT{Title and body non-empty?}
    TEXT -->|No| REJECT
    TEXT -->|Yes| DUP{Source ID already seen?}
    DUP -->|Yes| DUPREJ[Reject as duplicate_source_id]
    DUP -->|No| CLEAN[Trim and collapse whitespace]
    CLEAN --> STANDARD[Map to final schema]
    STANDARD --> ACCEPT([Accepted for UPSERT])
    REJECT --> CAPTURE[Capture run ID, optional source ID,<br/>reason, details, timestamp]
    DUPREJ --> CAPTURE
    CAPTURE --> REJTABLE[(rejected_records)]
```

| Rule | Example failure | Outcome |
|---|---|---|
| Required `id`, `userId`, `title`, and `body` | Missing `title` | Rejected |
| Strict integer identifiers | `"userId": "7"` | Rejected rather than silently coerced |
| Positive identifiers | `"id": 0` | Rejected |
| Non-empty text after trimming | `"body": "   "` | Rejected |
| Unique source ID within a batch | Second occurrence of ID `10` | First accepted; duplicate rejected |
| Unexpected extra fields | Additional source metadata | Ignored by standardized output |

## Retry and failure-handling design

```mermaid
flowchart TD
    CALL[Send HTTP request<br/>with configured timeout] --> RESULT{Result}
    RESULT -->|2xx| JSON{Valid JSON array<br/>of objects?}
    JSON -->|Yes| SUCCESS([Extraction succeeds])
    JSON -->|No| PERM[Fail immediately<br/>malformed response]
    RESULT -->|Timeout or connection error| RETRYABLE
    RESULT -->|HTTP 429| RETRYABLE[Retryable failure]
    RESULT -->|HTTP 5xx| RETRYABLE
    RESULT -->|Other HTTP 4xx| PERM[Permanent failure<br/>do not retry]
    RETRYABLE --> LIMIT{Attempts remaining?}
    LIMIT -->|Yes| WAIT[Exponential backoff<br/>bounded maximum wait]
    WAIT --> CALL
    LIMIT -->|No| EXHAUSTED[Fail after configured maximum]
    PERM --> FAILED([Run fails and error is logged])
    EXHAUSTED --> FAILED
```

Retries are selective. Retrying a timeout or server error can recover from a temporary problem; retrying a `404` or malformed JSON usually wastes time and hides the real issue.

## Transaction and failure boundaries

```mermaid
flowchart TD
    START([Create run history row]) --> EXTRACT[Extract source data]
    EXTRACT -->|failure| MARKFAIL[Update run status to FAIL]
    EXTRACT -->|success| TXBEGIN[Begin database transaction]

    subgraph AtomicWork[Atomic staging and loading transaction]
        TXBEGIN --> STAGE[Stage raw records]
        STAGE --> REJECTS[Save rejection details]
        REJECTS --> LOAD[UPSERT accepted records]
        LOAD --> STATUS[Update staging processing status]
    end

    STATUS -->|all statements succeed| COMMIT[Commit transaction]
    STAGE -->|database exception| ROLLBACK[Rollback transaction]
    REJECTS -->|database exception| ROLLBACK
    LOAD -->|database exception| ROLLBACK
    STATUS -->|database exception| ROLLBACK

    ROLLBACK --> MARKFAIL
    COMMIT --> RECON[Calculate reconciliation]
    RECON --> REPORT[Write CSV report]
    REPORT --> FINALIZE[Finalize run status and counts]
    MARKFAIL --> ERRORLOG[Write exception details to log]
```

The staging and load work is wrapped in a SQLAlchemy transaction. If one database statement fails, the transaction is rolled back instead of leaving a partly loaded batch. Run-history updates use a separate transaction so that failure evidence can still be recorded after the data transaction is rolled back.

## Idempotency and update policy

```mermaid
sequenceDiagram
    participant P as Pipeline
    participant DB as posts table
    Note over P,DB: First run for source ID 42
    P->>DB: INSERT id=42, title="Original"
    DB-->>P: inserted=1
    Note over P,DB: Second run with unchanged ID 42
    P->>DB: INSERT ... ON CONFLICT DO UPDATE
    DB-->>P: same row updated, no duplicate
    Note over P,DB: Later run with changed source data
    P->>DB: UPSERT id=42, title="Revised"
    DB-->>P: mutable fields replaced, created_at preserved
```

The policy is **source-wins for mutable fields**:

- `id` remains the stable source identifier and primary key.
- `created_at` records the first successful insertion.
- `user_id`, `title`, and `body` take the newest valid source values.
- `updated_at` records the latest successful observation.
- Source deletions are not inferred because the API has no reliable deletion feed.

This guarantees uniqueness but does not maintain historical versions.

## Reconciliation model

Reconciliation answers: **Did every extracted record reach a documented outcome?**

```mermaid
flowchart LR
    EX[Extracted records] --> AC[Accepted records]
    EX --> RJ[Rejected records]
    EX --> ST[Unique staged records]
    EX --> DU[Duplicate source IDs]
    AC --> IN[Inserted]
    AC --> UP[Updated]
    AC --> LF[Load failures]
    IN --> DEST[Destination unique IDs]
    UP --> DEST

    subgraph Rules[PASS invariants]
        R1[extracted = accepted + rejected]
        R2[extracted = staged + duplicates]
        R3[accepted = inserted + updated + load failures]
        R4[destination unique = accepted - load failures]
        R5[duplicates cannot exceed rejected]
    end
```

| Invariant | Purpose |
|---|---|
| `extracted = accepted + rejected` | Every source record received a validation outcome |
| `extracted = staged + duplicates` | Unique staging plus duplicate IDs explains extraction |
| `accepted = inserted + updated + load failures` | Every accepted record received a load outcome |
| `destination_unique = accepted - load_failures` | Loaded IDs exist in the destination |
| `duplicates <= rejected` | Duplicate records are represented as rejections |

If any invariant fails, reconciliation returns `FAIL`, records the mismatch, writes it to the CSV and logs, and the CLI exits non-zero. The pipeline never hardcodes a PASS result.

## Observability and audit trail

```mermaid
stateDiagram-v2
    [*] --> RUNNING: run ID created
    RUNNING --> PASS: all stages complete and invariants hold
    RUNNING --> FAIL: extraction, database, or reconciliation failure
    PASS --> [*]
    FAIL --> [*]
```

Each log entry includes timestamp, severity, logger name, run ID, and message. Logs go to the terminal and `logs/pipeline.log`; the file rotates at approximately 2 MB and keeps five backups.

The database history and CSV report record run identity, timing, source, all major counts, reconciliation status, and explanatory details. Raw payloads are not written to application logs; they remain in staging for controlled audit and debugging.

## Project structure

```text
automated-etl-pipeline/
├── src/
│   ├── config.py              # environment-backed settings
│   ├── database.py            # engine and repeatable schema setup
│   ├── extract.py             # HTTP extraction and retry classification
│   ├── validate.py            # Pydantic model and duplicate detection
│   ├── transform.py           # deterministic normalization
│   ├── staging.py             # raw staging and rejection persistence
│   ├── load.py                # PostgreSQL UPSERT logic
│   ├── reconcile.py           # count invariants
│   ├── report.py              # CSV generation
│   ├── logging_config.py      # console and rotating-file logging
│   ├── models.py              # shared domain dataclasses
│   ├── synthetic.py           # deterministic test data
│   └── pipeline.py            # end-to-end orchestration
├── scripts/
│   ├── run_pipeline.py        # primary CLI
│   ├── generate_test_data.py  # standalone JSON generator
│   ├── latest_run.py          # latest audit summary
│   └── reset_database.py      # guarded project-table reset
├── sql/schema.sql             # tables, constraints, and indexes
├── tests/                     # unit and opt-in integration tests
├── reports/                   # reconciliation CSV files
├── logs/                      # rotating application log
├── data/                      # generated synthetic JSON
├── .env.example
├── requirements.txt
├── pytest.ini
├── LICENSE
└── README.md
```

## Getting started

### Prerequisites

- Python 3.11 or newer
- PostgreSQL installed locally
- Git
- Internet access for dependency installation and real API extraction

Docker is not required.

### 1. Create a dedicated PostgreSQL database

Windows users can install PostgreSQL with the official installer and use SQL Shell (`psql`) or pgAdmin. On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```

Create a project-specific user and database:

```sql
CREATE USER etl_user WITH PASSWORD 'replace_with_a_local_password';
CREATE DATABASE etl_pipeline OWNER etl_user;
```

### 2. Create a virtual environment

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

### 3. Configure the environment

Edit `.env` using `.env.example` as the template. `.env` is excluded from version control. The first run applies the repeatable schema in `sql/schema.sql`.

## Running the pipeline

Real public API data:

```bash
python -m scripts.run_pipeline --source jsonplaceholder
```

Load 1,000 valid synthetic records:

```bash
python -m scripts.run_pipeline --source synthetic --records 1000
```

Run a mixed batch containing a missing field, invalid type, and duplicate ID:

```bash
python -m scripts.run_pipeline --source synthetic --records 1000 --scenario mixed
```

Generate JSON without loading it:

```bash
python -m scripts.generate_test_data --records 1000 --scenario valid --output data/synthetic_posts.json
```

View the latest run:

```bash
python -m scripts.latest_run
```

Reset only project tables:

```bash
python -m scripts.reset_database --confirm
```

The reset command also requires typing `RESET ETL` and truncates only this project's four tables.

## Testing

Database-free unit tests:

```bash
pytest -v -m "not integration"
```

The unit suite covers extraction, retries, HTTP errors, malformed responses, validation failures, rejection details, transformations, duplicates, synthetic generation, load error propagation, reconciliation, and CSV output.

For the isolated PostgreSQL integration test, create a disposable database whose name contains `test`:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://etl_user:password@localhost:5432/etl_pipeline_test'
pytest -v -m integration
```

The safety check rejects a URL that does not visibly identify a test database. The integration test verifies first-run insertion, an idempotent second run, changed-record updating, and transactional execution.

### Verification snapshot

On the environment used to build this project:

- 18 unit tests passed;
- 1 PostgreSQL integration test was skipped because PostgreSQL was unavailable;
- the live JSONPlaceholder check returned 100 valid records;
- 1,000 deterministic synthetic records were generated and validated.

These are verification results, not performance claims. Run the integration test locally before claiming full PostgreSQL verification.

## Inspecting results

```sql
\c etl_pipeline

SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;
SELECT validation_status, COUNT(*) FROM staging_posts GROUP BY validation_status;
SELECT reason, COUNT(*) FROM rejected_records GROUP BY reason;
SELECT * FROM posts ORDER BY id LIMIT 10;
```

Reports are written to `reports/reconciliation_<run-id>.csv`. Logs are written to `logs/pipeline.log`.

Example CLI shape—actual IDs and counts depend on the input and database state:

```text
Run ID: 86f...c12
Status: PASS
Counts: RunCounts(extracted=100, staged=100, accepted=100,
                  rejected=0, inserted=100, updated=0, ...)
Report: reports/reconciliation_86f...c12.csv
```

## Security

- Database credentials come from `.env` and are never committed.
- SQL values use parameter binding rather than string interpolation.
- Logs avoid passwords, secrets, and full raw payloads.
- The reset utility requires a flag and interactive confirmation.
- Integration tests require a visibly named test database.
- Only public, non-sensitive JSONPlaceholder records are expected in staging.

## Design decisions and trade-offs

| Decision | Reason | Trade-off |
|---|---|---|
| Local PostgreSQL | Demonstrates relational constraints, JSONB, and UPSERT | Requires local setup |
| Raw staging before transformation | Preserves evidence and supports debugging | Uses additional storage |
| Strict Pydantic types | Exposes dirty data instead of silently coercing it | Rejects some recoverable values |
| Source-wins UPSERT | Simple, deterministic update policy | No historical versions |
| Full-source extraction | Correct for this small API without a cursor | Not suitable for very large sources |
| CSV reconciliation | Portable and easy to inspect or automate | Not a live dashboard |
| Synchronous single process | Easy to learn, test, and run locally | No distributed scheduling |

## Known limitations

- JSONPlaceholder has no service-level guarantee, authentication, incremental cursor, or reliable deletion feed.
- The public endpoint is treated as a full snapshot, not a change-data-capture source.
- Multiple simultaneous runs are not coordinated with a distributed lock.
- UPSERT stores current state only; it does not preserve record-version history.
- Timeout and server-error scenarios use mocked tests rather than a fake HTTP server.
- PostgreSQL integration must be verified locally when PostgreSQL is available.
- No throughput or production-readiness claim is made without measurement.

## Future enhancements

```mermaid
flowchart LR
    CURRENT[Current local ETL] --> LOCK[Advisory lock<br/>for overlapping runs]
    CURRENT --> HIST[Change-history table<br/>or SCD Type 2]
    CURRENT --> METRICS[Operational metrics]
    CURRENT --> SCHED[Lightweight scheduler]
    CURRENT --> DLQ[Rejected-data retention policy]
    CURRENT --> INC[Incremental cursor<br/>when a source supports one]
```

Airflow, Kafka, Kubernetes, and cloud deployment remain excluded until scale or operational requirements justify them.

## Interview talking points

1. **Why use staging?** It preserves the exact source payload and separates ingestion from business validation, improving auditability and recovery.
2. **How is the pipeline idempotent?** The source ID is the destination primary key, and PostgreSQL UPSERT updates an existing row instead of inserting another one.
3. **What makes retry logic safe?** Only transient failures are retried, attempts are bounded, and backoff reduces pressure on an unhealthy service.
4. **Why reconcile counts?** A pipeline can finish without throwing an exception while still losing records. Count invariants detect silent inconsistency.
5. **How are bad records handled?** They receive a reason, validation details, run ID, optional source ID, and timestamp in a dedicated table.
6. **How are credentials protected?** They stay in ignored environment configuration and never appear in source code or logs.
7. **What changes at larger scale?** Add incremental extraction, bulk loading, metrics, scheduling, concurrency control, and history retention only when requirements demand them.

## License

Licensed under the MIT License. See `LICENSE`.
