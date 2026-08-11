# Hatcommways — Core Domain Model

## 1. Purpose

This document defines the core domain objects of Hatcommways and the relationships between them.

These definitions are authoritative for the product.

Codex must not collapse different concepts into one model.

The most important distinction is:

> Tasks define work and timeline.
> Actors define responsibility.

Hatcommways must keep those two systems separate and connect them during execution.

---

# 2. Core Domain Objects

The initial core domain objects are:

- Goal
- Project
- Task
- Dependency
- Timeline
- Actor Role
- Responsibility
- Participant
- Organization
- Group
- Community
- Event
- Funding Mode
- Funding State
- Contribution
- Map View
- Project State
- Outcome
- Project Memory

These objects may later gain subtypes, but their conceptual boundaries must remain stable.

---

# 3. Goal

A Goal describes:

> What does the creator want to make happen?

Examples:

- build shelters for street dogs before monsoon
- organize a neighborhood cleanup
- run a robotics workshop for local students
- restore a playground
- organize a community food-support event

The Goal is not the task list.

It is the desired real-world outcome.

A Goal may contain:

- title
- natural-language description
- location
- expected timeframe
- creator
- attached group/community
- funding mode
- visibility
- initial known context

The Goal is interpreted by AI and converted into a Project execution structure.

---

# 4. Project

A Project is the persistent execution container for a Goal.

A Project contains:

- one primary goal
- tasks
- dependencies
- timeline
- actor-role requirements
- responsibilities
- participants
- organizations
- groups/communities
- events
- support/funding state
- maps
- revisions
- execution history
- outcome

A Project may last:

- hours
- days
- weeks
- months

Projects are not required to be public.

Possible visibility states may include:

- public
- community-only
- controlled
- invite-only
- private

---

# 5. Task

A Task represents:

> A unit of work that must happen for the project to progress.

Examples:

- identify locations
- prepare project design
- organize materials
- arrange transport
- conduct installation
- coordinate participants
- perform final review

A Task is not a person.

A Task is not an actor role.

A Task is not a resource.

A Task mainly contributes to:

- execution structure
- sequencing
- dependencies
- estimated timing
- project readiness
- timeline calculation

A Task may contain:

- task id
- project id
- title
- description
- status
- estimated duration
- earliest possible start
- latest acceptable completion
- dependencies
- child tasks
- parent task
- relevant actor roles
- active responsibilities
- execution readiness
- completion evidence
- revision history

---

# 6. Task Status

Possible conceptual task states include:

- proposed
- planned
- waiting
- ready
- active
- blocked
- paused
- completed
- cancelled
- superseded

The exact state machine will be defined separately.

A task can be logically ready while still not executable.

Example:

All dependencies are satisfied.

But nobody has accepted the required responsibility.

Therefore:

logical_ready = true
execution_ready = false

This distinction is fundamental.

---

# 7. Dependency

A Dependency represents:

> A condition that affects whether a task can proceed.

Typical dependency:

Task B requires Task A to finish.

But dependencies may also later represent other execution conditions.

Initial dependency types may include:

- finish-to-start
- finish-to-finish
- start-to-start
- explicit prerequisite
- event prerequisite
- approval prerequisite
- responsibility prerequisite

The first implementation does not need every scheduling dependency type immediately, but the model must not assume all dependencies are simple linear chains.

Dependencies help determine:

- task readiness
- parallel execution
- blocking relationships
- timeline changes

---

# 8. Timeline

The Timeline is a derived execution structure.

It answers:

> When can the project work happen?

The Timeline is generated from:

- tasks
- dependencies
- estimated durations
- actor availability
- responsibility acceptance
- event timing
- delays
- blockers
- new execution capacity

The Timeline must never be treated as permanently fixed.

Core rule:

> Timeline is dynamic state derived from execution reality.

If new actors join, tasks may move earlier.

If actors leave, tasks may move later.

If independent tasks gain independent owners, sequential work may become parallel.

If a dependency changes, downstream timing may change.

---

# 9. Actor Role

An Actor Role represents:

> A kind of responsibility required by the project.

Examples:

- project owner
- organizer
- coordinator
- task owner
- executor
- specialist
- reviewer
- organization representative
- sponsor representative
- event host
- communication lead

Actor Role is a role definition.

It is not necessarily a specific person.

