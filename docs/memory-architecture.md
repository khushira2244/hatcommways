# Hatcommways — Memory Architecture

## 1. Purpose

This document defines how Hatcommways stores, retrieves, updates, and governs memory across:

- projects
- participants
- organizations
- communities
- responsibilities
- agents
- execution history
- failures
- outcomes

Hatcommways must not treat memory as one giant conversation transcript.

Memory exists to improve execution intelligence while preserving:

- privacy
- traceability
- correctness
- least-privilege access
- human control

Core principle:

> Store structured execution truth separately from agent memory.

---

# 2. Memory Is Not System Truth

The authoritative system state remains deterministic application data.

Examples:

- project state
- task state
- responsibility state
- accepted actors
- dependency edges
- timeline version
- event records
- organization membership
- visibility settings
- support state

Agent memory may summarize or retrieve this information, but memory must never silently override authoritative persisted state.

Core rule:

> Database state is truth.
> Memory provides context.

---

# 3. Memory Categories

Hatcommways initially requires these memory classes:

1. Project Memory
2. Participant Memory
3. Organization Memory
4. Community Memory
5. Relationship Memory
6. Execution Pattern Memory
7. Failure and Revision Memory
8. Outcome / Blueprint Memory
9. Agent Working Memory

Each category has different:

- lifetime
- visibility
- access rules
- update rules
- reuse boundaries

For technical execution, these categories form seven required memory capabilities:

The nine memory categories above describe ownership, scope, visibility, lifetime, and governance dimensions. The seven capabilities below describe technical runtime behavior. They are complementary views of the same governed memory architecture, not competing taxonomies.

## A. Agent Working Memory

Temporary context for one bounded agent or Strands Graph run.

## B. Project Episodic Memory

Important events, state transitions, decisions, and execution history within the current project. Project Episodic Memory is a structured view over relevant project history; it does not replace raw events.

## C. Decision Memory

What decision was made, by whom, when, why, against which state version, and with what affected scope.

## D. Execution-Pattern Memory

Reusable operational patterns derived from validated outcomes across projects.

## E. Failure / Revision Memory

Failures, causes, downstream consequences, replanning attempts, rejected alternatives, and successful mitigations.

## F. Outcome Memory

What ultimately happened, including outcome quality, partial success, unresolved work, and the relationship between the final result and the execution process.

## G. Blueprint Memory

Privacy-safe reusable task, dependency, actor, event, and mitigation structures derived from completed projects.

---

# 4. Project Memory

Project Memory represents the durable contextual history of one project.

It may contain:

- original goal
- clarified goal
- planning assumptions
- task-plan versions
- dependency-plan versions
- timeline revisions
- actor-role topology
- responsibility changes
- important decisions
- blocker history
- event history
- organization participation
- support-state changes
- project revisions
- outcome

Project Memory belongs to one project.

---

# 5. Project Memory vs Event History

Raw event history and Project Memory are different.

## Raw Event History

Contains exact append-only events such as:

- task.created
- responsibility.accepted
- actor.withdrawn
- timeline.recalculated
- event.rescheduled

This is authoritative audit/history data.

## Project Memory

Contains higher-level structured understanding such as:

> Two additional actors joined on Day 4, allowing the construction and location branches to run in parallel.

Project Memory may be generated from authoritative event history.

Never delete raw events because a memory summary exists.

---

# 6. Project Memory Entries

A project-memory entry may conceptually contain:

- memory id
- project id
- memory type
- source event ids
- source state version
- summary
- structured facts
- created time
- superseded-by reference
- visibility scope
- confidence where applicable

Memory should preserve source references.

---

# 7. Project Memory Types

Potential project memory types include:

- goal
- planning_assumption
- plan_revision
- actor_change
- responsibility_change
- blocker
- resolution
- decision
- event_summary
- support_change
- execution_pattern
- failure
- lesson
- outcome

The exact schema may evolve.

---

# 8. Participant Memory

Participant Memory represents reusable information about a person's participation where appropriate and permitted.

Potential information:

- voluntarily provided skills
- preferred contribution types
- communities joined
- organization affiliations
- prior responsibility types
- completed responsibilities
- availability preferences
- geographic preferences at an allowed precision
- participation history
- user-selected profile information

