# Hatcommways — Agent Architecture

## 1. Purpose

This document defines the initial multi-agent architecture for Hatcommways.

The goal is not to maximize agent count.

The goal is to create specialized reasoning boundaries where separate agents are genuinely justified by differences in:

- responsibility
- trigger conditions
- memory
- permissions
- tools
- execution state
- failure handling
- concurrency
- outputs

Hatcommways should use agents only for reasoning-heavy work.

Deterministic application logic should remain responsible for system truth.

Core principle:

> Use agents for reasoning.
> Use deterministic software for state, permissions, transitions, and truth.

---

# 2. Agent Architecture Philosophy

Hatcommways is not a linear chain of agents.

It must not behave like:

Agent 1
→ Agent 2
→ Agent 3
→ Agent 4

Instead, Hatcommways is event-driven and dependency-driven.

Different agents may run in parallel when:

- they have the inputs they require
- they are working on independent execution branches
- their outputs do not require strict sequencing
- project state allows concurrent reasoning

Core principle:

> Agents react to project state and events, not to a fixed global sequence.

---

# 3. Agent vs Deterministic Service

An agent should exist when the capability requires interpretation, reasoning, adaptation, or planning.

A deterministic service should exist when the capability is based on explicit rules or persisted truth.

## Agent examples

- decomposing an ambiguous goal
- identifying task relationships
- estimating actor-role needs
- proposing parallelization
- interpreting blockers
- proposing replanning alternatives
- summarizing impact
- detecting meaningful execution patterns

## Deterministic service examples

- permission checks
- task state transitions
- responsibility counts
- dependency satisfaction
- actor vacancy calculation
- event persistence
- audit logs
- map aggregation
- visibility filtering
- authentication
- notification delivery
- idempotency
- version checking

Do not convert deterministic capabilities into agents merely to increase agent count.

---

# 4. Initial Agent Domains

The initial architecture is divided into these domains:

1. Goal Understanding
2. Project Decomposition
3. Task and Dependency Planning
4. Timeline and Parallelization
5. Actor Requirement Planning
6. Responsibility Intelligence
7. Community / Organization Intelligence
8. Event and Scheduling Intelligence
9. Blocker and Replanning Intelligence
10. Support-State Intelligence
11. Map and Participation Intelligence
12. Memory and Outcome Intelligence

These domains produce the initial agent set.

---

# 5. Agent 1 — Goal Understanding Agent

## Purpose

Understand what the creator actually wants to make happen.

## Inputs

- natural-language goal
- location
- timeframe
- funding mode
- creator-provided context

## Responsibilities

- interpret the primary goal
- identify ambiguity
- identify project scale at a high level
- identify whether the request appears to describe:
  - a small event
  - a larger project
  - a recurring initiative
- produce a structured goal representation

## Should Ask Human When

A missing fact prevents reasonable project planning.

The agent should not ask unnecessary domain questions.

Hatcommways is an execution planner, not a domain interrogation system.

## Outputs

- structured goal
- preliminary project type
- ambiguity markers
- planning assumptions

---

# 6. Agent 2 — Project Scope Agent

## Purpose

Determine the initial execution scope of the project.

## Responsibilities

Reason about:

- approximate project scale
- likely number of execution branches
- likely duration class
- whether project contains one or more events
- whether multiple groups or organizations are likely to participate
- whether specialist roles may be required

## Outputs

- project scale
- complexity indicators
- initial planning boundaries
- scope assumptions

This agent does not create the final task graph.

---

# 7. Agent 3 — Task Decomposition Agent

## Purpose

Convert the goal into meaningful execution tasks.

## Responsibilities

- generate tasks
- avoid unnecessary micro-tasks
- avoid overly broad tasks
- identify natural work branches
- create parent/child task relationships when appropriate
- identify tasks that represent coordination work as well as direct execution work

## Outputs

- proposed task graph nodes
- task descriptions
- task groups/branches
- estimated task purpose

The agent must not assign people while decomposing tasks.

Tasks and actors remain separate systems.

---

# 8. Agent 4 — Dependency Reasoning Agent

## Purpose

Determine how tasks depend on one another.

## Responsibilities

Reason about:

- prerequisite relationships
- independent work
- branching
- merging
- conditional work
- event prerequisites
- approval prerequisites where relevant

## Outputs

