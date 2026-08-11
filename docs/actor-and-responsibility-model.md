# Hatcommways — Actor and Responsibility Model

## 1. Purpose

This document defines how Hatcommways determines:

- what actor roles a project needs
- how many actors are required
- how those roles change by project size and type
- how humans, groups, and organizations occupy those roles
- how responsibility is accepted, transferred, completed, or reopened
- how themed actor names work without changing execution semantics

This document is authoritative for actor planning.

Core principle:

> Tasks define the work.
> Actors define responsibility.

Hatcommways must never confuse actors with resources.

Money, equipment, venue, materials, transport, and information are not actors.

---

# 2. What Is an Actor?

An Actor is an entity capable of carrying responsibility in project execution.

An actor may be:

- an individual participant
- a temporary group
- a permanent community
- an organization
- a company
- an authorized representative acting for an organization

An actor is not simply someone who appears in the project.

An actor becomes relevant when they carry or participate in execution responsibility.

---

# 3. Actor Role vs Actor

These are different concepts.

## Actor Role

An Actor Role describes:

> What kind of responsibility needs to be carried?

Examples:

- Project Owner
- Organizer
- Coordinator
- Task Owner
- Executor
- Specialist
- Reviewer
- Organization Representative
- Event Host

## Actor

An Actor is the actual entity occupying that role.

Example:

Role:
Event Organizer

Actor:
Priya Sharma

or:

Role:
Organization Partner

Actor:
Green Paws Welfare Society

The same actor may occupy multiple roles.

The same role may also require multiple actors.

---

# 4. Canonical Actor Role Families

Hatcommways should maintain a reusable canonical actor-role taxonomy.

The taxonomy must remain broad enough to support many project domains while allowing project-specific specialization.

Initial actor-role families:

1. Ownership
2. Planning
3. Coordination
4. Execution
5. Specialist
6. Review / Validation
7. Organization Representation
8. Support / Sponsorship
9. Event Operation
10. Communication / Outreach
11. Approval / Authority
12. Advisory / Guidance

These are role families, not necessarily the final UI labels.

---

# 5. Ownership Roles

Ownership roles carry accountability for an outcome.

Examples:

- Project Owner
- Project Co-owner
- Task Owner
- Branch Owner
- Event Owner

## Project Owner

The Project Owner carries overall accountability for the project.

The Project Owner may:

- approve the initial AI-generated plan
- publish the project
- approve major scope changes
- control project visibility
- approve public map settings
- manage project administrators
- close or cancel the project
- approve major replanning decisions

The Project Owner does not need to execute every task.

---

## Task Owner

A Task Owner carries accountability for a specific task or task branch.

They are responsible for ensuring the task reaches completion.

They may:

- coordinate executors
- report blockers
- accept task-specific decisions
- update progress
- request help
- complete or submit the task for review

A Task Owner may or may not perform the actual execution work.

---

# 6. Planning Roles

Planning roles help shape execution before or during the project.

Examples:

- Planner
- Schedule Planner
- Event Planner
- Branch Planner

Planning responsibilities may include:

- refining task structure
- estimating time
- coordinating sequence
- proposing changes
- maintaining local plan details

The AI performs much of the planning intelligence, but human planning roles may still exist where judgment or local knowledge is needed.

---

# 7. Coordination Roles

Coordination roles keep multiple actors aligned.

Examples:

- Project Coordinator
- Volunteer Coordinator
- Team Coordinator
- Organization Coordinator
- Event Coordinator

A Coordinator may:

- manage communication
- track participant readiness
- organize handoffs
- help schedule actors
- detect missing confirmations
- escalate blockers
- coordinate multiple task owners

Coordination is not the same as ownership.

A person may coordinate work without owning the final task outcome.

---

# 8. Execution Roles

Execution roles perform the actual work required by the task.

Examples:

- Executor
- Volunteer
- Builder
- Participant
- Operator
- Field Worker

Execution roles may be:

- individual
- team-based
- temporary
- recurring

A task may require:

- one executor
- several executors
- a minimum number of executors
- a maximum safe/useful number of executors

Hatcommways should support capacity requirements.

Example:

Task:
Install shelters

Required executor capacity:
4–6 people

Current:
3 joined

Status:
execution capacity incomplete

---

# 9. Specialist Roles

Specialist roles are used where specific expertise is required.

Examples:

- Electronics Specialist
- Accessibility Specialist
- Animal Welfare Specialist
- Safety Specialist
- Design Specialist
- Legal/Permission Advisor
- Technical Reviewer

Project-specific specialist names may vary.

Internally they inherit from:

specialist

Example:

canonical_role:
specialist

specialization:
electronics

display_name:
Circuit Guide

This allows niche projects without creating unrelated role logic for every domain.

---

# 10. Review and Validation Roles

Some work needs independent checking.

Possible roles:

- Reviewer
- Validator
- Quality Checker
- Safety Reviewer
- Outcome Reviewer

The system may require separation between:

executor

and

reviewer

when appropriate.

Example:

A person who completed a task may submit it.

A different reviewer may confirm completion.

This should be configurable based on project complexity and risk.

---

# 11. Organization Representation Roles

Organizations participate through authorized actors.

Roles include:

- Organization Representative
- Community Representative
- NGO Representative
- School Representative
- Company Representative
- Sponsor Representative

The system must distinguish:

- the organization
- the representative
- the representative's authority
- the responsibility being carried

A representative should not automatically have authority over every organization action.

---

# 12. Sponsor / Support Roles

Sponsors are actors only when they have a responsibility or recognized support relationship.

Possible roles:

- Sponsor Representative
- Support Coordinator
- Funding Contact

Hatcommways does not automatically find sponsors.

Sponsors may:

- discover a project
- be contacted by a user
- request a meeting
- offer support
- accept a support-related responsibility

The actual money movement happens outside Hatcommways initially.

---

# 13. Event Roles

Events may require their own actor structure.

Possible roles:

- Event Owner
- Event Organizer
- Event Coordinator
- Host
- Participant Lead
- Volunteer Lead
- Check-in Coordinator
- Activity Lead
- Reviewer

An event inside a larger project may have its own roles independent of project-wide roles.

Example:

Project Owner:
Asha

Installation Event Owner:
Ravi

Event Coordinator:
Meera

These should remain separate responsibility records.

---

# 14. Communication and Outreach Roles

Some projects need dedicated communication responsibility.

Examples:

- Outreach Lead
- Community Communicator
- Participant Communication Lead
- Media/Update Coordinator

These roles may handle:

- project updates
- participant communication
- community announcements
- event reminders
- sponsor/organization contact

Hatcommways agents may automate routine communication, but human accountability may still be needed.

---

# 15. Approval / Authority Roles

Some projects require actors who can approve or authorize execution.

Examples:

- Community Administrator
- Organization Approver
- Venue Authority
- School Approver
- Project Approver

These roles are distinct from reviewers.

Reviewer:
determines whether work is satisfactory.

Approver:
has authority to permit an action.

The exact domain may vary, but the semantic distinction should remain.

---

# 16. Advisory Roles

Some people contribute guidance without carrying execution ownership.

Examples:

- Advisor
- Guide
- Mentor
- Subject Expert

An Advisor may:

- answer questions
- review plans
- suggest alternatives
- guide task owners

They should not automatically become responsible for execution.

---

# 17. Actor Role Generation

Hatcommways should not assign every possible actor role to every project.

The Actor Planning Agent should generate a project-specific actor structure based on:

- goal
- task graph
- project scale
- estimated duration
- number of parallel branches
- event count
- project complexity
- number of expected participants
- organization involvement
- specialist requirements
- approval requirements
- review requirements
- geographic distribution
- project stage

Core rule:

> Actor topology is generated from execution needs.

---

# 18. Small Project Actor Model

A small project may require very few roles.

Example:

Goal:
Run a neighborhood cleanup with 8 people.

Possible actor plan:

- 1 Project Owner
- 1 Organizer
- 6–8 Participants

The creator may occupy both:

Project Owner
+
Organizer

The platform should not artificially generate:

- branch managers
- multiple reviewers
- separate communication teams
- unnecessary hierarchy

Minimal projects should remain lightweight.

---

# 19. Medium Project Actor Model

Example:

Goal:
Run a two-day community robotics workshop.

Possible roles:

- 1 Project Owner
- 1 Project Coordinator
- 2 Task Owners
- 2 Specialists
- 6 Volunteers
- 1 Event Coordinator
- 1 Organization Representative

The actor structure should reflect actual execution complexity.

---

# 20. Large Project Actor Model

Example:

Goal:
Restore multiple public spaces across a city over two months.

Possible structure:

