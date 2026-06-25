# Database Schema

PostgreSQL is the **system of record**. 11 tables, all with UUID primary keys
(`uuid_generate_v4()`) and `created_at`/`updated_at` timestamps (from `UUIDPrimaryKeyMixin`
+ `TimestampMixin` in `backend/app/db/base.py`). ORM definitions live in
`backend/app/models/`.

## Entity-relationship overview

```mermaid
erDiagram
  users ||--o{ repositories : owns
  users ||--o{ stars : creates
  users ||--o{ chat_sessions : owns
  repositories ||--o{ analysis_jobs : has
  repositories ||--o{ source_files : has
  repositories ||--o{ stars : receives
  repositories ||--o{ chat_sessions : context
  source_files ||--o{ symbols : declares
  source_files ||--|| metrics : measured_by
  source_files ||--o{ dependencies : from
  source_files ||--o{ dependencies : to
  chat_sessions ||--o{ chat_messages : contains
```

## Tables

### `users`
GitHub-authenticated accounts.
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| github_id | BIGINT | no | UNIQUE, INDEX — stable account id |
| username | VARCHAR(255) | no | INDEX |
| display_name | VARCHAR(255) | yes | |
| email | VARCHAR(320) | yes | may be private |
| avatar_url | VARCHAR(1024) | yes | |
| created_at / updated_at | TIMESTAMPTZ | no | |

### `repositories`
A submitted repo + its analysis status and cached stats.
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| owner_id | UUID | yes | FK→users CASCADE, INDEX |
| is_public | BOOL | no | default false |
| url | VARCHAR(2048) | no | INDEX, canonical HTTPS |
| branch / default_branch | VARCHAR(255) | yes | |
| name | VARCHAR(255) | no | |
| owner | VARCHAR(255) | no | INDEX |
| status | ENUM repository_status | no | PENDING/CLONING/ANALYZING/READY/FAILED, INDEX |
| error_message | VARCHAR(2048) | yes | |
| analyzed_at | TIMESTAMPTZ | yes | |
| commit_hash | VARCHAR(40) | yes | last analyzed SHA |
| analysis_version / pipeline_version / schema_version | INT | yes | freshness stamps |
| embedding_model | VARCHAR(255) | yes | "provider:model" |
| file_count / total_lines | INT | no | cached |
| languages | VARCHAR(512) | yes | JSON map |
| star_count | INT | no | denormalized, INDEX |

**Unique:** `uq_repositories_owner_id_url_branch(owner_id, url, branch)`.

### `analysis_jobs`
One row per analysis run.
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| repository_id | UUID | no | FK→repositories CASCADE, INDEX |
| status | ENUM analysis_job_status | no | QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED, INDEX |
| rq_job_id | VARCHAR(64) | yes | INDEX |
| error | VARCHAR(4096) | yes | |
| queued_at / started_at / completed_at | TIMESTAMPTZ | | |
| heartbeat_at | TIMESTAMPTZ | yes | reaper liveness signal |
| progress | INT | no | 0..100 |
| progress_message | VARCHAR(512) | yes | |

**Partial unique:** `uq_active_job_per_repository(repository_id, status) WHERE status IN
('queued','running')` — at most one active job per repo (prevents duplicate analyses).

### `source_files`
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| repository_id | UUID | no | FK→repositories CASCADE, INDEX |
| path | VARCHAR(1024) | no | |
| language | VARCHAR(32) | no | INDEX |
| line_count | INT | no | |
| size_bytes | BIGINT | no | |
| sha256 | VARCHAR(64) | yes | |

**Unique:** `uq_source_files_repo_path(repository_id, path)`.

### `symbols`
Declared functions/classes/etc. per file.
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| file_id | UUID | no | FK→source_files CASCADE, INDEX |
| name | VARCHAR(512) | no | |
| qualified_name | VARCHAR(1024) | yes | |
| kind | ENUM symbol_kind | no | function/method/class/interface/struct/enum/variable/constant/type_alias/module |
| line_start / line_end | INT | no | |
| is_exported | BOOL | no | |
| is_used | BOOL | no | INDEX (dead-code) |
| usage_count | INT | no | |

**Indexes:** `ix_symbols_file_kind(file_id, kind)`, `ix_symbols_name(name)`.

### `dependencies`
Edges between files.
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| from_file_id | UUID | no | FK→source_files CASCADE |
| to_file_id | UUID | no | FK→source_files CASCADE |
| kind | ENUM dependency_kind | no | import/inheritance/call/instantiation/reference |
| symbol | VARCHAR(512) | yes | |
| line | INT | yes | |

**Unique:** `uq_dependencies_edge(from_file_id, to_file_id, kind, symbol)`.
**Indexes:** `ix_dependencies_from`, `ix_dependencies_to`.

> Note: today the analyzers emit file-level `import` edges (no per-function `call`/`reference`
> edges in practice). The schema is ready for richer edges.

### `metrics`
One row per file (1:1).
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| file_id | UUID | no | FK→source_files CASCADE, **UNIQUE**, INDEX |
| cyclomatic / cognitive / lines_of_code / function_count / class_count | INT | no | |
| dead_code_score | NUMERIC(4,3) | no | 0..1 |

**Indexes:** `ix_metrics_cyclomatic`, `ix_metrics_dead_code_score`.

### `stars`
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| user_id | UUID | no | FK→users CASCADE, INDEX |
| repository_id | UUID | no | FK→repositories CASCADE, INDEX |

**Unique:** `uq_stars_user_repository(user_id, repository_id)`.

### `chat_sessions`
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| user_id | UUID | no | FK→users CASCADE, INDEX |
| repository_id | UUID | no | FK→repositories CASCADE |
| title | VARCHAR(200) | no | default "New chat" |
| last_activity_at | TIMESTAMPTZ | no | bumped on new message, not rename |

**Index:** `ix_chat_sessions_user_repo_activity(user_id, repository_id, last_activity_at)`.

### `chat_messages`
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| id | UUID | no | PK |
| session_id | UUID | no | FK→chat_sessions CASCADE, INDEX |
| role | VARCHAR(16) | no | "user" / "assistant" |
| content | TEXT | no | |
| citations | JSONB | yes | `[{file_path,line_start,line_end,symbol?,snippet}]` |
| attached_context | JSONB | yes | `[{path,language?}]` (user turns) |

## Why these choices
- **UUID PKs** — globally unique, safe to expose in URLs, no sequence contention.
- **Cascade deletes** — deleting a repo cleanly removes files→symbols→metrics→deps and
  sessions→messages; deleting a user removes their repos and stars.
- **Denormalized `star_count`** — avoids a COUNT on every list render; kept correct by
  `StarService`.
- **JSONB for citations/context** — flexible, queryable-if-needed message metadata without
  extra tables.
- **Partial unique index** — enforces the "one active job" invariant in the database, not
  just app code.

Data lifecycle and query patterns: [data-lifecycle.md](data-lifecycle.md). Migration
history: [migrations.md](migrations.md).