Hatcommways must not infer or retain unnecessary personal information.

---

# 9. Participant Memory Boundaries

Participant Memory must not automatically contain:

- private conversations unrelated to projects
- restricted support or external-funding information
- sensitive personal details unrelated to execution
- hidden demographic inference
- exact location history
- behavioral profiling unrelated to community execution

Core principle:

> Remember what improves participation, not everything the person has ever done.

---

# 10. Participant Execution Memory

The system may retain structured contribution history such as:

- role type carried
- project
- responsibility scope
- completion state
- event participation
- handoff/withdrawal where relevant
- execution duration
- organization represented

This can improve future actor recommendations.

Example:

Participant previously completed:

- 3 organizer responsibilities
- 2 event-coordinator responsibilities

The Actor Fit Agent may use this where allowed.

---

# 11. Participant Memory Visibility

Different participant-memory fields may have different scopes.

Possible scopes:

- private to user
- usable internally by authorized agents
- visible to project members
- visible to communities
- public profile

Public visibility must not be inferred.

Users control what becomes public.

---

# 12. Organization Memory

Organization Memory represents durable execution context about an organization.

Examples:

- organization type
- service area
- participation preferences
- project categories supported
- roles previously carried
- representatives
- recurring communities
- events hosted
- execution history
- public support preferences

This may apply to:

- NGO
- welfare group
- school
- company
- resident body
- nonprofit
- other organization

---

# 13. Sponsor / Company Memory

A company may have private memory about:

- projects supported
- contribution type
- amount where appropriate
- roles enabled
- locations
- outcomes
- appreciation messages
- internal impact history

This supports the private Sponsor Impact Map.

Core rule:

> Private sponsor memory does not become public sponsorship history automatically.

---

# 14. Organization Representative Memory

Hatcommways must distinguish:

Organization
from
Representative

The system may remember:

- which person represents which organization
- authorization scope
- relevant projects
- expiration/revocation of authority

This should be authoritative identity/authorization data where possible rather than free-form agent memory.

---

# 15. Community Memory

Community Memory represents recurring knowledge about a Temporary Group or Permanent Community.

Possible information:

- community purpose
- location/service area
- recurring members
- previous projects
- common actor roles
- recurring organization relationships
- typical event patterns
- previous execution outcomes
- participation patterns

Temporary groups may have shorter-lived memory.

Permanent communities may accumulate richer memory over time.

---

# 16. Temporary Group Memory

Temporary-group memory should focus on:

- current project
- members
- responsibility structure
- events
- decisions
- support state
- outcome

After project completion:

- archive memory
- retain project provenance
- do not automatically convert it to permanent community memory

---

# 17. Permanent Community Memory

Permanent communities may reuse knowledge across multiple projects.

Examples:

> This neighborhood often has strong weekend participation.

> This maker community frequently provides technical specialists.

> This welfare group has previously hosted animal-care events.

These should be based on recorded participation, not unsupported inference.

---

# 18. Relationship Memory

Relationship Memory represents recurring execution relationships between entities.

Examples:

- participant ↔ community
- participant ↔ organization
- organization ↔ community
- organization ↔ project type
- community ↔ location
- participant ↔ actor role
- organization ↔ event hosting
- sponsor ↔ project

Relationship Memory should be graph-like.

---

# 19. Relationship Memory Example

Example:

Person A
→ member_of
Community B

Community B
→ previously_collaborated_with
Organization C

Organization C
→ hosted
Event Type D

Future agents may use these relationships to improve execution planning.

But relationship existence must not automatically imply future commitment.

---

# 20. Execution Pattern Memory

Execution Pattern Memory captures reusable patterns learned from completed projects.

Examples:

- projects of this scale often need two coordinators
- actor recruitment commonly takes longer than expected
- installation tasks often become parallelizable after location confirmation
- community events in this category frequently require a separate event owner

This memory can improve future planning.

Reusable execution memory should carry applicability metadata rather than relying on semantic similarity alone.

Potential metadata includes:

- source_project_type
- context_signature
- project_scale
- actor_structure
- dependency_pattern
- location/context class where safe
- outcome_quality
- failure_pattern
- mitigation_pattern
- recency
- reuse_count
- confidence
- applicability_score
- provenance

---

# 21. Execution Pattern Sources