- 1 Project Owner
- 2 Program Coordinators
- several Branch Owners
- multiple Task Owners
- local Team Leads
- Executors / Volunteers
- Specialists
- Reviewers
- Organization Representatives
- Sponsor Representatives
- Event Coordinators
- Communication Lead

Large projects may form multiple parallel actor branches.

Hatcommways must support hierarchical responsibility without turning the platform into a fixed enterprise org chart.

---

# 21. Niche Project Actor Model

Niche projects may require domain-specific roles.

Example:

Robotics Project:

- Project Owner
- Technical Coordinator
- Mechanical Specialist
- Electronics Specialist
- Software Specialist
- Build Executors
- Test Reviewer

Example:

Accessibility Project:

- Project Owner
- Community Coordinator
- Accessibility Specialist
- Field Participants
- Validation Reviewer

Example:

Animal Welfare Event:

- Project Owner
- Organizer
- Welfare Organization Representative
- Volunteer Coordinator
- Field Participants
- Event Coordinator

Domain-specific names should map to canonical roles.

---

# 22. Role Cardinality

Actor roles should support cardinality.

Examples:

Project Owner:
exactly 1

Coordinator:
1–3

Executors:
5–10

Reviewer:
minimum 1

Specialist:
optional 0–2

The actor planner may determine:

- minimum required
- ideal count
- maximum useful count

Example:

role:
executor

minimum:
4

ideal:
6

maximum:
8

This helps execution readiness.

---

# 23. Required vs Optional Roles

Every generated actor role should be classified.

Possible requirement levels:

- required
- recommended
- optional
- conditional

Example:

Small cleanup:

Organizer:
required

Reviewer:
optional

Large technical build:

Technical Specialist:
required

Independent Reviewer:
recommended

This prevents over-structuring simple projects.

---

# 24. Responsibility Scope

A responsibility can have several scopes.

Possible scopes:

- project-wide
- branch
- task
- event
- review
- organization relationship
- communication
- support

Example:

Project Coordinator:
project-wide

Task Owner:
task scope

Event Host:
event scope

Reviewer:
review scope

The scope must be explicit.

---

# 25. Responsibility Creation

A responsibility may be created when:

- project plan is generated
- task is added
- event is created
- project grows
- actor capacity becomes insufficient
- a specialist need appears
- a reviewer becomes necessary
- an actor withdraws
- replanning creates a new role requirement

Responsibilities may therefore appear dynamically during execution.

---

# 26. Open Responsibilities

Before an actor accepts a responsibility, it exists as an open responsibility.

Example:

Open role:
Event Coordinator

Needed:
1

Filled:
0

A public project page may expose open responsibilities according to visibility settings.

Users should be able to browse:

- what role is needed
- what it means
- expected time
- related task/event
- location
- estimated commitment
- prerequisites
- whether approval is required to join

---

# 27. Responsibility Acceptance

A human or authorized organization must explicitly accept responsibility.

Possible flow:

open
→ requested / offered
→ accepted
→ active
→ fulfilled

No agent may silently move:

open
→ accepted

for a human actor.

---

# 28. Responsibility Assignment Modes

Responsibilities may be filled in several ways.

## Self-claim

A user sees an open responsibility and requests/claims it.

## Creator invitation

Project owner invites someone.

## Agent suggestion

AI recommends a suitable actor.

The actor must still accept.

## Organization assignment

An authorized organization representative assigns or proposes an internal participant where policy permits.

## Group assignment

A group nominates someone, subject to that person's acceptance where required.

---

# 29. Responsibility Vacancy

A responsibility becomes vacant when:

- nobody has accepted it
- actor withdraws
- actor becomes unavailable
- responsibility is reopened
- actor is removed
- project changes
- additional capacity is required

Vacancy should be explicit.

Example:

role_required:
Task Owner

needed:
2

filled:
1

vacancies:
1

---

# 30. Actor Withdrawal

Actors must be able to withdraw responsibly.

Possible outcomes:

- responsibility becomes vacant
- handoff requested
- replacement sought
- downstream task becomes blocked
- timeline recalculated

Withdrawal must preserve history.

Do not delete the actor's prior involvement.

---

# 31. Responsibility Transfer

A responsibility may be transferred.

Example:

Ravi
→ Task Owner

Ravi withdraws.

Meera accepts handoff.

History should preserve:

Ravi:
previous owner