- dependency edges
- dependency explanations
- independent branches
- possible execution order

Deterministic graph services later persist and validate dependency state.

---

# 9. Agent 5 — Timeline Planning Agent

## Purpose

Create the initial timing model from tasks and dependencies.

## Responsibilities

- estimate task duration
- estimate earliest plausible start
- estimate likely completion
- identify major execution phases
- produce initial project timeline
- mark uncertainty

## Outputs

- initial timeline
- timing estimates
- confidence ranges
- critical timing assumptions

The timeline is never treated as immutable.

---

# 10. Agent 6 — Parallelization Agent

## Purpose

Identify work that can safely run in parallel.

## Responsibilities

Reason about:

- structural task independence
- potential concurrent branches
- actor contention
- opportunities for timeline compression
- work that does not need to wait for unrelated tasks

## Outputs

- parallelizable task groups
- actor requirements for parallel execution
- potential duration improvement
- contention warnings

This agent may rerun later when actor availability changes.

---

# 11. Agent 7 — Actor Requirement Agent

## Purpose

Determine what kinds of actor roles the project requires.

## Responsibilities

Generate project-specific roles based on:

- task graph
- project scale
- duration
- execution complexity
- specialist requirements
- organization involvement
- event structure

## Outputs

- canonical actor roles
- required role families
- role scope
- required / recommended / optional classification

This agent must not create every possible role for every project.

---

# 12. Agent 8 — Actor Capacity Agent

## Purpose

Determine how many actors of each role are needed.

## Responsibilities

Estimate:

- minimum actors
- ideal actors
- maximum useful actors
- team size
- coordination thresholds
- when additional leads/coordinators become necessary

## Example

Executor:

minimum = 4
ideal = 6
maximum useful = 8

## Outputs

- actor cardinality
- capacity requirements
- scale-based role expansion

---

# 13. Agent 9 — Role Specialization Agent

## Purpose

Convert generic actor roles into domain-relevant specializations when needed.

## Example

Canonical:

specialist

Specialization:

electronics

Display:

Electronics Specialist

## Responsibilities

- identify genuine specialist needs
- avoid unnecessary niche roles
- map specializations back to canonical roles
- preserve stable permissions

## Outputs

- specialized roles
- canonical mappings
- specialization metadata

---

# 14. Agent 10 — Actor Theme Agent

## Purpose

Generate project-specific actor naming themes.

## Responsibilities

Support:

- Classic
- Heroes
- Change Makers
- Expedition
- Builders
- Custom Story

## Example

Canonical:

project_owner

Display:

Captain

## Important Rule

Theme changes presentation only.

It must never change:

- permissions
- canonical semantics
- responsibility behavior
- orchestration

## Outputs

- theme
- canonical-to-display mappings
- creator-reviewable role names

---

# 15. Agent 11 — Actor Fit Agent

## Purpose

Suggest suitable participants, groups, communities, or organizations for open roles.

## Inputs

Where allowed:

- location
- voluntarily provided skills
- availability
- previous contribution types
- community membership
- organization relationships
- actor capacity

## Responsibilities

- rank possible actors
- explain fit
- respect privacy
- avoid automatic commitment

## Outputs

- recommendations
- fit explanation
- confidence

Core rule:

> Agent suggestion does not equal responsibility acceptance.

---

# 16. Agent 12 — Responsibility Intelligence Agent

## Purpose

Reason about responsibility vacancies and execution accountability.

## Responsibilities

- identify important unfilled responsibilities
- detect responsibilities that may need reassignment
- detect overloaded responsibility structures
- recommend handoff/reassignment
- distinguish primary accountability from supporting participation

## Outputs

- vacancy priority
- reassignment recommendation
- responsibility health
- actor overload warnings

Responsibility state transitions remain deterministic.

---

# 17. Agent 13 — Community and Group Structure Agent

## Purpose

Reason about temporary groups, permanent communities, and project collaboration structure.

## Responsibilities

- suggest when a temporary group is useful
- identify whether a project belongs to an existing community
- reason about multi-community participation
- suggest group decomposition for large projects
- identify when temporary groups could become long-term communities after project completion

Conversion to a permanent community must always require human choice.

## Outputs

- group/community recommendations
- group topology
- collaboration structure

---

# 18. Agent 14 — Organization Participation Agent

## Purpose

Reason about how organizations and companies participate in execution.

