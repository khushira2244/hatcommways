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

CREATE TABLE IF NOT EXISTS participation_advisories (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    requester_account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    selections jsonb NOT NULL CHECK (jsonb_typeof(selections)='array'),
    availability jsonb NOT NULL CHECK (jsonb_typeof(availability)='object'),
    result jsonb NOT NULL CHECK (jsonb_typeof(result)='object'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS participation_requests (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    requester_account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    status varchar(40) NOT NULL CHECK (status IN ('PENDING','PARTIALLY_APPROVED','APPROVED','REJECTED','WITHDRAWN_BY_PARTICIPANT','REMOVED_BY_ORGANIZER')),
    note varchar(2000),
    advisory_id uuid NOT NULL REFERENCES participation_advisories(id),
    advisory_summary jsonb NOT NULL CHECK (jsonb_typeof(advisory_summary)='object'),
    idempotency_key varchar(200) NOT NULL UNIQUE,
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS participation_request_items (
    id uuid PRIMARY KEY,
    participation_request_id uuid NOT NULL REFERENCES participation_requests(id) ON DELETE CASCADE,
    stage_id uuid NOT NULL REFERENCES stages(id),
    work_id uuid NOT NULL REFERENCES work_items(id),
    actor_requirement_id uuid NOT NULL REFERENCES actor_requirements(id),
    preference varchar(30) NOT NULL CHECK (preference IN ('PREFERRED','CAN_ALSO_HELP')),
    availability_type varchar(20) NOT NULL CHECK (availability_type IN ('FULL','PARTIAL','FLEXIBLE')),
    availability_start timestamptz,
    availability_end timestamptz,
    max_commitment_minutes integer CHECK (max_commitment_minutes IS NULL OR max_commitment_minutes > 0),
    allow_alternative_work boolean NOT NULL DEFAULT false,
    status varchar(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(participation_request_id,actor_requirement_id),
    CHECK ((availability_start IS NULL AND availability_end IS NULL) OR (availability_start IS NOT NULL AND availability_end IS NOT NULL AND availability_end > availability_start))
);

CREATE TABLE IF NOT EXISTS participations (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    work_id uuid NOT NULL REFERENCES work_items(id),
    stage_id uuid NOT NULL REFERENCES stages(id),
    actor_requirement_id uuid NOT NULL REFERENCES actor_requirements(id),
    approved_from_request_item_id uuid NOT NULL UNIQUE REFERENCES participation_request_items(id),
    approved_start timestamptz NOT NULL,
    approved_end timestamptz NOT NULL,
    status varchar(40) NOT NULL DEFAULT 'ACCEPTED' CHECK (status IN ('ACCEPTED','WITHDRAWN_BY_PARTICIPANT','REMOVED_BY_ORGANIZER')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (approved_end > approved_start)
);

CREATE TABLE IF NOT EXISTS participation_item_decisions (
    id uuid PRIMARY KEY,
    request_item_id uuid NOT NULL REFERENCES participation_request_items(id) ON DELETE CASCADE,
    organizer_id uuid NOT NULL REFERENCES accounts(id),
    decision varchar(20) NOT NULL CHECK (decision IN ('APPROVE','REJECT')),
    idempotency_key varchar(200) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_notifications (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    notification_type varchar(50) NOT NULL CHECK (notification_type='PARTICIPATION_REQUEST'),
    participation_request_id uuid NOT NULL REFERENCES participation_requests(id) ON DELETE CASCADE,
    is_read boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(account_id,participation_request_id)
);

CREATE INDEX IF NOT EXISTS participation_requests_actor_idx ON participation_requests(requester_account_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS participations_actor_idx ON participations(account_id,event_id);

CREATE TABLE IF NOT EXISTS event_meetings (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title varchar(200) NOT NULL CHECK (length(btrim(title)) > 0),
    meeting_type varchar(30) NOT NULL CHECK (meeting_type IN ('BRIEFING','COORDINATION','HANDOFF','CHECK_IN','REVIEW','OTHER')),
    start_time timestamptz NOT NULL,
    end_time timestamptz NOT NULL,
    location varchar(500), note text,
    audience varchar(30) NOT NULL CHECK (audience IN ('ALL_ACTORS','STAGE','WORK','ROLE','SPECIFIC_ACTORS')),
    stage_id uuid REFERENCES stages(id), work_id uuid REFERENCES work_items(id),
    actor_requirement_id uuid REFERENCES actor_requirements(id),
    specific_actor_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(specific_actor_ids)='array'),
    status varchar(20) NOT NULL DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED','RESCHEDULED','CANCELLED')),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_by uuid NOT NULL REFERENCES accounts(id),
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (end_time > start_time)
);

CREATE TABLE IF NOT EXISTS actor_updates (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    recipient_account_id uuid REFERENCES accounts(id) ON DELETE CASCADE,
    audience varchar(30) NOT NULL CHECK (audience IN ('ACTOR','ALL_ACTORS')),
    update_type varchar(40) NOT NULL CHECK (update_type IN ('PARTICIPATION_DECISION','ORGANIZER_ANNOUNCEMENT','MEETING_UPDATE')),
    title varchar(200) NOT NULL, message text NOT NULL,
    priority varchar(20) NOT NULL DEFAULT 'NORMAL' CHECK (priority IN ('LOW','NORMAL','HIGH')),
    meeting_id uuid REFERENCES event_meetings(id) ON DELETE CASCADE,
    read_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS event_meetings_event_time_idx ON event_meetings(event_id,start_time);
CREATE INDEX IF NOT EXISTS actor_updates_recipient_idx ON actor_updates(event_id,recipient_account_id,created_at DESC);

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

-- Human reports are distinct from organizer announcements in actor_updates.
CREATE TABLE IF NOT EXISTS human_updates (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    reporter_account_id uuid NOT NULL REFERENCES accounts(id),
    source_type varchar(20) NOT NULL CHECK (source_type IN ('ACTOR','ORGANIZER')),
    stage_id uuid REFERENCES stages(id),
    work_id uuid REFERENCES work_items(id),
    actor_requirement_id uuid REFERENCES actor_requirements(id),
    participation_id uuid REFERENCES participations(id),
    original_text text NOT NULL CHECK (length(btrim(original_text)) > 0 AND length(original_text) <= 10000),
    idempotency_key varchar(200),
    interpretation_status varchar(20) NOT NULL DEFAULT 'NOT_REQUESTED',
    interpreted_at timestamptz,
    interpretation_failed_at timestamptz,
    interpretation_failure_code varchar(100),
    interpretation_attempt_count integer NOT NULL DEFAULT 0 CHECK (interpretation_attempt_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    UNIQUE(id,event_id),
    UNIQUE(event_id,reporter_account_id,idempotency_key)
);
ALTER TABLE human_updates DROP CONSTRAINT IF EXISTS human_updates_interpretation_status_check;
ALTER TABLE human_updates DROP CONSTRAINT IF EXISTS human_updates_interpretation_lifecycle_check;
ALTER TABLE human_updates DROP CONSTRAINT IF EXISTS human_updates_check;
ALTER TABLE human_updates ADD COLUMN IF NOT EXISTS interpretation_failed_at timestamptz;
ALTER TABLE human_updates ADD COLUMN IF NOT EXISTS interpretation_failure_code varchar(100);
ALTER TABLE human_updates ADD COLUMN IF NOT EXISTS interpretation_attempt_count integer NOT NULL DEFAULT 0;
ALTER TABLE human_updates DROP CONSTRAINT IF EXISTS human_updates_interpretation_attempt_count_check;
ALTER TABLE human_updates ADD CONSTRAINT human_updates_interpretation_attempt_count_check
    CHECK (interpretation_attempt_count >= 0);
UPDATE human_updates SET interpretation_status='FAILED',interpreted_at=NULL,
    interpretation_failed_at=COALESCE(interpretation_failed_at,now()),
    interpretation_failure_code=COALESCE(interpretation_failure_code,'LEGACY_INTERPRETATION_UNAVAILABLE'),
    interpretation_attempt_count=GREATEST(interpretation_attempt_count,1)
WHERE interpretation_status IN ('SUCCEEDED','FAILED');
UPDATE human_updates SET interpretation_attempt_count=GREATEST(interpretation_attempt_count,1)
WHERE interpretation_status IN ('RUNNING','INTERPRETED');
ALTER TABLE human_updates ADD CONSTRAINT human_updates_interpretation_status_check
    CHECK (interpretation_status IN ('NOT_REQUESTED','RUNNING','INTERPRETED','FAILED'));
ALTER TABLE human_updates ADD CONSTRAINT human_updates_interpretation_lifecycle_check CHECK (
    (interpretation_status='NOT_REQUESTED' AND interpreted_at IS NULL
        AND interpretation_failed_at IS NULL AND interpretation_failure_code IS NULL)
 OR (interpretation_status='RUNNING' AND interpreted_at IS NULL
        AND interpretation_failed_at IS NULL AND interpretation_failure_code IS NULL)
 OR (interpretation_status='INTERPRETED' AND interpreted_at IS NOT NULL
        AND interpretation_failed_at IS NULL AND interpretation_failure_code IS NULL)
 OR (interpretation_status='FAILED' AND interpreted_at IS NULL
        AND interpretation_failed_at IS NOT NULL AND interpretation_failure_code IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS human_updates_event_created_idx ON human_updates(event_id,created_at DESC);

CREATE OR REPLACE FUNCTION preserve_human_report() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.id, NEW.original_text, NEW.reporter_account_id, NEW.event_id, NEW.source_type,
           NEW.stage_id, NEW.work_id, NEW.actor_requirement_id, NEW.participation_id,
           NEW.created_at, NEW.idempotency_key)
       IS DISTINCT FROM
       ROW(OLD.id, OLD.original_text, OLD.reporter_account_id, OLD.event_id, OLD.source_type,
           OLD.stage_id, OLD.work_id, OLD.actor_requirement_id, OLD.participation_id,
           OLD.created_at, OLD.idempotency_key) THEN
        RAISE EXCEPTION 'original human report and attribution are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE OR REPLACE TRIGGER human_updates_immutable_report
    BEFORE UPDATE ON human_updates FOR EACH ROW EXECUTE FUNCTION preserve_human_report();

CREATE TABLE IF NOT EXISTS human_update_interpretations (
    id uuid PRIMARY KEY,
    human_update_id uuid NOT NULL UNIQUE,
    event_id uuid NOT NULL,
    interpretation_type varchar(40) NOT NULL CHECK (interpretation_type IN (
        'AVAILABILITY_CHANGE','ACCESS_PROBLEM','RESOURCE_PROBLEM','EQUIPMENT_PROBLEM',
        'SCHEDULE_DELAY','SAFETY_CONCERN','COMPLETION_UPDATE','GENERAL_UPDATE','UNKNOWN')),
    concise_summary varchar(500) NOT NULL CHECK (length(btrim(concise_summary)) > 0),
    reported_condition varchar(1000) NOT NULL CHECK (length(btrim(reported_condition)) > 0),
    temporal_signal varchar(500),
    location_signal varchar(500),
    referenced_stage_id uuid REFERENCES stages(id),
    referenced_work_id uuid REFERENCES work_items(id),
    possible_blocker boolean NOT NULL,
    blocker_reason varchar(1000),
    confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    requires_clarification boolean NOT NULL,
    clarification_question varchar(500),
    provider_name varchar(100) NOT NULL CHECK (length(btrim(provider_name)) > 0),
    model_id varchar(300) NOT NULL CHECK (length(btrim(model_id)) > 0),
    agent_name varchar(200) NOT NULL CHECK (length(btrim(agent_name)) > 0),
    agent_version varchar(50) NOT NULL CHECK (length(btrim(agent_version)) > 0),
    stop_reason varchar(100) NOT NULL CHECK (length(btrim(stop_reason)) > 0),
    usage jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(usage)='object'),
    blocker_assessment_status varchar(20) NOT NULL DEFAULT 'NOT_REQUESTED',
    blocker_assessment_failed_at timestamptz,
    blocker_assessment_failure_code varchar(100),
    blocker_assessment_attempt_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(human_update_id,event_id) REFERENCES human_updates(id,event_id),
    CHECK (possible_blocker = (blocker_reason IS NOT NULL)),
    CHECK (requires_clarification = (clarification_question IS NOT NULL))
);
ALTER TABLE human_update_interpretations
    ADD COLUMN IF NOT EXISTS blocker_assessment_status varchar(20) NOT NULL DEFAULT 'NOT_REQUESTED';
ALTER TABLE human_update_interpretations
    ADD COLUMN IF NOT EXISTS blocker_assessment_failed_at timestamptz;
ALTER TABLE human_update_interpretations
    ADD COLUMN IF NOT EXISTS blocker_assessment_failure_code varchar(100);
ALTER TABLE human_update_interpretations
    ADD COLUMN IF NOT EXISTS blocker_assessment_attempt_count integer NOT NULL DEFAULT 0;
ALTER TABLE human_update_interpretations
    DROP CONSTRAINT IF EXISTS human_update_interpretations_blocker_assessment_status_check;
ALTER TABLE human_update_interpretations
    DROP CONSTRAINT IF EXISTS human_update_interpretations_blocker_assessment_lifecycle_check;
ALTER TABLE human_update_interpretations
    DROP CONSTRAINT IF EXISTS human_update_interpretations_blocker_assessment_attempt_count_check;
ALTER TABLE human_update_interpretations
    ADD CONSTRAINT human_update_interpretations_blocker_assessment_status_check
    CHECK (blocker_assessment_status IN ('NOT_REQUESTED','RUNNING','ASSESSED','FAILED'));
ALTER TABLE human_update_interpretations
    ADD CONSTRAINT human_update_interpretations_blocker_assessment_attempt_count_check
    CHECK (blocker_assessment_attempt_count >= 0);
ALTER TABLE human_update_interpretations
    ADD CONSTRAINT human_update_interpretations_blocker_assessment_lifecycle_check CHECK (
       (blocker_assessment_status='NOT_REQUESTED' AND blocker_assessment_failed_at IS NULL
          AND blocker_assessment_failure_code IS NULL AND blocker_assessment_attempt_count=0)
    OR (blocker_assessment_status='RUNNING' AND blocker_assessment_failed_at IS NULL
          AND blocker_assessment_failure_code IS NULL AND blocker_assessment_attempt_count>0)
    OR (blocker_assessment_status='ASSESSED' AND blocker_assessment_failed_at IS NULL
          AND blocker_assessment_failure_code IS NULL AND blocker_assessment_attempt_count>0)
    OR (blocker_assessment_status='FAILED' AND blocker_assessment_failed_at IS NOT NULL
          AND blocker_assessment_failure_code IS NOT NULL AND blocker_assessment_attempt_count>0)
);
CREATE INDEX IF NOT EXISTS human_update_interpretations_event_created_idx
    ON human_update_interpretations(event_id,created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS human_update_interpretations_identity_scope_idx
    ON human_update_interpretations(id,human_update_id,event_id);

CREATE TABLE IF NOT EXISTS blockers (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id),
    source_human_update_id uuid NOT NULL,
    reported_by_account_id uuid NOT NULL REFERENCES accounts(id),
    created_by_account_id uuid NOT NULL REFERENCES accounts(id),
    stage_id uuid REFERENCES stages(id),
    work_id uuid REFERENCES work_items(id),
    title varchar(200) NOT NULL CHECK (length(btrim(title)) > 0),
    summary varchar(4000) NOT NULL CHECK (length(btrim(summary)) > 0),
    category varchar(100),
    handling_state varchar(20) NOT NULL DEFAULT 'ACKNOWLEDGED'
        CHECK (handling_state IN ('ACKNOWLEDGED','WORKING','STALLED')),
    condition_state varchar(20) NOT NULL DEFAULT 'OPEN'
        CHECK (condition_state IN ('OPEN','CLEARED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    cleared_at timestamptz,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    idempotency_key varchar(200),
    FOREIGN KEY(source_human_update_id,event_id) REFERENCES human_updates(id,event_id),
    UNIQUE(event_id,source_human_update_id),
    UNIQUE(event_id,idempotency_key),
    CHECK ((condition_state='OPEN' AND cleared_at IS NULL)
        OR (condition_state='CLEARED' AND cleared_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS blockers_event_created_idx ON blockers(event_id,created_at DESC);
CREATE INDEX IF NOT EXISTS blockers_event_work_idx ON blockers(event_id,work_id,condition_state);

CREATE TABLE IF NOT EXISTS blocker_assessments (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL,
    human_update_id uuid NOT NULL,
    interpretation_id uuid NOT NULL UNIQUE,
    is_execution_blocker boolean NOT NULL,
    blocker_kind varchar(30) NOT NULL CHECK (blocker_kind IN (
        'AVAILABILITY','ACCESS','RESOURCE','EQUIPMENT','SCHEDULE','SAFETY',
        'DEPENDENCY','OTHER','NONE')),
    concise_reason varchar(1000) NOT NULL CHECK (length(btrim(concise_reason)) > 0),
    directly_referenced_stage_id uuid REFERENCES stages(id),
    directly_referenced_work_id uuid REFERENCES work_items(id),
    severity_internal varchar(10) NOT NULL CHECK (severity_internal IN ('LOW','MEDIUM','HIGH')),
    urgency_internal varchar(10) NOT NULL CHECK (urgency_internal IN ('LOW','MEDIUM','HIGH')),
    coordination_needed boolean NOT NULL,
    replanning_may_be_needed boolean NOT NULL,
    requires_clarification boolean NOT NULL,
    clarification_question varchar(500),
    confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    authoritative_blocker_id uuid REFERENCES blockers(id),
    provider_name varchar(100) NOT NULL CHECK (length(btrim(provider_name)) > 0),
    model_id varchar(300) NOT NULL CHECK (length(btrim(model_id)) > 0),
    agent_name varchar(200) NOT NULL CHECK (length(btrim(agent_name)) > 0),
    agent_version varchar(50) NOT NULL CHECK (length(btrim(agent_version)) > 0),
    stop_reason varchar(100) NOT NULL CHECK (length(btrim(stop_reason)) > 0),
    usage jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(usage)='object'),
    assessed_event_version integer CHECK (assessed_event_version > 0),
    assessed_stage_version integer CHECK (assessed_stage_version > 0),
    assessed_work_version integer CHECK (assessed_work_version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(interpretation_id,human_update_id,event_id)
        REFERENCES human_update_interpretations(id,human_update_id,event_id),
    FOREIGN KEY(human_update_id,event_id) REFERENCES human_updates(id,event_id),
    CHECK (is_execution_blocker = (blocker_kind <> 'NONE')),
    CHECK (is_execution_blocker OR (coordination_needed=false AND replanning_may_be_needed=false)),
    CHECK (requires_clarification = (clarification_question IS NOT NULL)),
    CHECK (NOT requires_clarification OR NOT is_execution_blocker),
    CHECK (is_execution_blocker = (authoritative_blocker_id IS NOT NULL))
);
ALTER TABLE blocker_assessments ADD COLUMN IF NOT EXISTS assessed_event_version integer;
ALTER TABLE blocker_assessments ADD COLUMN IF NOT EXISTS assessed_stage_version integer;
ALTER TABLE blocker_assessments ADD COLUMN IF NOT EXISTS assessed_work_version integer;
ALTER TABLE blocker_assessments DROP CONSTRAINT IF EXISTS blocker_assessments_assessed_event_version_check;
ALTER TABLE blocker_assessments DROP CONSTRAINT IF EXISTS blocker_assessments_assessed_stage_version_check;
ALTER TABLE blocker_assessments DROP CONSTRAINT IF EXISTS blocker_assessments_assessed_work_version_check;
ALTER TABLE blocker_assessments ADD CONSTRAINT blocker_assessments_assessed_event_version_check
    CHECK (assessed_event_version > 0);
ALTER TABLE blocker_assessments ADD CONSTRAINT blocker_assessments_assessed_stage_version_check
    CHECK (assessed_stage_version > 0);
ALTER TABLE blocker_assessments ADD CONSTRAINT blocker_assessments_assessed_work_version_check
    CHECK (assessed_work_version > 0);
CREATE INDEX IF NOT EXISTS blocker_assessments_event_created_idx
    ON blocker_assessments(event_id,created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS blockers_identity_scope_idx ON blockers(id,event_id);
CREATE UNIQUE INDEX IF NOT EXISTS blocker_assessments_identity_scope_idx
    ON blocker_assessments(id,event_id,authoritative_blocker_id);

CREATE TABLE IF NOT EXISTS affected_work_resolutions (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL,
    blocker_id uuid NOT NULL UNIQUE,
    blocker_assessment_id uuid NOT NULL UNIQUE,
    directly_affected_work_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
    downstream_affected_work_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
    affected_stage_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
    deterministic_reason varchar(500) NOT NULL CHECK (length(btrim(deterministic_reason)) > 0),
    graph_fingerprint char(64) NOT NULL CHECK (graph_fingerprint ~ '^[0-9a-f]{64}$'),
    assessed_event_version integer NOT NULL CHECK (assessed_event_version > 0),
    resolved_event_version integer NOT NULL CHECK (resolved_event_version > 0),
    source_versions jsonb NOT NULL CHECK (jsonb_typeof(source_versions)='object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(blocker_id,event_id) REFERENCES blockers(id,event_id) ON DELETE CASCADE,
    FOREIGN KEY(blocker_assessment_id,event_id,blocker_id)
        REFERENCES blocker_assessments(id,event_id,authoritative_blocker_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS affected_work_resolutions_event_created_idx
    ON affected_work_resolutions(event_id,created_at DESC);

CREATE TABLE IF NOT EXISTS coordination_requests (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    blocker_id uuid NOT NULL UNIQUE REFERENCES blockers(id) ON DELETE CASCADE,
    blocker_assessment_id uuid NOT NULL REFERENCES blocker_assessments(id),
    affected_work_resolution_id uuid NOT NULL UNIQUE REFERENCES affected_work_resolutions(id),
    organizer_id uuid NOT NULL REFERENCES accounts(id),
    source_fingerprint char(64) NOT NULL CHECK (source_fingerprint ~ '^[0-9a-f]{64}$'),
    source_versions jsonb NOT NULL CHECK (jsonb_typeof(source_versions)='object'),
    status varchar(20) NOT NULL CHECK (status IN ('RUNNING','SUCCEEDED','FAILED')),
    attempt_count integer NOT NULL CHECK (attempt_count > 0),
    proposal_id uuid,
    failure_code varchar(100),
    failed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((status='FAILED') = (failed_at IS NOT NULL AND failure_code IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS coordination_proposals (
    id uuid PRIMARY KEY,
    request_id uuid NOT NULL UNIQUE REFERENCES coordination_requests(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    blocker_id uuid NOT NULL UNIQUE REFERENCES blockers(id) ON DELETE CASCADE,
    affected_work_resolution_id uuid NOT NULL UNIQUE REFERENCES affected_work_resolutions(id),
    coordination_possible boolean NOT NULL,
    requires_replanning boolean NOT NULL,
    actions jsonb NOT NULL CHECK (jsonb_typeof(actions)='array'),
    rationale varchar(2000) NOT NULL CHECK (length(btrim(rationale)) > 0),
    confidence numeric(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    source_fingerprint char(64) NOT NULL CHECK (source_fingerprint ~ '^[0-9a-f]{64}$'),
    source_versions jsonb NOT NULL CHECK (jsonb_typeof(source_versions)='object'),
    provider_name varchar(100) NOT NULL,
    model_id varchar(300) NOT NULL,
    agent_name varchar(200) NOT NULL,
    agent_version varchar(50) NOT NULL,
    stop_reason varchar(100) NOT NULL,
    usage jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(usage)='object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (NOT (coordination_possible AND requires_replanning))
);
ALTER TABLE coordination_requests DROP CONSTRAINT IF EXISTS coordination_requests_proposal_id_fkey;
ALTER TABLE coordination_requests ADD CONSTRAINT coordination_requests_proposal_id_fkey
    FOREIGN KEY(proposal_id) REFERENCES coordination_proposals(id);
CREATE INDEX IF NOT EXISTS coordination_requests_event_created_idx
    ON coordination_requests(event_id,created_at DESC);