Patterns should derive from actual historical data.

Potential sources:

- completed projects
- task duration history
- actor-count history
- dependency structures
- replanning history
- blocker frequency
- event outcomes

Avoid creating "learned patterns" from one isolated project unless clearly marked low confidence.

---

# 22. Pattern Confidence

Execution patterns should have confidence metadata.

Example:

Pattern:

Community cleanups with >50 participants often need more than one coordinator.

Evidence:
18 completed projects

Confidence:
high

Another pattern:

Robotics workshops need two specialists.

Evidence:
1 project

Confidence:
low

Agents may use confidence during reasoning.

---

# 23. Cross-Project Memory

Some memory may be reusable across projects.

Examples:

- actor skills
- organization participation history
- execution patterns
- community capability
- common task timing

Cross-project reuse must obey:

- privacy
- visibility
- tenant/community boundary
- user preference
- project permissions

Core principle:

> Reusable does not mean universally visible.

---

# 24. Failure Memory

Failure Memory is a first-class category.

Hatcommways should remember:

- what failed
- where
- why
- affected tasks
- affected actors
- recovery attempt
- replacement plan
- final outcome

Do not store only successful execution.

Failure Memory should preserve the causal path and mitigation, not merely a failure label.

Example:

venue confirmation delayed
→ setup delayed
→ volunteers idle
→ event started late

Stored failure pattern:

late venue confirmation
→ downstream setup risk

Stored mitigation:

venue confirmation should occur before a defined pre-event threshold

A future Event Planning Agent may retrieve this pattern and propose an earlier confirmation dependency. The agent must still validate the pattern against the current event, actors, location, and timeline.

---

# 25. Failure Memory Example

Initial plan:

One organizer for 120-person event.

Failure:

Organizer became overloaded.

Replan:

Three sub-coordinators added.

Outcome:

Event completed successfully.

Future planning may learn:

> Similar project scale may require multiple coordination roles.

This is valuable execution intelligence.

---

# 26. Revision Memory

Revision Memory preserves:

- original plan
- revised plan
- reason for revision
- trigger event
- affected tasks
- affected actors
- timeline impact
- outcome

Never overwrite historical plans.

Core rule:

> Current state may change.
> History must not disappear.

---

# 27. Decision Memory

Important human or system decisions should be remembered with provenance.

Examples:

- creator approved revised scope
- organization accepted participation
- project owner enabled public Support Map
- event moved to another date
- responsibility transferred

Decision Memory may include:

- decision
- decision maker
- time
- reason where provided
- affected objects
- source state

---

# 28. Outcome Memory

When a project finishes, Outcome Memory records what actually happened.

Possible information:

- intended goal
- achieved outcome
- incomplete work
- participant count
- actor roles filled
- organizations involved
- events completed
- support model
- timeline difference
- blockers
- revisions
- final evidence
- lessons

Outcome Memory becomes the basis for reusable blueprints.

---

# 29. Blueprint Memory

A completed project may produce a reusable execution blueprint where privacy allows.

A blueprint may contain:

- project category
- goal structure
- task pattern
- dependency pattern
- actor-role structure
- approximate timeline
- common blockers
- useful replanning patterns
- event structure
- outcome summary

Blueprints must exclude private participant or restricted support information unless explicitly permitted.

Blueprint reuse must be applicability-aware. Scale-sensitive counts, durations, actor allocations, locations, and organization structures should be regenerated when the current context differs materially from the source project.

---

# 30. Agent Working Memory

Agent Working Memory is temporary.

It exists only for the current reasoning process.

Example:

Replanning Agent is comparing:

- current blocker
- affected tasks
- actor availability
- timeline alternatives

This temporary scratch state should not automatically become durable memory.

---

# 31. Working Memory Lifetime

Agent Working Memory may expire:

- after agent run
- after workflow completion
- after bounded retention period

Only meaningful validated conclusions should move into durable memory.

Core principle:

> Do not persist every reasoning scratchpad.

---

# 32. Memory Promotion

Information may move from temporary working context to durable memory only when:

- it represents a meaningful decision
- it represents a validated execution fact
- it represents an important project revision
- it represents a blocker/resolution
- it represents a durable project outcome

Promotion should be explicit.

---

# 33. Memory Provenance

Every durable memory item should ideally know where it came from.