Meera:
current owner

The responsibility lineage must remain auditable.

---

# 32. Multiple Actors on One Responsibility

Some responsibilities may have:

- one owner
- multiple executors
- co-owners
- one lead + supporting actors

Example:

Task Owner:
1 lead

Executors:
6 participants

The system should distinguish primary accountability from supporting participation.

---

# 33. One Actor Across Multiple Responsibilities

One participant may hold multiple responsibilities.

Example:

Asha:

- Project Owner
- Organizer
- Event Host

This is allowed.

However, Hatcommways should eventually reason about overload.

The system may warn:

> This actor currently carries 6 active responsibilities across 3 projects.

But it should not automatically remove responsibilities.

---

# 34. Actor Availability

Availability affects execution.

Availability may include:

- date/time availability
- project-level availability
- event availability
- temporary unavailable
- fully unavailable

A responsibility can remain accepted while execution is temporarily unavailable.

Example:

accepted = true

available_now = false

This may affect the timeline.

---

# 35. Actor Capacity

Actors have limited execution capacity.

Potential dimensions:

- active responsibility count
- expected hours
- concurrent projects
- role complexity

Hatcommways may use capacity to:

- warn about overload
- avoid poor recommendations
- improve timeline planning
- identify need for additional actors

Capacity is not a social score.

---

# 36. Actor Readiness

Actor readiness for a task may require:

- accepted responsibility
- current availability
- required role qualification
- organization authorization where applicable
- task not blocked

Actor readiness contributes to task execution readiness.

---

# 37. Actor-Driven Parallelization

This is a core intelligence feature.

Suppose:

Task A
Task B
Task C

have no logical dependencies.

Initially:

one actor can execute all three.

The timeline may be:

A
→ B
→ C

Later:

two more suitable actors join.

Now the system may replan:

A
B
C

in parallel.

Therefore:

> Actor availability can change timeline topology.

This must be supported explicitly.

---

# 38. Actor-Driven De-Parallelization

The reverse is also true.

If several tasks are running independently and two actors withdraw:

parallel execution may no longer be possible.

The scheduler may:

- serialize remaining work
- find replacement actors
- delay tasks
- reduce active branches

The prior plan must remain in history.

---

# 39. Dynamic Role Expansion

Projects may grow.

Example:

Initially:
20 participants expected

Later:
150 participants expected

The Actor Planning Agent may determine:

> One coordinator is no longer sufficient.

New roles may be created:

- additional coordinator
- subgroup leads
- check-in lead
- communication lead

Actor topology must be dynamic.

---

# 40. Dynamic Role Reduction

Projects may shrink.

Example:

Large event reduced from 100 attendees to 20.

Previously needed:

3 coordinators

Now:

1 coordinator

The system may propose reducing unnecessary roles.

Existing commitments should not be silently deleted.

Human confirmation may be required.

---

# 41. Themed Actor Names

Project creators may choose thematic actor names.

Possible built-in themes:

- Classic
- Heroes
- Change Makers
- Expedition
- Builders
- Custom

Example:

Canonical:
project_owner

Hero display:
Captain

Change Maker display:
Initiator

Expedition display:
Expedition Lead

Canonical:
coordinator

Hero:
Strategist

Change Maker:
Mobilizer

Expedition:
Navigator

Canonical:
executor

Hero:
Hero

Change Maker:
Change Maker

Expedition:
Explorer

The backend must always operate on canonical roles.

---

# 42. Custom Story Themes

A creator may describe a desired theme naturally.

Example:

> Make the project feel like a space mission.

AI may generate:

Project Owner:
Commander

Coordinator:
Mission Control

Task Owner:
Mission Lead

Executor:
Crew

Reviewer:
Flight Checker

The creator should review the mapping before it becomes active.

The system must prevent ambiguous custom names from changing actual permissions.

---

# 43. Public Role Presentation

Public project pages may show roles using themed display names.

Example:

Open Missions:

- 1 Mission Lead needed
- 3 Heroes needed
- 1 Guardian needed

The UI should provide enough context that users understand what each role actually means.

Example:

Guardian
Reviewer

This prevents themed language from becoming confusing.

---

# 44. Actor Discovery

The platform may eventually help people discover responsibilities based on:

- location
- interests
- prior contribution types
- availability
- project communities
- organization membership
- skills voluntarily provided

Discovery should recommend opportunities.

