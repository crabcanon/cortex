-- Cortex metadata bootstrap schema
-- Design targets:
-- 1. Standard SQL-friendly DDL with app-generated string IDs.
-- 2. S3-compatible object storage metadata kept outside provider-specific features.
-- 3. Relational metadata as the portability layer across SQLite, PostgreSQL, and similar engines.
-- 4. JSON payloads are stored as UTF-8 TEXT to avoid vendor lock-in on JSON column types.

BEGIN TRANSACTION;

CREATE TABLE tenants (
    tenant_id            VARCHAR(36)  PRIMARY KEY,
    tenant_key           VARCHAR(128) NOT NULL UNIQUE,
    display_name         VARCHAR(255) NOT NULL,
    status               VARCHAR(32)  NOT NULL,
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE actors (
    actor_id             VARCHAR(36)  PRIMARY KEY,
    tenant_id            VARCHAR(36)  NOT NULL,
    actor_type           VARCHAR(32)  NOT NULL,
    actor_ref            VARCHAR(255) NOT NULL,
    display_name         VARCHAR(255),
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, actor_type, actor_ref),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
);

CREATE TABLE permissions (
    permission_key       VARCHAR(128) PRIMARY KEY,
    permission_kind      VARCHAR(32)  NOT NULL,
    resource_type        VARCHAR(64)  NOT NULL,
    action_name          VARCHAR(64)  NOT NULL,
    description          TEXT,
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    role_id              VARCHAR(36)  PRIMARY KEY,
    tenant_id            VARCHAR(36)  NOT NULL,
    role_key             VARCHAR(128) NOT NULL,
    display_name         VARCHAR(255) NOT NULL,
    scope_level          VARCHAR(32)  NOT NULL,
    is_builtin           BOOLEAN      NOT NULL DEFAULT FALSE,
    description          TEXT,
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_by           VARCHAR(36),
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, role_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE role_permissions (
    role_id              VARCHAR(36)  NOT NULL,
    permission_key       VARCHAR(128) NOT NULL,
    effect               VARCHAR(16)  NOT NULL DEFAULT 'allow',
    condition_json       TEXT         NOT NULL DEFAULT '{}',
    PRIMARY KEY (role_id, permission_key),
    FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_key) REFERENCES permissions (permission_key)
);