Possible provenance:

- project event
- task state
- actor action
- organization action
- creator decision
- agent proposal
- approved plan revision
- completed outcome

Memory without provenance should be treated with lower trust.

---

# 34. Structured Memory vs Semantic Retrieval

Hatcommways may later use embeddings/vector retrieval, but structured memory remains primary.

Examples of structured lookup:

- who owns Task 7?
- which responsibilities are open?
- what was Plan v3?
- what organization joined?
- what blockers occurred?

These should not require semantic vector search.

Semantic retrieval is useful for:

- similar historical projects
- lessons
- narrative decisions
- project descriptions
- archived discussions

Core principle:

> Use exact structured retrieval when exact structure exists.

---

# 35. Memory Retrieval Strategy

An agent should receive only relevant memory.

Example:

Timeline Planning Agent may need:

- current task graph
- task timing history
- relevant execution patterns

It does not need:

- private support instructions
- full private organization-support history
- unrelated participant messages

Memory retrieval should be:

- scoped
- permission-aware
- agent-specific
- query-driven

## Applicability-Aware Retrieval

Reusable memory must not use a "closest text wins" policy.

Retrieval and ranking should consider:

semantic relevance
+
structural similarity
+
project scale
+
actor structure
+
outcome quality
+
recency
+
applicability

Example:

Past project:

- community cleanup
- 12 volunteers
- 1 location
- 4 hours

Current project:

- community cleanup
- 45 volunteers
- 3 locations
- 2 organizations

The memory system may conclude:

- the dependency pattern is applicable
- timing is only partially applicable
- actor allocation is not directly reusable
- scale-sensitive values must be regenerated

Each supplied memory reference should include provenance, source scope, confidence, applicability metadata, and the reason it was selected. Agents must clearly distinguish current-state facts from historical or reusable context.

Core rule:

> Memory recommends context. Current transactional state remains truth.

---

# 36. Memory Access Control

Memory access follows least privilege.

Potential controls:

- project membership
- actor role
- organization role
- community membership
- project visibility
- memory type
- agent permission
- purpose of access

Agents must not bypass normal application permissions.

---

# 37. Agent Memory Profiles

Each agent should eventually have an explicit memory profile.

Example:

## Goal Understanding Agent

May read:

- current project creation input
- creator-approved project context
- relevant prior project context if explicitly reused

May not read:

- unrelated private organization-support history
- unrelated participant history

## Actor Fit Agent

May read:

- open role
- participant-provided skills
- availability
- allowed prior contribution history
- location at allowed precision

May not read:

- private project support instructions

---

# 38. Planning-Agent Memory

Goal, task, dependency, timeline, and parallelization agents may access:

- current project plan
- previous plan revisions
- relevant execution-pattern memory
- historical timing patterns
- blocker history from similar projects where allowed

They should not automatically access:

- private contributor details
- unrelated user profile information

---

# 39. Actor-Agent Memory

Actor-related agents may access:

- actor-role requirements
- participant availability
- role history
- skills voluntarily provided
- community/organization relationships
- current responsibility load

They should not assume prior participation equals willingness to participate again.

---

# 40. Organization-Agent Memory

Organization Participation Agent may access:

- organization type
- public capabilities
- project participation history
- representative relationships
- organization preferences
- current project interaction

Private sponsorship history should be accessible only when authorized.

---

# 41. Scheduling-Agent Memory

Scheduling Agent may access:

- task timing
- event constraints
- relevant participant availability
- organization availability where shared
- current timeline

It should not retain unrelated personal-calendar data beyond what is necessary.

---

# 42. Blocker and Replanning Memory

Blocker Detection and Replanning Agents may access:

- current plan
- blocker history
- prior revisions
- affected actor availability
- relevant failure patterns
- timeline state

These agents benefit strongly from failure/revision memory.

---

# 43. Support-Agent Memory

Support State Reasoning Agent may access:

- support mode
- project support state, including optional externally arranged funding where relevant
- tasks whose execution explicitly depends on support
- manually confirmed contribution state

It should not need:

- restricted external-funding credentials or instructions
- private banking information

---

# 44. Map-Intelligence Memory

Participation and Support Intelligence Agents may access:

- privacy-safe aggregated map data
- current participation structure
- role distribution
- support distribution
- organization involvement