A project may require:

- 1 organizer
- 3 task owners
- 10 executors
- 1 specialist
- 2 reviewers

Actor-role requirements are generated based on:

- project scale
- project type
- task structure
- duration
- complexity
- execution stage
- specialist needs
- organization involvement

---

# 10. Canonical Actor Roles and Display Names

Hatcommways keeps canonical actor-role semantics internally.

Example:

canonical_role = coordinator

A creator may choose a themed display name:

display_name = Strategist

The canonical role controls:

- permissions
- responsibility semantics
- orchestration
- analytics
- execution behavior

The display name controls only:

- UI
- storytelling
- project identity

Core rule:

> Theme changes presentation, never execution semantics.

---

# 11. Responsibility

A Responsibility represents:

> Accountability accepted by an actor for part of project execution.

This is different from a Task.

A task answers:

> What must happen?

A responsibility answers:

> Who has agreed to carry accountability for making part of that execution happen?

Responsibilities may be attached to:

- a task
- a group of tasks
- an event
- a coordination function
- a review function
- a project-wide function

Examples:

- Priya accepts responsibility for organizing the installation event
- Ravi accepts responsibility for Task 4
- Welfare Group A accepts responsibility for field coordination
- Company Representative B accepts responsibility for sponsor communication

A responsibility may contain:

- responsibility id
- project id
- canonical actor role
- display actor role
- responsible participant or organization
- related task/event
- scope
- status
- accepted timestamp
- expected availability
- handoff state
- completion state
- withdrawal state

---

# 12. Responsibility State

Conceptual states may include:

- open
- offered
- requested
- accepted
- active
- fulfilled
- declined
- withdrawn
- reassignment_required
- cancelled

No AI agent may silently create a human commitment.

Core rule:

> Agents coordinate commitments. Humans make commitments.

AI may:

- identify needed responsibility
- suggest an actor
- request participation
- propose reassignment

AI may not:

- accept responsibility for a human
- promise a person's time
- commit an organization without authorization

---

# 13. Participant

A Participant is an individual person participating in Hatcommways.

A Participant may:

- create projects
- join groups
- join communities
- accept responsibilities
- attend events
- organize tasks
- contribute support
- represent an organization where authorized

One participant may hold multiple responsibilities.

Example:

Participant A may be:

- project creator
- organizer
- task owner for Task 2

These are separate responsibility records, not one merged role.

---

# 14. Organization

An Organization is a persistent non-individual actor.

Examples:

- NGO
- animal welfare group
- school
- nonprofit
- local organization
- resident body
- company
- sponsor organization

An Organization can:

- create projects
- join projects
- assign representatives
- accept organizational responsibilities
- contribute people
- contribute expertise
- support events
- provide sponsorship/support
- receive project communication
- participate in meetings

Organizations must not be reduced to sponsors.

They are full execution actors.

---

# 15. Organization Representative

An Organization Representative is a Participant authorized to act on behalf of an Organization.

Example:

Company X is an organization.

An employee may participate as:

organization_representative
for Company X

The system must distinguish:

- the person
- the organization
- the person's authority to represent that organization

This becomes important for:

- meetings
- commitments
- organization responsibility
- sponsor support
- approvals

---

# 16. Group

A Group is a collection of participants connected around execution.

Groups may be temporary or persistent.

A Group may:

- create a project
- participate in a project
- support a project
- organize members
- carry group-level responsibility

---

# 17. Temporary Group

A Temporary Group exists primarily for one project or event.

Examples:

- Street Dog Shelter Jaipur Team
- Sunday Lake Cleanup Group
- School Robotics Workshop Volunteers

A Temporary Group may be created automatically or manually during project formation.

After project completion it may:

- become inactive
- remain archived
- convert into a permanent community if members choose

---

# 18. Permanent Community

A Permanent Community exists beyond one project.

Examples:

- neighborhood community
- animal welfare network
- school community
- environmental group
- maker community
- resident association

A Permanent Community may:

- run multiple projects
- have recurring members
- maintain community history
- create temporary subgroups
- attach projects
- provide recurring actors

Location may be one dimension of community identity but is not required for every community.

---

# 19. Event

An Event is a time-bound activity.

Examples:

- meeting
- workshop
- cleanup day
- build session
- installation event
- volunteer session
- testing event
- community gathering