CREATE TABLE actor_role_bindings (
    binding_id           VARCHAR(36)  PRIMARY KEY,
    tenant_id            VARCHAR(36)  NOT NULL,
    actor_id             VARCHAR(36)  NOT NULL,
    role_id              VARCHAR(36)  NOT NULL,
    binding_scope        VARCHAR(32)  NOT NULL DEFAULT 'tenant',
    resource_type        VARCHAR(64),
    resource_id          VARCHAR(64),
    expires_at           TIMESTAMP,
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_by           VARCHAR(36),
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, actor_id, role_id, binding_scope, resource_type, resource_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (actor_id) REFERENCES actors (actor_id),
    FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE authorization_policies (
    policy_id               VARCHAR(36)  PRIMARY KEY,
    tenant_id               VARCHAR(36)  NOT NULL,
    policy_key              VARCHAR(128) NOT NULL,
    effect                  VARCHAR(16)  NOT NULL,
    priority                INTEGER      NOT NULL DEFAULT 100,
    status                  VARCHAR(32)  NOT NULL,
    subject_selector_json   TEXT         NOT NULL DEFAULT '{}',
    resource_selector_json  TEXT         NOT NULL DEFAULT '{}',
    condition_json          TEXT         NOT NULL DEFAULT '{}',
    description             TEXT,
    metadata_json           TEXT         NOT NULL DEFAULT '{}',
    created_by              VARCHAR(36),
    created_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, policy_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE authorization_decisions (
    decision_id          VARCHAR(36)  PRIMARY KEY,
    tenant_id            VARCHAR(36)  NOT NULL,
    actor_id             VARCHAR(36)  NOT NULL,
    permission_key       VARCHAR(128) NOT NULL,
    resource_type        VARCHAR(64),
    resource_id          VARCHAR(64),
    effect               VARCHAR(16)  NOT NULL,
    reason_code          VARCHAR(128) NOT NULL,
    policy_id            VARCHAR(36),
    trace_id             VARCHAR(64),
    request_id           VARCHAR(128),
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (actor_id) REFERENCES actors (actor_id),
    FOREIGN KEY (permission_key) REFERENCES permissions (permission_key),
    FOREIGN KEY (policy_id) REFERENCES authorization_policies (policy_id)
);

CREATE TABLE storage_buckets (
    bucket_id            VARCHAR(36)  PRIMARY KEY,
    tenant_id            VARCHAR(36)  NOT NULL,
    bucket_name          VARCHAR(255) NOT NULL,
    endpoint_url         VARCHAR(2048),
    region_name          VARCHAR(128),
    provider_hint        VARCHAR(64),
    is_default           BOOLEAN      NOT NULL DEFAULT FALSE,
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, bucket_name),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
);

CREATE TABLE objects (
    object_id            VARCHAR(36)  PRIMARY KEY,
    tenant_id            VARCHAR(36)  NOT NULL,
    bucket_id            VARCHAR(36)  NOT NULL,
    object_key           VARCHAR(1024) NOT NULL,
    filename             VARCHAR(512) NOT NULL,
    content_type         VARCHAR(255) NOT NULL,
    size_bytes           BIGINT       NOT NULL,
    checksum_sha256      CHAR(64),
    etag                 VARCHAR(255),
    storage_class        VARCHAR(64),
    source_uri           VARCHAR(2048),
    access_level         VARCHAR(32)  NOT NULL DEFAULT 'tenant_private',
    access_policy_json   TEXT         NOT NULL DEFAULT '{}',
    status               VARCHAR(32)  NOT NULL,
    metadata_json        TEXT         NOT NULL DEFAULT '{}',
    created_by           VARCHAR(36),
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (bucket_id, object_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (bucket_id) REFERENCES storage_buckets (bucket_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE object_versions (
    object_version_id    VARCHAR(36)  PRIMARY KEY,
    object_id            VARCHAR(36)  NOT NULL,
    version_no           INTEGER      NOT NULL,
    provider_version_ref VARCHAR(255),
    size_bytes           BIGINT       NOT NULL,
    checksum_sha256      CHAR(64),
    etag                 VARCHAR(255),
    is_latest            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (object_id, version_no),
    FOREIGN KEY (object_id) REFERENCES objects (object_id) ON DELETE CASCADE
);

CREATE TABLE parser_engines (
    engine_id               VARCHAR(36)  PRIMARY KEY,
    engine_key              VARCHAR(128) NOT NULL UNIQUE,
    display_name            VARCHAR(255) NOT NULL,
    engine_family           VARCHAR(64)  NOT NULL,
    deployment_mode         VARCHAR(32)  NOT NULL,
    status                  VARCHAR(32)  NOT NULL,
    supported_source_types_json TEXT     NOT NULL DEFAULT '[]',
    supported_formats_json  TEXT         NOT NULL DEFAULT '[]',
    capability_flags_json   TEXT         NOT NULL DEFAULT '[]',
    config_schema_json      TEXT         NOT NULL DEFAULT '{}',
    metadata_json           TEXT         NOT NULL DEFAULT '{}',
    created_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE parser_profiles (
    profile_id              VARCHAR(36)  PRIMARY KEY,
    tenant_id               VARCHAR(36)  NOT NULL,
    profile_key             VARCHAR(128) NOT NULL,
    display_name            VARCHAR(255) NOT NULL,
    description             TEXT,
    routing_mode            VARCHAR(32)  NOT NULL,
    preferred_engine_id     VARCHAR(36),
    allowed_engines_json    TEXT         NOT NULL DEFAULT '[]',
    source_constraints_json TEXT         NOT NULL DEFAULT '{}',
    normalization_json      TEXT         NOT NULL DEFAULT '{}',
    fallback_policy_json    TEXT         NOT NULL DEFAULT '{}',
    engine_overrides_json   TEXT         NOT NULL DEFAULT '{}',
    metadata_json           TEXT         NOT NULL DEFAULT '{}',
    created_by              VARCHAR(36),
    created_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, profile_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (preferred_engine_id) REFERENCES parser_engines (engine_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE crawl_sessions (
    session_id               VARCHAR(36)  PRIMARY KEY,
    tenant_id                VARCHAR(36)  NOT NULL,
    session_key              VARCHAR(255) NOT NULL,
    storage_state_object_id  VARCHAR(36),
    browser_profile_json     TEXT         NOT NULL DEFAULT '{}',
    expires_at               TIMESTAMP,
    last_used_at             TIMESTAMP,
    created_by               VARCHAR(36),
    created_at               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, session_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (storage_state_object_id) REFERENCES objects (object_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE documents (
    document_id           VARCHAR(36)  PRIMARY KEY,
    tenant_id             VARCHAR(36)  NOT NULL,
    source_type           VARCHAR(32)  NOT NULL,
    source_uri            VARCHAR(2048),
    canonical_url         VARCHAR(2048),
    source_object_id      VARCHAR(36),
    title                 VARCHAR(1024),
    language_code         VARCHAR(32),
    source_format         VARCHAR(128) NOT NULL,
    detected_mime_type    VARCHAR(255),
    content_hash_sha256   CHAR(64),
    access_level          VARCHAR(32)  NOT NULL DEFAULT 'tenant_private',
    access_policy_json    TEXT         NOT NULL DEFAULT '{}',
    status                VARCHAR(32)  NOT NULL,
    metadata_json         TEXT         NOT NULL DEFAULT '{}',
    audit_json            TEXT         NOT NULL DEFAULT '{}',
    published_at          TIMESTAMP,
    created_by            VARCHAR(36),
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (source_object_id) REFERENCES objects (object_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE document_artifacts (
    document_id           VARCHAR(36)  NOT NULL,
    artifact_type         VARCHAR(64)  NOT NULL,
    object_id             VARCHAR(36),
    artifact_ref          VARCHAR(255),
    metadata_json         TEXT         NOT NULL DEFAULT '{}',
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, artifact_type),
    FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE CASCADE,
    FOREIGN KEY (object_id) REFERENCES objects (object_id)
);

CREATE TABLE document_tags (
    document_id           VARCHAR(36)  NOT NULL,
    tag                   VARCHAR(128) NOT NULL,
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, tag),
    FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE CASCADE
);

CREATE TABLE document_chunks (
    chunk_id              VARCHAR(36)  PRIMARY KEY,
    document_id           VARCHAR(36)  NOT NULL,
    chunk_index           INTEGER      NOT NULL,
    heading_path          VARCHAR(1024),
    token_count           INTEGER      NOT NULL DEFAULT 0,
    char_count            INTEGER      NOT NULL DEFAULT 0,
    checksum_sha256       CHAR(64),
    chunk_text            TEXT         NOT NULL,
    metadata_json         TEXT         NOT NULL DEFAULT '{}',
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE CASCADE
);

CREATE TABLE datasets (
    dataset_id            VARCHAR(36)  PRIMARY KEY,
    tenant_id             VARCHAR(36)  NOT NULL,
    dataset_key           VARCHAR(128) NOT NULL,
    display_name          VARCHAR(255) NOT NULL,
    description           TEXT,
    retention_class       VARCHAR(64)  NOT NULL DEFAULT 'standard',
    access_level          VARCHAR(32)  NOT NULL DEFAULT 'tenant_private',
    access_policy_json    TEXT         NOT NULL DEFAULT '{}',
    status                VARCHAR(32)  NOT NULL,
    metadata_json         TEXT         NOT NULL DEFAULT '{}',
    created_by            VARCHAR(36),
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, dataset_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE dataset_items (
    dataset_id            VARCHAR(36)  NOT NULL,
    item_type             VARCHAR(32)  NOT NULL,
    item_id               VARCHAR(36)  NOT NULL,
    source_stage          VARCHAR(32)  NOT NULL,
    label                 VARCHAR(255),
    metadata_json         TEXT         NOT NULL DEFAULT '{}',
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dataset_id, item_type, item_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE
);

CREATE TABLE jobs (
    job_id                VARCHAR(36)  PRIMARY KEY,
    tenant_id             VARCHAR(36)  NOT NULL,
    job_type              VARCHAR(64)  NOT NULL,
    operation_name        VARCHAR(64)  NOT NULL,
    status                VARCHAR(32)  NOT NULL,
    priority              INTEGER      NOT NULL DEFAULT 5,
    idempotency_key       VARCHAR(255),
    target_type           VARCHAR(64),
    target_id             VARCHAR(36),
    correlation_id        VARCHAR(128),
    trace_id              VARCHAR(64),
    span_id               VARCHAR(32),
    request_json          TEXT         NOT NULL DEFAULT '{}',
    result_json           TEXT         NOT NULL DEFAULT '{}',
    telemetry_context_json TEXT        NOT NULL DEFAULT '{}',
    deployment_context_json TEXT       NOT NULL DEFAULT '{}',
    experiment_context_json TEXT       NOT NULL DEFAULT '{}',
    error_code            VARCHAR(128),
    error_message         TEXT,
    submitted_by          VARCHAR(36),
    submitted_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at            TIMESTAMP,
    heartbeat_at          TIMESTAMP,
    completed_at          TIMESTAMP,
    UNIQUE (tenant_id, job_type, idempotency_key),
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (submitted_by) REFERENCES actors (actor_id)
);

CREATE TABLE job_events (
    job_id                VARCHAR(36)  NOT NULL,
    sequence_no           INTEGER      NOT NULL,
    level                 VARCHAR(16)  NOT NULL,
    event_type            VARCHAR(128) NOT NULL,
    trace_id              VARCHAR(64),
    span_id               VARCHAR(32),
    message               TEXT,
    details_json          TEXT         NOT NULL DEFAULT '{}',
    event_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id, sequence_no),
    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE
);

CREATE TABLE parse_runs (
    parse_run_id          VARCHAR(36)  PRIMARY KEY,
    job_id                VARCHAR(36)  NOT NULL UNIQUE,
    source_kind           VARCHAR(32)  NOT NULL,
    parser_profile_id     VARCHAR(36),
    selected_engine_id    VARCHAR(36),
    trace_id              VARCHAR(64),
    document_id           VARCHAR(36),
    source_url            VARCHAR(2048),
    source_ref            VARCHAR(2048),
    selection_policy_json TEXT         NOT NULL DEFAULT '{}',
    crawl_profile_json    TEXT         NOT NULL DEFAULT '{}',
    normalization_json    TEXT         NOT NULL DEFAULT '{}',
    output_profile_json   TEXT         NOT NULL DEFAULT '{}',
    fallback_chain_json   TEXT         NOT NULL DEFAULT '[]',
    diagnostics_json      TEXT         NOT NULL DEFAULT '{}',
    telemetry_context_json TEXT        NOT NULL DEFAULT '{}',
    deployment_context_json TEXT       NOT NULL DEFAULT '{}',
    experiment_context_json TEXT       NOT NULL DEFAULT '{}',
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE,
    FOREIGN KEY (parser_profile_id) REFERENCES parser_profiles (profile_id),
    FOREIGN KEY (selected_engine_id) REFERENCES parser_engines (engine_id),
    FOREIGN KEY (document_id) REFERENCES documents (document_id)
);

CREATE TABLE parse_run_attempts (
    parse_run_id          VARCHAR(36)  NOT NULL,
    attempt_no            INTEGER      NOT NULL,
    engine_id             VARCHAR(36)  NOT NULL,
    status                VARCHAR(32)  NOT NULL,
    trace_id              VARCHAR(64),
    span_id               VARCHAR(32),
    engine_request_json   TEXT         NOT NULL DEFAULT '{}',
    engine_result_json    TEXT         NOT NULL DEFAULT '{}',
    diagnostics_json      TEXT         NOT NULL DEFAULT '{}',
    started_at            TIMESTAMP,
    completed_at          TIMESTAMP,
    error_code            VARCHAR(128),
    error_message         TEXT,
    PRIMARY KEY (parse_run_id, attempt_no),
    FOREIGN KEY (parse_run_id) REFERENCES parse_runs (parse_run_id) ON DELETE CASCADE,
    FOREIGN KEY (engine_id) REFERENCES parser_engines (engine_id)
);

CREATE TABLE knowledge_runs (
    knowledge_run_id      VARCHAR(36)  PRIMARY KEY,
    job_id                VARCHAR(36)  NOT NULL UNIQUE,
    dataset_id            VARCHAR(36)  NOT NULL,
    operation_name        VARCHAR(64)  NOT NULL,
    trace_id              VARCHAR(64),
    request_json          TEXT         NOT NULL DEFAULT '{}',
    result_summary_json   TEXT         NOT NULL DEFAULT '{}',
    telemetry_context_json TEXT        NOT NULL DEFAULT '{}',
    deployment_context_json TEXT       NOT NULL DEFAULT '{}',
    experiment_context_json TEXT       NOT NULL DEFAULT '{}',
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id)
);

CREATE TABLE search_requests (
    request_id            VARCHAR(36)  PRIMARY KEY,
    tenant_id             VARCHAR(36)  NOT NULL,
    dataset_scope_json    TEXT         NOT NULL DEFAULT '[]',
    session_id            VARCHAR(64),
    search_type           VARCHAR(64)  NOT NULL,
    trace_id              VARCHAR(64),
    span_id               VARCHAR(32),
    query_text            TEXT         NOT NULL,
    filters_json          TEXT         NOT NULL DEFAULT '{}',
    options_json          TEXT         NOT NULL DEFAULT '{}',
    answer_text           TEXT,
    latency_ms            INTEGER,
    telemetry_context_json TEXT        NOT NULL DEFAULT '{}',
    deployment_context_json TEXT       NOT NULL DEFAULT '{}',
    experiment_context_json TEXT       NOT NULL DEFAULT '{}',
    created_by            VARCHAR(36),
    created_at            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
    FOREIGN KEY (created_by) REFERENCES actors (actor_id)
);

CREATE TABLE search_hits (
    request_id            VARCHAR(36)  NOT NULL,
    hit_index             INTEGER      NOT NULL,
    hit_type              VARCHAR(32)  NOT NULL,
    source_id             VARCHAR(36),
    document_id           VARCHAR(36),
    object_id             VARCHAR(36),
    score                 DECIMAL(12, 6),
    title                 VARCHAR(1024),
    snippet               TEXT,
    citation_json         TEXT         NOT NULL DEFAULT '{}',
    metadata_json         TEXT         NOT NULL DEFAULT '{}',
    PRIMARY KEY (request_id, hit_index),
    FOREIGN KEY (request_id) REFERENCES search_requests (request_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents (document_id),
    FOREIGN KEY (object_id) REFERENCES objects (object_id)
);

CREATE INDEX idx_actors_tenant_ref
    ON actors (tenant_id, actor_ref);

CREATE INDEX idx_objects_tenant_created_at
    ON objects (tenant_id, created_at);

CREATE INDEX idx_objects_checksum
    ON objects (checksum_sha256);

CREATE INDEX idx_documents_tenant_status
    ON documents (tenant_id, status);

CREATE INDEX idx_documents_source_uri
    ON documents (source_uri);

CREATE INDEX idx_document_chunks_document
    ON document_chunks (document_id, chunk_index);

CREATE INDEX idx_parser_profiles_tenant_key
    ON parser_profiles (tenant_id, profile_key);

CREATE INDEX idx_roles_tenant_role_key
    ON roles (tenant_id, role_key);

CREATE INDEX idx_actor_role_bindings_actor_scope
    ON actor_role_bindings (actor_id, tenant_id, binding_scope);

CREATE INDEX idx_actor_role_bindings_resource
    ON actor_role_bindings (resource_type, resource_id);

CREATE INDEX idx_authorization_policies_tenant_status
    ON authorization_policies (tenant_id, status, priority);

CREATE INDEX idx_authorization_decisions_trace_id
    ON authorization_decisions (trace_id, created_at);

CREATE INDEX idx_authorization_decisions_actor_created_at
    ON authorization_decisions (actor_id, created_at);

CREATE INDEX idx_dataset_items_item
    ON dataset_items (item_type, item_id);

CREATE INDEX idx_objects_tenant_access_level
    ON objects (tenant_id, access_level, created_at);

CREATE INDEX idx_documents_tenant_access_level
    ON documents (tenant_id, access_level, created_at);

CREATE INDEX idx_datasets_tenant_access_level
    ON datasets (tenant_id, access_level, created_at);

CREATE INDEX idx_jobs_tenant_status
    ON jobs (tenant_id, status, submitted_at);

CREATE INDEX idx_jobs_target
    ON jobs (target_type, target_id);

CREATE INDEX idx_jobs_trace_id
    ON jobs (trace_id);

CREATE INDEX idx_job_events_trace_id
    ON job_events (trace_id, event_at);

CREATE INDEX idx_knowledge_runs_dataset
    ON knowledge_runs (dataset_id, operation_name);

CREATE INDEX idx_search_requests_tenant_created_at
    ON search_requests (tenant_id, created_at);

CREATE INDEX idx_search_requests_trace_id
    ON search_requests (trace_id, created_at);

CREATE INDEX idx_parse_runs_profile_engine
    ON parse_runs (parser_profile_id, selected_engine_id);

CREATE INDEX idx_parse_runs_trace_id
    ON parse_runs (trace_id, created_at);

CREATE INDEX idx_parse_run_attempts_engine
    ON parse_run_attempts (engine_id, status);

COMMIT;