They must not query private raw data merely to create public narratives.

---

# 45. Project Memory Agent

Project Memory Agent may access broad project execution history because its role is to identify and structure candidate memory and summarize important execution history.

It may read:

- raw project events
- plan revisions
- task history
- responsibility history
- event history
- support-state changes
- project decisions

Its outputs may include candidate memory entries, structured summaries, and candidate execution-history interpretations. They still require provenance and validation.

The agent does not control durable persistence, promotion, supersession, or compaction. Those remain governed by the Memory Writer and validation rules.

---

# 46. Outcome and Blueprint Agent

Outcome Agent may access:

- final goal
- project history
- completed tasks
- failed tasks
- revisions
- actors
- organizations
- events
- support state
- evidence
- lessons

When generating reusable blueprint memory, it must remove or generalize private information.

---

# 47. Memory Freshness

Some memory becomes stale.

Examples:

- availability
- organization representative authorization
- project role
- current actor capacity
- temporary group membership

Memory should distinguish:

- durable history
- current state
- stale context

Do not treat old availability as current availability.

---

# 48. Memory Versioning

Memory entries may be superseded but should not be destructively overwritten when history matters.

Example:

Plan assumption v1:
6 volunteers available

Later:

4 volunteers available

Current planning uses the latest value.

Historical memory preserves both states.

---

# 49. Memory Conflict Handling

Different sources may conflict.

Example:

Project member says:

event is Saturday

Project owner later updates:

event is Sunday

Authoritative event state becomes Sunday.

Old memory remains historical but must not be presented as current truth.

Memory retrieval should prioritize:

1. current authoritative state
2. latest validated memory
3. historical context

---

# 50. Memory Confidence

Some memory is factual.

Example:

Task completed at 15:42.

Confidence:
authoritative

Some is inferred.

Example:

This project likely struggled because coordination capacity was too low.

Confidence:
inferred

Memory should distinguish fact from interpretation.

---

# 51. Memory Privacy Classes

Potential memory privacy classes:

- public
- project_members
- project_admins
- community_members
- organization_internal
- participant_private
- system_internal

Every durable memory item should inherit or define appropriate visibility.

---

# 52. Sensitive Memory

Sensitive information may include:

- restricted support instructions
- exact private locations
- contact information
- private organization details
- participant availability
- private project discussions

Sensitive information should not enter general semantic memory indexes without a strong reason and proper access controls.

---

# 53. Public Memory

Public project memory may include:

- public project goal
- public updates
- approved actor participation
- approved organization involvement
- public timeline summary
- approved maps
- completed outcome
- public appreciation

Public memory is safe for project discovery.

---

# 54. Retention

Not every memory category requires permanent retention.

Potential examples:

## Long-term

- project outcome
- plan revisions
- responsibility history
- blueprint
- important decisions

## Medium-term

- project working summaries
- organization project context

## Short-term

- temporary agent working memory
- transient availability
- temporary scheduling options

Retention policies will be defined later.

---

# 55. Forget / Remove Requirements

Hatcommways should support privacy-driven deletion or deactivation where legally/product-wise appropriate.

However, deletion must be balanced against:

- audit requirements
- project integrity
- responsibility history
- organization records

Where a participant must be removed from reusable memory, project history may need pseudonymized references rather than rewriting project truth.

Exact retention/deletion policy will be defined later.

---

# 56. Memory and Maps

Maps should derive from current governed data.

They should not derive blindly from historical semantic memory.

Example:

Action Map needs:

current participation state

not:

"Participant once lived in this area."

Support Map needs:

approved contribution aggregation

not:

historical organization-support memory from unrelated projects.

---

# 57. Memory and Actor Matching

Actor Fit Agent may use relevant historical memory.

Example:

Open role:
Event Coordinator

Candidate has previously completed:
4 event-coordination responsibilities

This may increase fit.

But matching must also consider:

- current availability
- current capacity
- project location
- user preferences
- privacy

Historical success is one signal, not automatic assignment.

---

# 58. Memory and Timeline Planning

Historical project memory can improve timing.

Example:

Initial generic estimate:
2 days

Historical similar tasks:
usually 4–5 days

Timeline Agent may use that pattern.

The system should retain:

- estimate source
- confidence
- whether historical data influenced the estimate