An Event may be:

- standalone
- attached to a project
- attached to one or more tasks
- dependent on task readiness

Event is not equivalent to Project.

A Project may contain many Events.

---

# 20. Event State

Conceptual states may include:

- proposed
- scheduling
- scheduled
- ready
- active
- completed
- postponed
- cancelled

An Event may require:

- confirmed participants
- responsible organizer
- prerequisite tasks
- location
- time
- organization approval

The scheduling system must not assume that an event can occur just because a date exists.

---

# 21. Funding Mode

Funding Mode describes:

> How the project expects its money requirement to be satisfied.

Possible initial values:

- none_required
- self_funded
- group_funded
- community_funded
- sponsor_supported
- mixed

Funding Mode is descriptive execution state.

Hatcommways does not initially process payments.

---

# 22. Funding State

Funding State represents the current project-level financial execution status.

Possible conceptual values:

- not_required
- unknown
- being_arranged
- partially_ready
- sufficient
- insufficient
- blocked
- completed

The exact money values may remain private to authorized users.

Funding state may affect execution readiness.

Example:

Task X cannot begin until sufficient funding has been confirmed manually.

---

# 23. Payment Instructions

Hatcommways may store instructions describing how an authorized participant can contribute financially.

Examples:

- UPI/payment address
- external payment link
- bank/payment contact
- organization payment instructions

Payment instructions are sensitive information.

They must:

- be access controlled
- not appear on public maps
- not appear on public project pages by default
- not be indexed for public discovery

Hatcommways initially does not verify or process the transaction.

---

# 24. Contribution

A Contribution represents support provided toward the project.

Contribution types may eventually include:

- financial
- human participation
- organizational participation
- expertise
- equipment
- service
- venue
- other support

However, contribution must not replace Responsibility.

Example:

A sponsor may contribute money but carry no execution responsibility.

A volunteer may carry responsibility but contribute no money.

These concepts must remain distinct.

---

# 25. Money Contribution

A Money Contribution may include:

- contributor type
- contributor reference if visibility permits
- project
- amount
- contribution category
- manually confirmed state
- visibility level
- associated organization/community
- geographic aggregation metadata where allowed

The first product version may rely on manual confirmation.

The application must never claim that a manually entered payment is independently verified.

---

# 26. Project Maps

Maps are views derived from project execution/support data.

Maps are not separate projects or separate data stores.

Initial map categories:

- Action Map
- Money / Support Map
- Sponsor / Organization Map
- optional analytics maps

---

# 27. Action Map

Action Map answers:

> Where and how is execution participation happening?

Possible inputs:

- participant location at an appropriate privacy level
- actor roles
- responsibility participation
- groups
- communities
- execution activity

It may visualize:

- participant concentration
- actor distribution
- action strength
- open responsibility areas
- community involvement

Action Map is the primary map type.

---

# 28. Money / Support Map

Money / Support Map answers:

> Where and how is financial support forming around this project?

It must operate on aggregated data.

It may visualize:

- area contribution strength
- community contribution strength
- sponsor/company participation
- contributor-category distribution

It must not publicly expose:

- payment addresses
- private transaction details
- private donor identity unless explicitly allowed

---

# 29. Sponsor / Organization Map

This map represents organizational participation around a specific project.

Possible data:

- organizations involved
- support type
- location
- organizational role
- contribution intensity

This map is project-centric.

It must not automatically expose the organization's complete historical support profile.

---

# 30. Optional Analytics Maps

Optional analytics may include:

- age bands
- community type
- participant category
- geographic segment
- local vs external support
- first-time vs repeat contributor

These should be:

- aggregated
- privacy protected
- creator-controlled
- disabled by default unless explicitly selected

---

# 31. Project State

Project State represents the overall execution lifecycle.

Conceptual states may include:

- draft
- planning
- awaiting_creator_review
- published
- recruiting
- active
- blocked
- paused
- completing
- completed
- cancelled
- archived

The exact state machine will be defined separately.

Project state is influenced by:

- task state
- actor availability
- responsibility state
- event state
- funding state
- creator decisions

---

# 32. Outcome

Outcome represents:

> What actually happened because the project was executed?

Outcome is not simply:

project_status = completed

It may contain:

- achieved goal
- partially achieved goal
- final state
- completed tasks
- cancelled tasks
- participants
- events
- organizations
- final support state
- impact summary
- evidence
- lessons
- unresolved work

Outcome history should preserve failure and revision rather than hiding them.

---

# 33. Project Memory

Project Memory preserves the execution history of the project.

It may include:

- original goal
- goal revisions
- generated task structures
- dependency changes
- timeline versions
- actor-role changes
- responsibility acceptance/withdrawal
- project decisions
- blockers
- replanning decisions
- events
- support state changes
- completed outcomes

Project Memory is not simply conversation history.

It is structured execution memory.

---

# 34. Primary Relationships

The most important relationships are:

Goal
→ creates
Project

Project
→ contains
Tasks

Task
→ may depend on
Task

Tasks + Dependencies
→ derive
Timeline

Project
→ requires
Actor Roles

Actor Role
→ may become
Responsibility

Participant / Organization
→ accepts
Responsibility

Responsibility
→ may relate to
Task / Event / Project

Project
→ contains
Events

Project
→ may belong to
Temporary Group / Permanent Community

Project
→ may involve
Organizations

Project
→ has
Funding Mode + Funding State

Project execution data
→ derives
Maps

Project history
→ becomes
Project Memory

Project completion
→ produces
Outcome

---

# 35. Execution Readiness

A task should not be considered executable merely because dependencies are complete.

Execution readiness may depend on:

- logical dependencies satisfied
- required responsibility accepted
- responsible actor available
- event prerequisite satisfied
- required approval available
- required project state
- funding state where applicable

Conceptually:

logical_readiness
+
actor_readiness
+
project_conditions
=
execution_readiness

This calculation should be deterministic wherever possible.

AI may reason about ambiguous planning conditions, but final execution state should be persisted explicitly.

---

# 36. Parallel Execution

Parallelism is a core product behavior.

Tasks may run in parallel when:

- no dependency prevents it
- sufficient independent responsibility exists
- actor availability allows it
- project conditions allow it

The system must support:

- multiple active tasks
- multiple active actors
- multiple concurrent agents
- independent event branches

Adding new actors may increase execution parallelism.

Removing actors may decrease parallelism.

---

# 37. Replanning

Replanning occurs when execution reality changes.

Triggers may include:

- actor joins
- actor withdraws
- task delayed
- task completed early
- dependency changes
- event postponed
- funding state changes
- project scope changes
- new responsibility accepted
- blocker created

Replanning may modify:

- timeline
- task sequencing
- parallel execution
- responsibility vacancies
- event schedule

Replanning must preserve history.

Never overwrite prior plans without keeping revision lineage.

---

# 38. Domain Invariants

These rules must always remain true.

## Invariant 1

Task != Responsibility

## Invariant 2

Actor Role != Participant

## Invariant 3

Participant != Organization

## Invariant 4

Project != Event

## Invariant 5

Funding State != Payment Processing

## Invariant 6

Contribution != Responsibility

## Invariant 7

Timeline is derived and revisable, not immutable truth.

## Invariant 8

An AI suggestion does not equal a human commitment.

## Invariant 9

Themed actor names never alter canonical permissions or semantics.

## Invariant 10

Public map data must not automatically expose private personal or payment information.

---

# 39. Core Mental Model

Hatcommways should always be understood through these connected structures:

## Work Structure

Goal
→ Tasks
→ Dependencies
→ Dynamic Timeline

## Responsibility Structure

Project
→ Actor Roles
→ Responsibilities
→ Participants / Organizations

## Social Structure

Participants
→ Temporary Groups
→ Permanent Communities
→ Organizations

## Support Structure

Project
→ Funding Mode
→ Funding State
→ Contributions

## Execution Structure

Tasks
+
Responsibilities
+
Actor Availability
+
Events
+
Project Conditions
→ Execution Readiness

## Observation Structure

Execution + Participation + Support
→ Maps + Analytics

## Knowledge Structure

Execution History
→ Project Memory
→ Outcome

---

# 40. Final Domain Principle

Hatcommways does not simply assign people to a checklist.

It maintains two independent but connected systems:

> A graph of what needs to happen.

and

> A graph of who is responsible for making it happen.

The dynamic timeline emerges from the relationship between those two systems.

That separation is foundational to Hatcommways and must be preserved throughout backend, frontend, agent, data, and orchestration design.