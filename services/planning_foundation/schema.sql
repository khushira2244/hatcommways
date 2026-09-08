CREATE TABLE IF NOT EXISTS accounts (
    id uuid PRIMARY KEY,
    email varchar(320) NOT NULL UNIQUE,
    display_name varchar(200) NOT NULL CHECK (length(btrim(display_name)) > 0),
    account_type varchar(20) NOT NULL
        CHECK (account_type IN ('INDIVIDUAL', 'ORGANIZATION')),
    status varchar(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'DISABLED')),
    password_hash text NOT NULL CHECK (length(password_hash) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (email = lower(btrim(email)))
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    token_hash char(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    CHECK (expires_at > created_at)
);

CREATE TABLE IF NOT EXISTS events (
    id uuid PRIMARY KEY,
    organizer_id uuid NOT NULL,
    name varchar(200) NOT NULL CHECK (length(btrim(name)) > 0),
    category varchar(100),
    purpose varchar(4000) NOT NULL CHECK (length(btrim(purpose)) > 0),
    event_type varchar(100) NOT NULL CHECK (length(btrim(event_type)) > 0),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    timezone varchar(100) NOT NULL CHECK (length(btrim(timezone)) > 0),
    location_description varchar(500) NOT NULL CHECK (length(btrim(location_description)) > 0),
    planning_context jsonb,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    CHECK (planning_context IS NULL OR jsonb_typeof(planning_context) = 'object')
);

ALTER TABLE events ADD COLUMN IF NOT EXISTS planning_context jsonb;
ALTER TABLE events ADD COLUMN IF NOT EXISTS category varchar(100);

CREATE TABLE IF NOT EXISTS event_creation_drafts (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name varchar(200) NOT NULL DEFAULT 'Untitled event',
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    current_step integer NOT NULL CHECK (current_step BETWEEN 1 AND 4),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE event_creation_drafts ADD COLUMN IF NOT EXISTS name varchar(200) NOT NULL DEFAULT 'Untitled event';

CREATE INDEX IF NOT EXISTS event_creation_drafts_account_idx
    ON event_creation_drafts (account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS event_memberships (
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role varchar(40) NOT NULL CHECK (
        role IN (
            'ORGANIZER', 'ACTOR', 'WATCHER', 'SUPPORTER',
            'RESOURCE_CONTRIBUTOR', 'SPONSOR', 'SUPPORT_PARTNER'
        )
    ),
    status varchar(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, account_id, role)
);

CREATE UNIQUE INDEX IF NOT EXISTS event_one_active_organizer_idx
    ON event_memberships (event_id)
    WHERE role = 'ORGANIZER' AND status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS event_setups (
    event_id uuid PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    initial_invites jsonb NOT NULL DEFAULT '[]'::jsonb,
    sponsors_support jsonb NOT NULL DEFAULT '[]'::jsonb,
    resource_needs jsonb NOT NULL DEFAULT '[]'::jsonb,
    contribution_links jsonb NOT NULL DEFAULT '[]'::jsonb,
    map_enabled boolean NOT NULL DEFAULT false,
    default_view varchar(100),
    participation_dimensions jsonb NOT NULL DEFAULT '[]'::jsonb,
    event_visibility varchar(20) NOT NULL DEFAULT 'PRIVATE'
        CHECK (event_visibility IN ('PUBLIC', 'UNLISTED', 'PRIVATE')),
    show_participant_counts boolean NOT NULL DEFAULT false,
    show_actor_tree boolean NOT NULL DEFAULT false,
    show_sponsors boolean NOT NULL DEFAULT false,
    show_resources boolean NOT NULL DEFAULT false,
    show_payment_links boolean NOT NULL DEFAULT false,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(initial_invites) = 'array'),
    CHECK (jsonb_typeof(sponsors_support) = 'array'),
    CHECK (jsonb_typeof(resource_needs) = 'array'),
    CHECK (jsonb_typeof(contribution_links) = 'array'),
    CHECK (jsonb_typeof(participation_dimensions) = 'array')
);

CREATE TABLE IF NOT EXISTS event_setup_updates (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    organizer_id uuid NOT NULL,
    idempotency_key varchar(200) NOT NULL UNIQUE,
    request_fingerprint char(64) NOT NULL,
    applied_version integer NOT NULL CHECK (applied_version > 0),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
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

CREATE TABLE IF NOT EXISTS event_resume_states (
    event_id uuid PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    current_phase varchar(40) NOT NULL CHECK (current_phase IN (
        'GOVERNANCE','STAGE_PLANNING','WORK_DESIGN','ACTOR_REQUIREMENTS','EVENT_SETUP','READY','PUBLISHED'
    )),
    last_open_stage_id uuid REFERENCES stages(id) ON DELETE SET NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
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

CREATE TABLE IF NOT EXISTS actor_requirement_requests (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    stage_id uuid NOT NULL REFERENCES stages(id),
    work_id uuid NOT NULL REFERENCES work_items(id),
    organizer_id uuid NOT NULL,
    base_event_version integer NOT NULL CHECK (base_event_version > 0),
    base_stage_version integer NOT NULL CHECK (base_stage_version > 0),
    base_work_version integer NOT NULL CHECK (base_work_version > 0),
    status varchar(20) NOT NULL
        CHECK (status IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    idempotency_key varchar(200) NOT NULL UNIQUE,
    correlation_id uuid NOT NULL,
    proposal_id uuid REFERENCES proposals(id),
    failure_code varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS actor_requirements (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    stage_id uuid NOT NULL REFERENCES stages(id),
    work_id uuid NOT NULL REFERENCES work_items(id),
    role_category varchar(100) NOT NULL CHECK (length(btrim(role_category)) > 0),
    canonical_role_name varchar(200) NOT NULL
        CHECK (length(btrim(canonical_role_name)) > 0),
    responsibility_summary varchar(2000) NOT NULL
        CHECK (length(btrim(responsibility_summary)) > 0),
    minimum_required_count integer NOT NULL CHECK (minimum_required_count >= 0),
    relevant_capabilities jsonb NOT NULL DEFAULT '[]'::jsonb,
    rough_effort_expectation varchar(1000) NOT NULL
        CHECK (length(btrim(rough_effort_expectation)) > 0),
    rationale varchar(2000) NOT NULL CHECK (length(btrim(rationale)) > 0),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    source_proposal_id uuid NOT NULL REFERENCES proposals(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (work_id, role_category, canonical_role_name),
    CHECK (jsonb_typeof(relevant_capabilities) = 'array')
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

CREATE TABLE IF NOT EXISTS governance_assessments (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    governance_required boolean NOT NULL,
    completeness varchar(20) NOT NULL CHECK (completeness IN ('NOT_REQUIRED','COMPLETE','INCOMPLETE')),
    internal_risk varchar(10) NOT NULL CHECK (internal_risk IN ('LOW','MEDIUM','HIGH')),
    review_mode varchar(20) NOT NULL CHECK (review_mode IN ('NONE','ORGANIZER','HATCOMMWAYS')),
    organizer_visible_status varchar(30) NOT NULL CHECK (organizer_visible_status IN ('NOT_REQUIRED','NEEDS_INFORMATION','EVIDENCE_REQUESTED','SUBMITTED','UNDER_REVIEW','CLEARED')),
    location_context text,
    event_facts_snapshot jsonb NOT NULL,
    reasoning_summary text NOT NULL,
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS governance_items (
    id uuid PRIMARY KEY, assessment_id uuid NOT NULL REFERENCES governance_assessments(id) ON DELETE CASCADE,
    category varchar(40) NOT NULL CHECK (category IN ('LOCATION_VENUE','PUBLIC_SPACE_PERMISSION','SAFETY_EMERGENCY','TRAFFIC_ACCESS','CROWD_CAPACITY','FOOD_VENDOR','MINORS_SUPERVISION','ANIMALS','EQUIPMENT_TEMPORARY_STRUCTURE','SOUND_NOISE','SPONSOR_COMMERCIAL','OTHER')),
    label varchar(200) NOT NULL, source varchar(30) NOT NULL CHECK (source IN ('AI_DETECTED','ORGANIZER_ADDED','HATCOMMWAYS_ADDED')),
    knowledge_type varchar(30) NOT NULL CHECK (knowledge_type IN ('VERIFIED_REQUIREMENT','COMMON_PRACTICE','AI_RISK_ADVISORY','UNKNOWN')),
    reason text, suggested_documents jsonb NOT NULL DEFAULT '[]'::jsonb,
    status varchar(30) NOT NULL CHECK (status IN ('NEEDS_INFORMATION','EVIDENCE_REQUESTED','PROVIDED','SUBMITTED','UNDER_REVIEW','CLEARED','NOT_APPLICABLE')),
    organizer_note text, reviewer_note text, blocking boolean NOT NULL DEFAULT false CHECK (blocking=false),
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS governance_evidence (
    id uuid PRIMARY KEY, governance_item_id uuid NOT NULL REFERENCES governance_items(id) ON DELETE CASCADE,
    evidence_type varchar(30) NOT NULL CHECK (evidence_type IN ('FILE','URL','REFERENCE_NUMBER','TEXT_CONFIRMATION')),
    label varchar(200) NOT NULL, value_or_reference text,
    original_filename varchar(255), content_type varchar(100), file_size bigint,
    storage_key varchar(500), note text,
    submitted_by uuid NOT NULL REFERENCES accounts(id), submitted_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((evidence_type='FILE' AND original_filename IS NOT NULL AND content_type IS NOT NULL AND file_size IS NOT NULL AND storage_key IS NOT NULL AND value_or_reference IS NULL) OR (evidence_type<>'FILE' AND value_or_reference IS NOT NULL AND original_filename IS NULL AND content_type IS NULL AND file_size IS NULL AND storage_key IS NULL))
);
ALTER TABLE governance_evidence DROP CONSTRAINT IF EXISTS governance_evidence_evidence_type_check;
ALTER TABLE governance_evidence ALTER COLUMN value_or_reference DROP NOT NULL;
ALTER TABLE governance_evidence ADD COLUMN IF NOT EXISTS original_filename varchar(255);
ALTER TABLE governance_evidence ADD COLUMN IF NOT EXISTS content_type varchar(100);
ALTER TABLE governance_evidence ADD COLUMN IF NOT EXISTS file_size bigint;
ALTER TABLE governance_evidence ADD COLUMN IF NOT EXISTS storage_key varchar(500);
ALTER TABLE governance_evidence ADD COLUMN IF NOT EXISTS note text;
UPDATE governance_evidence SET evidence_type='REFERENCE_NUMBER' WHERE evidence_type='FILE_REFERENCE';
ALTER TABLE governance_evidence ADD CONSTRAINT governance_evidence_evidence_type_check CHECK (evidence_type IN ('FILE','URL','REFERENCE_NUMBER','TEXT_CONFIRMATION'));
ALTER TABLE governance_evidence DROP CONSTRAINT IF EXISTS governance_evidence_shape_check;
ALTER TABLE governance_evidence ADD CONSTRAINT governance_evidence_shape_check CHECK ((evidence_type='FILE' AND original_filename IS NOT NULL AND content_type IS NOT NULL AND file_size IS NOT NULL AND storage_key IS NOT NULL AND value_or_reference IS NULL) OR (evidence_type<>'FILE' AND value_or_reference IS NOT NULL AND original_filename IS NULL AND content_type IS NULL AND file_size IS NULL AND storage_key IS NULL));
CREATE TABLE IF NOT EXISTS governance_tickets (
    id uuid PRIMARY KEY, event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    assessment_id uuid NOT NULL UNIQUE REFERENCES governance_assessments(id) ON DELETE CASCADE,
    ticket_number varchar(30) NOT NULL UNIQUE,
    status varchar(40) NOT NULL CHECK (status IN ('UNDER_REVIEW','MORE_INFORMATION_REQUESTED','CLEARED','NOT_APPLICABLE')),
    internal_risk varchar(10) NOT NULL CHECK (internal_risk IN ('LOW','MEDIUM','HIGH')),
    decision text, decision_reason text,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