---

# 59. Memory and Parallelization

Historical execution patterns may reveal:

> These two task categories usually execute independently.

Parallelization Agent may use this as a suggestion.

It must still validate against the current project's actual dependencies and actors.

Past patterns cannot override current graph truth.

---

# 60. Memory and Blockers

Blocker Detection may use memory to identify repeated patterns.

Example:

This branch has had three responsibility withdrawals.

The agent may infer:

> Actor capacity may be unstable.

This is an interpretation, not a deterministic fact.

The output should indicate that.

---

# 61. Memory and Replanning

Replanning Agent should be able to retrieve:

- previous successful alternatives
- prior failed replans
- similar blocker resolutions
- project-specific failed attempts

This prevents repeatedly proposing an already failed solution.

---

# 62. Memory and Outcome

Outcome memory should preserve both:

- achievement
- process

Example:

Goal completed successfully.

But history may show:

- two failed event dates
- one actor withdrawal
- one major plan revision

Those are part of the project's real story.

---

# 63. Memory Write Events

Potential triggers for durable memory creation:

- goal approved
- plan approved
- plan revised
- task branch materially changed
- important responsibility accepted
- major actor withdrawal
- blocker created
- blocker resolved
- important human decision
- event completed
- support state materially changed
- project completed

Not every minor UI event deserves durable memory.

---

# 64. Memory Compaction

Long-running projects may generate thousands of events.

Project Memory Agent may propose periodic structured compactions. The Memory Writer creates the durable compaction record only after validation.

Example:

Raw:
250 low-level events

Compacted memory:

Week 2 Execution Summary

with source references to those events.

Raw events remain append-only and available for audit.

Compaction improves agent context efficiency.

---

# 65. Memory Hierarchy

Conceptually:

Raw Events
→ authoritative historical record

Current Structured State
→ authoritative current truth

Structured Project Memory
→ durable contextual understanding

Cross-Project Pattern Memory
→ reusable execution intelligence

Agent Working Memory
→ temporary reasoning context

These layers must not be collapsed.

---

# 66. Retrieval Priority

When an agent needs information:

1. Read current authoritative state.
2. Retrieve relevant project memory.
3. Retrieve relevant historical pattern memory if useful.
4. Use temporary working memory during reasoning.

Never start with generic semantic memory when exact current state exists.

---

# 67. Memory Storage Architecture

The final infrastructure may use multiple storage technologies.

Conceptually:

## Relational / transactional storage

For:

- current state
- tasks
- responsibilities
- actors
- events
- permissions
- support state
- plan revisions

## Append-only event/audit store

For:

- historical state transitions
- agent runs
- decisions

## Semantic retrieval capability

For:

- project narratives
- lessons
- similar blueprints
- historical summaries

A dedicated semantic/vector database is not required for the initial implementation. Structured relational storage remains primary. Semantic retrieval may later be introduced narrowly for similar completed projects, historical lessons, narrative decisions, reusable blueprint retrieval, and historical summaries.

## Cache / temporary store

For:

- working context
- ephemeral agent state
- short-lived execution data

Technology choice will be defined later.

## Memory Retriever Boundary

The Memory Retriever accepts an authorized, agent-specific query and current-context signature. It returns only relevant memory with provenance, confidence, applicability metadata, and privacy-safe fields.

It should:

- retrieve current-project episodic and decision memory first where relevant
- retrieve failure/revision and blueprint memory only when useful
- compare structural context and scale rather than semantic similarity alone
- reject or down-rank inapplicable memories
- enforce project, participant, organization, community, and agent access boundaries
- attach stable memory references for proposal provenance

## Memory Writer Boundary

The Memory Writer records durable memory only from validated facts, decisions, outcomes, failures, revisions, and approved lessons.

It must not persist:

- raw chain-of-thought
- every model message
- unvalidated agent guesses
- transient graph-run scratch state

Raw events remain append-only authoritative history. The Memory Writer creates structured contextual records with source references and state versions after the relevant outcome or decision has been validated.

---

# 68. Embeddings

Hatcommways should not embed everything.

Embeddings may be useful for:

- finding similar completed projects
- retrieving historical lessons
- matching narrative descriptions
- finding relevant blueprint sections

Embeddings are not needed for:

- task ownership
- current responsibility status
- permissions
- dependency traversal
- exact contribution amount
- timeline version

Core principle:

> Structured facts stay structured.

---

# 69. Memory Security

Memory systems must protect against:

- unauthorized cross-project access
- accidental sponsor-history leakage
- restricted support-detail leakage
- exact location leakage
- agent over-retrieval
- stale authorization data
- semantic-search permission bypass

Permission checks must apply before and after retrieval where required.

---

# 70. Multi-Agent Memory Coordination

Multiple agents may write memory around the same project.

To avoid conflicts:

- use typed memory categories
- reference source state versions
- use append-only writes where possible
- support supersession
- avoid agents destructively editing each other's memory
- let deterministic services control final persisted state

---

# 71. Agent Run Memory

Every agent run should have execution metadata:

- run id
- agent type
- project id
- trigger
- input state version
- memory retrieved
- tools used
- output reference
- final status

This is operational/audit memory, not product memory.

---

# 72. Memory Failure Isolation

If semantic memory is unavailable:

- current project execution must continue
- deterministic state remains usable
- agents may operate with reduced historical context
- optional historical recommendations may be disabled

Memory failure must not corrupt execution truth.

---

# 73. Memory Cost Control

Memory retrieval should be bounded.

Strategies:

- agent-specific scopes
- latest relevant summaries
- affected-task retrieval
- targeted historical retrieval
- memory compaction
- avoid full project replay for every agent invocation

---

# 74. Initial Memory-Agent Responsibilities

The Project Memory Agent should initially focus on:

- plan revisions
- major decisions
- actor topology changes
- blockers/resolutions
- event summaries
- outcome preparation

These are candidate-memory and summarization responsibilities. The Memory Writer governs durable persistence, validated promotion, supersession, and compaction records.

It should not attempt to build a universal knowledge graph on Day 1.

---

# 75. Initial Cross-Project Memory

The first real reusable cross-project memory should likely focus on:

- task-duration patterns
- actor-role requirements
- common blocker patterns
- successful replanning patterns
- completed project blueprints

These directly improve future execution planning.

---

# 76. Memory Invariants

## Invariant 1

Memory does not override authoritative current state.

## Invariant 2

Raw history is not replaced by summaries.

## Invariant 3

Temporary agent reasoning is not automatically durable memory.

## Invariant 4

Historical participation does not imply future commitment.

## Invariant 5

Current availability must not be inferred from old memory.

## Invariant 6

Private sponsor history must not leak into public project views.

## Invariant 7

Restricted support instructions must not enter general public semantic retrieval.

## Invariant 8

Cross-project memory reuse must obey access boundaries.

## Invariant 9

Facts and agent interpretations should be distinguishable.

## Invariant 10

Structured facts should remain structured.

## Invariant 11

Reusable memory must carry applicability and provenance; semantic similarity alone is insufficient.

## Invariant 12

Memory Writer persists validated outcomes, failures, revisions, and decisions, not raw hidden reasoning.

---

# 77. Example Memory Flow

Project:

Build 20 shelters for street dogs.

Initial plan:

6 tasks
2 parallel branches
5 actor roles

Project Memory stores:

Plan v1.

Later:

Two new actors join.

Parallelization Agent proposes:

Construction and location branch can run concurrently.

Creator/project policy accepts safe timeline update.

Memory records:

Plan v2
Reason:
additional execution capacity

Later:

transport actor withdraws.

Blocker recorded.

Replanning Agent proposes:

reassign transport responsibility without pausing construction.

Memory records:

Blocker
Resolution
Plan v3

Project completes.

Outcome Agent generates:

- final result
- timeline variance
- actor participation
- blockers
- revisions
- lessons

Blueprint Agent creates privacy-safe reusable execution blueprint.

Future similar project may retrieve:

> Transport responsibility was a recurring bottleneck in this completed project.

That is how Hatcommways becomes smarter without losing execution truth.

---

# 78. Final Principle

Hatcommways memory should answer:

> What happened?
> What changed?
> Why did it change?
> Who carried responsibility?
> What failed?
> What worked?
> What should this project remember?
> What can future projects safely learn from it?

Memory exists to make execution increasingly intelligent.

It must never become an uncontrolled archive of everything users have ever said or done.