## Responsibilities

- identify organization-role needs
- reason about NGO/school/company involvement
- distinguish:
  - sponsor
  - organization partner
  - event host
  - expertise provider
  - executor provider
  - reviewer
- interpret organization offers
- map organization participation to project responsibilities

## Outputs

- proposed organization roles
- participation interpretation
- responsibility mapping

The agent does not automatically contact or commit organizations.

---

# 19. Agent 15 — Scheduling Agent

## Purpose

Reason about people, task, and event timing.

## Responsibilities

- identify candidate times
- reason about actor availability
- reason about task readiness
- avoid scheduling before prerequisites
- coordinate meeting/event timing
- propose scheduling alternatives

## Outputs

- candidate schedules
- timing conflicts
- scheduling recommendations

Actual calendar persistence remains deterministic.

---

# 20. Agent 16 — Event Planning Agent

## Purpose

Create and maintain event execution plans.

## Responsibilities

- determine whether a project task should become an event
- identify event actor roles
- identify event prerequisites
- estimate participant structure
- connect event to project task graph
- propose event plan

## Outputs

- event proposal
- event roles
- prerequisites
- execution links

---

# 21. Agent 17 — Blocker Detection Agent

## Purpose

Identify meaningful execution blockers.

## Inputs

- task states
- responsibility vacancies
- actor availability
- event changes
- support state, including optional externally arranged funding where relevant
- delays
- dependency changes

## Responsibilities

- identify blocker
- classify severity
- identify affected branch
- identify downstream risk
- distinguish local blocker from project-wide blocker

## Outputs

- blocker classification
- affected graph region
- urgency
- suggested next reasoning steps

---

# 22. Agent 18 — Replanning Agent

## Purpose

Generate revised execution plans after project reality changes.

## Triggers

- actor withdrawal
- major delay
- event cancellation
- dependency invalidation
- scope change
- blocker
- support-state change
- new actor capacity

## Responsibilities

- preserve unaffected work
- revise affected branches
- propose sequencing changes
- propose actor restructuring
- update expected completion
- preserve plan lineage

## Outputs

- revised plan proposal
- affected tasks
- revised timeline
- rationale
- confidence

---

# 23. Agent 19 — Acceleration Agent

## Purpose

Continuously look for safe ways to improve execution speed.

## Responsibilities

Ask:

- Can more work run in parallel?
- Is actor capacity now sufficient to split branches?
- Is unrelated work waiting unnecessarily?
- Has a new actor removed a bottleneck?
- Can timeline be compressed?
- Can a branch begin earlier?

## Outputs

- acceleration opportunities
- timeline-compression proposals
- unnecessary-wait warnings

This agent is different from Replanning Agent.

Replanning responds to disruption.

Acceleration proactively searches for improvement.

---

# 24. Agent 20 — Support State Reasoning Agent

## Purpose

Interpret how support state affects execution, including people, organizations, venue, materials, equipment, transport, expertise, and optional externally arranged funding where relevant.

Hatcommways does not process payments.

## Responsibilities

- interpret project support state
- identify tasks affected by insufficient support
- distinguish affected vs unaffected work
- interpret the project's support model, including optional externally arranged funding where relevant
- reason about support-related execution readiness

## Outputs

- affected task set
- support blockers
- unaffected work
- support state explanation

The agent does not raise money or find sponsors.

---

# 25. Agent 21 — Participation and Action Intelligence Agent

## Purpose

Understand how people are participating in project execution.

## Responsibilities

Reason about:

- actor-role participation
- responsibility coverage
- participation concentration
- weak execution areas
- strong execution areas
- community participation patterns

## Outputs

- Action Map interpretations
- participation summaries
- execution-participation insights

Map generation and aggregation remain deterministic.

---

# 26. Agent 22 — Support and Organization Intelligence Agent

## Purpose

Interpret support and organization-participation patterns.

## Responsibilities

- summarize support distribution
- interpret organization participation
- identify which communities/areas are supporting the project
- generate privacy-safe support narratives
- help explain sponsor/organization involvement

## Outputs

- support-map interpretation
- organization participation summary
- organization/support participation narrative

This agent must not expose private contribution data.

---

# 27. Agent 23 — Project Memory Agent

## Purpose

Identify and structure project events, decisions, revisions, failures, execution transitions, and patterns that are candidates for durable memory.