It should not assign people automatically.

---

# 45. Organization Responsibilities

Organizations may carry responsibility directly.

Example:

Animal Welfare Group A
accepts:
Field Coordination

The organization may then designate representatives or participants internally.

The system should preserve:

organization responsibility
+
human representatives

as separate relationships.

---

# 46. Group Responsibilities

A temporary or permanent group may carry responsibility.

Example:

Local Cycling Community
accepts:
Volunteer Mobilization

Individual members may then perform related actions.

Group accountability and individual execution should remain distinguishable.

---

# 47. Sponsor Responsibilities

A sponsor may have responsibilities such as:

- confirmed sponsor contact
- sponsor communication
- committed support
- sponsor event participation

Do not model financial amount itself as actor responsibility.

Example:

Wrong:

Actor role:
₹50,000

Correct:

Actor:
Company X

Role:
Sponsor

Commitment:
financial support amount recorded separately

---

# 48. Responsibility Completion

A responsibility may be considered fulfilled when:

- related task completes
- event completes
- required coordination concludes
- review is completed
- project closes
- explicit fulfillment condition is met

Completion rules may vary by scope.

---

# 49. Responsibility vs Participation

Participation is broader than responsibility.

A person may attend an event without carrying a formal responsibility.

Example:

100 people attend cleanup.

Formal actors may include:

- 1 Project Owner
- 2 Coordinators
- 5 Task Owners
- 20 registered Executors

Other attendees may simply be participants.

Do not force every participant into a responsibility role.

---

# 50. Responsibility History

Responsibility history should preserve:

- creation
- open state
- invitations
- requests
- acceptance
- activation
- pauses
- transfers
- withdrawal
- reassignment
- fulfillment

This becomes part of Project Memory.

---

# 51. Actor History

Project history may preserve:

- actors involved
- roles carried
- duration
- tasks/events supported
- completed responsibilities
- withdrawals
- handoffs

Cross-project reuse must respect privacy.

---

# 52. Agent Responsibilities Around Actors

Several specialized agents may eventually exist around this model.

Possible reasoning boundaries:

## Actor Requirement Agent

Determines what roles a project requires.

## Actor Capacity Agent

Determines how many actors of each role are needed.

## Actor Fit Agent

Suggests suitable participants or organizations.

## Responsibility Agent

Maintains responsibility lifecycle and vacancies.

## Actor Availability Agent

Understands availability changes.

## Actor Replanning Agent

Recalculates execution when actor topology changes.

These boundaries are not yet final.

Do not implement agents solely from this list until the full agent architecture document exists.

---

# 53. Deterministic Responsibilities

Not everything should be agent reasoning.

Deterministic application logic should handle:

- responsibility state transitions
- cardinality counts
- vacancy calculation
- permission checks
- accepted actor records
- canonical role IDs
- organization authorization
- history persistence
- availability state storage

Agents may reason about:

- which roles are needed
- how many may be useful
- whether project growth requires new roles
- whether work can be parallelized
- which actors may be suitable

---

# 54. Actor Model Invariants

## Invariant 1

Actor Role != Actor

## Invariant 2

Actor != Resource

## Invariant 3

Task != Responsibility

## Invariant 4

Participant != Responsibility

## Invariant 5

Organization != Organization Representative

## Invariant 6

Themed role name != canonical role

## Invariant 7

AI suggestion != accepted responsibility

## Invariant 8

Actor withdrawal must not delete history.

## Invariant 9

Project scale determines actor topology; every project must not receive the same actor set.

## Invariant 10

Additional actors may change execution parallelism and therefore the timeline.

---

# 55. Core Actor Model

The fundamental relationship is:

Project
→ requires
Actor Roles

Actor Roles
→ create
Open Responsibilities

Participants / Groups / Organizations
→ accept
Responsibilities

Responsibilities
→ enable
Execution

Actor availability
+
Responsibility acceptance
+
Task readiness
→ affect
Dynamic Timeline

---

# 56. Final Principle

Hatcommways does not merely ask:

> Who wants to join?

It asks:

> What kinds of responsibility does this project actually require, how many actors are needed, and who chooses to carry each responsibility?

That actor structure must adapt to:

- small projects
- large projects
- niche projects
- changing project scope
- new participants
- participant withdrawal
- increasing or decreasing execution capacity

The Actor Model is therefore a dynamic execution structure, not a static list of user roles.