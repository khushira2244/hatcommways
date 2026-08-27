CREATE TABLE IF NOT EXISTS events (
    id uuid PRIMARY KEY,
    organizer_id uuid NOT NULL,
    name varchar(200) NOT NULL CHECK (length(btrim(name)) > 0),
    purpose varchar(4000) NOT NULL CHECK (length(btrim(purpose)) > 0),
    event_type varchar(100) NOT NULL CHECK (length(btrim(event_type)) > 0),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    timezone varchar(100) NOT NULL CHECK (length(btrim(timezone)) > 0),
    location_description varchar(500) NOT NULL CHECK (length(btrim(location_description)) > 0),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS proposals (
    id uuid PRIMARY KEY,
    proposal_type varchar(100) NOT NULL,
    target_type varchar(100) NOT NULL,
    target_id uuid NOT NULL,
    created_by varchar(200) NOT NULL,
    base_versions jsonb NOT NULL,
    payload jsonb NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'STALE')),
    idempotency_key varchar(200) NOT NULL UNIQUE,
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    decided_at timestamptz,
    CHECK (jsonb_typeof(base_versions) = 'object'),
    CHECK (jsonb_typeof(payload) = 'object')
);

CREATE TABLE IF NOT EXISTS proposal_decisions (
    id uuid PRIMARY KEY,
    proposal_id uuid NOT NULL UNIQUE REFERENCES proposals(id),
    organizer_id uuid NOT NULL,
    decision varchar(20) NOT NULL CHECK (decision IN ('APPROVE', 'REJECT')),
    decision_idempotency_key varchar(200) NOT NULL UNIQUE,
    applied_event_id uuid REFERENCES events(id),
    applied_event_version integer,
    application_result jsonb,
    decided_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE proposal_decisions
    ADD COLUMN IF NOT EXISTS application_result jsonb;

CREATE TABLE IF NOT EXISTS event_planning_requests (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    organizer_id uuid NOT NULL,
    base_event_version integer NOT NULL CHECK (base_event_version > 0),
    status varchar(20) NOT NULL
        CHECK (status IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    idempotency_key varchar(200) NOT NULL UNIQUE,
    correlation_id uuid NOT NULL,
    proposal_id uuid REFERENCES proposals(id),
    failure_code varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stages (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    canonical_name varchar(200) NOT NULL CHECK (length(btrim(canonical_name)) > 0),
    purpose varchar(2000) NOT NULL CHECK (length(btrim(purpose)) > 0),
    stage_order integer NOT NULL CHECK (stage_order > 0),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    source_proposal_id uuid NOT NULL REFERENCES proposals(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, stage_order),
    CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS stage_dependencies (
    stage_id uuid NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
    depends_on_stage_id uuid NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
    PRIMARY KEY (stage_id, depends_on_stage_id),
    CHECK (stage_id <> depends_on_stage_id)
);

CREATE TABLE IF NOT EXISTS work_design_requests (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    stage_id uuid NOT NULL REFERENCES stages(id),
    organizer_id uuid NOT NULL,
    base_event_version integer NOT NULL CHECK (base_event_version > 0),
    base_stage_version integer NOT NULL CHECK (base_stage_version > 0),
    status varchar(20) NOT NULL
        CHECK (status IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    idempotency_key varchar(200) NOT NULL UNIQUE,
    correlation_id uuid NOT NULL,
    proposal_id uuid REFERENCES proposals(id),
    failure_code varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS work_items (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    stage_id uuid NOT NULL REFERENCES stages(id),
    canonical_name varchar(200) NOT NULL CHECK (length(btrim(canonical_name)) > 0),
    purpose varchar(2000) NOT NULL CHECK (length(btrim(purpose)) > 0),
    work_order integer NOT NULL CHECK (work_order > 0),
    estimated_person_hours numeric(12,2) NOT NULL CHECK (estimated_person_hours > 0),
    work_share numeric(7,4) NOT NULL CHECK (work_share > 0 AND work_share <= 100),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    source_proposal_id uuid NOT NULL REFERENCES proposals(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (stage_id, work_order),
    CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS work_dependencies (
    work_id uuid NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    depends_on_work_id uuid NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    PRIMARY KEY (work_id, depends_on_work_id),
    CHECK (work_id <> depends_on_work_id)
);

CREATE TABLE IF NOT EXISTS domain_outbox (
    id uuid PRIMARY KEY,
    event_type varchar(200) NOT NULL,
    aggregate_type varchar(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    aggregate_version integer NOT NULL CHECK (aggregate_version > 0),
    payload jsonb NOT NULL,
    correlation_id uuid NOT NULL,
    causation_id uuid,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    CHECK (jsonb_typeof(payload) = 'object')
);

CREATE INDEX IF NOT EXISTS domain_outbox_unpublished_idx
    ON domain_outbox (occurred_at)
    WHERE published_at IS NULL;