## Responsibilities

Summarize and organize:

- original goal
- task versions
- dependency changes
- actor-role changes
- responsibility changes
- timeline revisions
- blockers
- decisions
- event history
- support state changes
- major execution transitions

## Outputs

- candidate memory entries
- summarized project state
- candidate execution-history interpretations

Durable memory persistence, promotion, supersession, and governed compaction remain controlled by the Memory Writer and validation rules.

Raw system history remains deterministic and append-only.

---

# 28. Agent 24 — Outcome and Blueprint Agent

## Purpose

Understand what happened when the project reaches an outcome.

## Responsibilities

- compare intended goal vs actual outcome
- identify completed work
- identify partial success
- identify unresolved work
- summarize participant and organization contributions
- preserve failures and revisions
- generate reusable project blueprint where privacy allows
- generate project appreciation/outcome summaries

## Outputs

- outcome summary
- execution retrospective
- reusable blueprint
- appreciation summary
- lessons

---

# 29. Current Agent Count

The current product model naturally produces:

> 24 specialized reasoning agents

This count is not a marketing target.

Each agent must continue to justify its existence during implementation.

Possible future outcomes:

- two agents may merge
- an agent may become a deterministic service
- one agent may split because its permissions/state become too different

The architecture may therefore settle around:

22–25 agents

without concern.

---

# 30. Danger Zone

If the product approaches:

26–30 agents

every additional agent should undergo explicit architecture review.

Questions:

- Does it have genuinely different reasoning?
- Does it need different memory?
- Does it require different permissions?
- Does it activate from different events?
- Does it need independent failure/retry handling?
- Would combining it with another agent create unsafe coupling?

If the answer is mostly no:

do not create a new agent.

---

# 31. Agent Activation

Agents should activate from project events and state.

Example:

goal.created
→ Goal Understanding Agent

goal.structured
→ Project Scope Agent
→ Task Decomposition Agent

tasks.proposed
→ Dependency Reasoning Agent
→ Actor Requirement Agent

dependency_graph.ready
→ Timeline Planning Agent
→ Parallelization Agent

actor_structure.ready
→ Actor Capacity Agent
→ Role Specialization Agent

responsibility.accepted
→ Responsibility Intelligence Agent
→ Parallelization Agent
→ Acceleration Agent

actor.withdrawn
→ Blocker Detection Agent
→ Replanning Agent

task.completed
→ Dependency update
→ Timeline reasoning
→ Acceleration reasoning
→ Project Memory Agent

project.completed
→ Outcome and Blueprint Agent

---

# 32. Parallel Agent Activation

One event may activate multiple agents.

Example:

actor.joined

may independently trigger:

- Actor Fit/Responsibility updates
- Parallelization Agent
- Acceleration Agent
- Participation Intelligence Agent
- Project Memory Agent

These agents should not be artificially serialized if their inputs are independent.

## Bounded Strands Graph Execution

The 24 Hatcommways agents must not be modeled as one permanent global graph.

Strands Graph is an execution primitive for a bounded reasoning episode. Hatcommways owns the long-lived project lifecycle, event routing, permissions, versions, decisions, and authoritative state.

Conceptually:

Domain Event
→ Trigger Router
→ identify affected execution region
→ choose relevant agents
→ construct or select a bounded Strands Graph
→ execute independent graph nodes concurrently where dependencies permit
→ merge typed results

A bounded graph run should define:

- graph run id
- source event and correlation id
- affected execution region
- source project, task-graph, actor-graph, and timeline versions
- participating specialized agents
- graph nodes and dependencies
- allowed parallel branches
- fan-out and fan-in points
- completion and failure conditions

Example:

responsibility.accepted

may activate a bounded graph containing:

- Actor Capacity Agent
- Parallelization Agent
- Acceleration Agent

followed by:

- Timeline Planning Agent, if the earlier results demonstrate a material timing effect

Independent nodes may run concurrently. Fan-in occurs through typed proposals rather than free-form agent conversation.

Bounded cyclic refinement may be used only where a reasoning result requires a limited, explicit review or repair cycle. Every cycle must have a stopping condition, attempt limit, and no-progress protection. A graph run must not remain alive for the lifetime of a project.

## Proposal Merger / Conflict Resolver

Several agents in one graph may produce compatible or conflicting proposals.

The Proposal Merger / Conflict Resolver should:

- combine compatible changes that reference the same current state
- preserve the provenance of every contributing agent and memory reference
- detect overlapping or contradictory writes
- reject ambiguous conflicts rather than guessing
- route repair, rerun, or human review where appropriate
- produce a merged typed proposal for deterministic validation

Proposal merging does not make a proposal authoritative. Schema, reference, version, domain-invariant, permission, and approval checks still occur before a domain service may apply a change.

---

# 33. Agent Input Contracts

Each agent should eventually have an explicit typed input contract.

Inputs should contain only the state required by that agent.

Avoid sending the entire project database to every agent.

Example:

Parallelization Agent may receive:

- affected tasks
- dependencies
- active actors
- responsibility relationships
- availability
- current timeline

It does not need:

- private payment instructions
- unrelated project messages
- sponsor contact details

---

# 34. Agent Output Contracts

Agent outputs must be structured.

Avoid depending on free-form text for system transitions.

Example output:

ParallelizationProposal

- affected_task_ids
- currently_serialized
- proposed_parallel_groups
- required_actor_capacity
- estimated_time_saved
- reasoning_summary
- confidence
- source_state_version

The application validates outputs before applying them.

---

# 35. Agent State Versioning

Every reasoning result should reference relevant project state versions.

Examples:

- project_version
- task_graph_version
- actor_graph_version
- timeline_version

Before applying an agent result:

- compare current state
- reject stale result if necessary
- rerun agent when required

This protects concurrent reasoning.

---

# 36. Agent Memory Access

Agents should not all access every form of memory.

Possible memory scopes:

- current project state
- project execution history
- actor history
- organization history
- community history
- cross-project execution patterns
- temporary working memory

Memory access should follow least privilege.

Example:

Actor Theme Agent does not need sponsor financial history.

Support Intelligence Agent does not need private user conversations unrelated to support.

---

# 37. Agent Write Permissions

Agents should also have limited write authority.

Most agents should generate:

- proposals
- classifications
- structured reasoning results

Deterministic services then decide whether those results may become persisted state.

Examples:

Task Decomposition Agent:
may propose tasks

Project Plan Service:
persists approved tasks

Replanning Agent:
may propose revised plan

Project Owner / policy:
may approve consequential changes

---

# 38. Human Approval Categories

Human approval is required for actions such as:

- accepting responsibility
- committing a person
- committing an organization
- publishing a project
- major project scope change
- changing project visibility
- public demographic-map activation
- certain organization/sponsor attribution changes
- project cancellation

Agents may propose these actions.

They do not silently execute them.

---

# 39. Safe Autonomous Actions

Agents may autonomously perform or trigger safe internal work such as:

- recomputing planning suggestions
- identifying parallel work
- detecting blockers
- generating map summaries
- updating internal planning analysis
- generating memory summaries
- identifying stale timelines
- creating non-consequential notifications

The exact action policy will be defined separately.

---

# 40. Agent Failure Isolation

One agent failure must not destroy unrelated project execution.

Example:

Support Intelligence Agent fails.

Task execution should continue.

Map narrative may temporarily be unavailable.

Similarly:

Actor Theme Agent failure

must not prevent project execution using canonical role names.

Core principle:

> Optional intelligence failure must not break execution truth.

---

# 41. Retry Policy

Agents may have retry policies based on failure type.

Examples:

- model timeout
- malformed structured output
- tool failure
- stale state
- transient infrastructure failure

Retries must be:

- bounded
- auditable
- idempotent where appropriate

---

# 42. No-Progress Protection

The orchestrator should detect agent loops.

Example:

Agent repeatedly proposes the same invalid plan.

The system should:

- stop repeated attempts
- record failure state
- surface human review if required

Do not allow unbounded autonomous loops.

---

# 43. Agent Observability

Every agent run should record:

- agent id/type
- trigger event
- project id
- run id
- input state version
- start time
- end time
- result status
- output reference
- tool usage
- failure reason
- retry count

This is required for debugging and governance.

---

# 44. Agent Cost Awareness

Agents should not rerun unnecessarily.

Potential strategies:

- affected-region reasoning
- event filtering
- state-delta inputs
- cached stable reasoning
- deterministic prechecks
- avoid invoking LLM when no ambiguity exists

Example:

If task dependency state can be recalculated deterministically:

do not call an agent.

---

# 45. Agent Trigger Categories

Possible trigger families:

## Goal Triggers

- goal.created
- goal.changed

## Task Triggers

- task.created
- task.completed
- task.blocked

## Actor Triggers

- actor.joined
- actor.available
- actor.unavailable

## Responsibility Triggers

- responsibility.opened
- responsibility.accepted
- responsibility.withdrawn

## Event Triggers

- event.created
- event.scheduled
- event.rescheduled

## Support Triggers

- support.state_changed
- contribution.updated
- sponsor.joined

## Execution Triggers

- blocker.created
- blocker.resolved
- timeline.changed
- project.scope_changed

## Lifecycle Triggers

- project.published
- project.paused
- project.completed

---

# 46. Agent-to-Agent Communication

Agents should generally communicate through:

- persisted state
- typed proposals
- events

rather than free-form direct agent conversations.

Preferred model:

Agent A
→ structured result
→ persisted/validated state
→ event
→ Agent B

This improves:

- auditability
- replay
- debugging
- concurrency
- deterministic boundaries

Direct agent-to-agent calls should exist only when there is a strong architectural reason.

---

# 47. Orchestrator

Hatcommways requires a governed orchestration layer.

The orchestrator is not counted as one of the 24 product agents.

Core principle:

> The orchestrator performs deterministic routing and governance; it does not replace specialized agent reasoning.

Responsibilities:

- consume events
- determine affected domain
- run deterministic prechecks
- select eligible agents
- enforce concurrency rules
- manage state versions
- enforce permissions
- handle retries
- record audit data
- prevent no-progress loops
- route human decisions
- persist validated results

For reasoning-heavy events, the orchestrator also resolves the affected execution region, constructs/selects the bounded Strands Graph, tracks graph completion, and routes typed proposals through merge and validation boundaries.

---

# 48. Execution Example

Goal:

Build 20 shelters for street dogs.

Initial flow:

Goal Understanding Agent
+
Project Scope Agent

produce structured goal/scope.

Task Decomposition Agent
creates task proposal.

Dependency Reasoning Agent
creates dependency proposal.

Actor Requirement Agent
creates actor-role structure.

Actor Capacity Agent
determines counts.

Timeline Planning Agent
+
Parallelization Agent

generate initial execution model.

Creator approves.

Project is published.

Users begin joining responsibilities.

Actor joins.

Event emitted:

responsibility.accepted

This may activate in parallel:

Responsibility Intelligence Agent
Parallelization Agent
Acceleration Agent
Participation Intelligence Agent
Project Memory Agent

The system discovers:

two previously serial tasks can now execute independently.

Timeline proposal changes.

Execution continues.

Later:

an actor withdraws.

Blocker Detection Agent
+
Replanning Agent

activate.

Unaffected branches continue.

The final project completes.

Outcome and Blueprint Agent
creates the structured outcome and reusable execution history.

---

# 49. Initial Agent Registry

Current proposed registry:

1. Goal Understanding Agent
2. Project Scope Agent
3. Task Decomposition Agent
4. Dependency Reasoning Agent
5. Timeline Planning Agent
6. Parallelization Agent
7. Actor Requirement Agent
8. Actor Capacity Agent
9. Role Specialization Agent
10. Actor Theme Agent
11. Actor Fit Agent
12. Responsibility Intelligence Agent
13. Community and Group Structure Agent
14. Organization Participation Agent
15. Scheduling Agent
16. Event Planning Agent
17. Blocker Detection Agent
18. Replanning Agent
19. Acceleration Agent
20. Support State Reasoning Agent
21. Participation and Action Intelligence Agent
22. Support and Organization Intelligence Agent
23. Project Memory Agent
24. Outcome and Blueprint Agent

---

# 50. Final Principle

Hatcommways agents are not characters talking to one another for show.

They are specialized reasoning workers inside a governed execution system.

Their job is to continuously answer questions such as:

- What does this community want to make happen?
- What work is required?
- What depends on what?
- What can happen in parallel?
- What kinds of actors are needed?
- Is enough execution capacity available?
- What changed?
- What is blocked?
- Can the project move faster?
- What should be replanned?
- How is the community participating?
- What should be remembered?
- What outcome was actually achieved?

The agents provide intelligence.

The platform provides truth, permissions, state, auditability, and execution control.
