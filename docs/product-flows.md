# Hatcommways — Product Flows

> Design/planning reference, not a deployed feature inventory. For current behavior and boundaries, see the [implementation documentation index](README.md). Broader capabilities below remain proposals unless confirmed there.

## 1. Purpose

This document defines the primary end-to-end user and system flows in Hatcommways.

The goal is to convert the product model into actual behavior.

The flows below define:

- what the user experiences
- what the system does underneath
- which agents reason
- which deterministic services update truth
- where human approval is required
- where parallel execution can happen
- what events are emitted

These flows are authoritative for product behavior.

Core principle:

> Hatcommways should make execution feel simple for humans while maintaining a rigorous execution graph underneath.

---

# 2. Flow Design Principles

All product flows should follow these principles.

## 2.1 Natural input first

Users should not begin by filling complex project-management forms.

The creator starts by describing:

> What do you want to make happen?

The system gradually turns that into structured execution state.

---

## 2.2 Planning is AI-assisted, not AI-imposed

Agents may generate:

- tasks
- dependencies
- actor roles
- timeline
- event suggestions
- execution structure

The creator sees and reviews important parts before publication.

---

## 2.3 Humans choose commitments

Agents may identify:

> We need an Event Coordinator.

Agents may not decide:

> Riya is now the Event Coordinator.

Responsibility requires human or authorized organization acceptance.

---

## 2.4 Execution is event-driven

Once the project becomes active, execution evolves from events.

Examples:

- participant joins
- responsibility accepted
- task completed
- actor unavailable
- support changed
- event rescheduled
- blocker resolved

The system reacts continuously.

---

## 2.5 Independent work runs independently

One blocked branch must not stop unrelated work.

Agents and tasks may run concurrently when dependencies allow it.

---

# 3. Primary Product Lifecycle

The main Hatcommways lifecycle is:

Idea
→ Project Creation
→ AI Planning
→ Creator Review
→ Publish / Activate
→ Responsibility Recruitment
→ Execution
→ Dynamic Replanning
→ Events
→ Outcome
→ Memory / Blueprint

This is not always strictly linear.

Once execution begins, many branches operate simultaneously.

---

# 4. Flow 1 — Start a New Project

## User Goal

A person wants to make something happen in their community.

Example:

> We want to build shelters for street dogs before the monsoon.

## User Experience

The first screen should be simple.

Primary input:

> What do you want to make happen?

User enters the goal naturally.

The system may then ask only lightweight planning questions.

Examples:

- Where should this happen?
- When do you want this completed?
- How do you expect it to be funded?
- Is there anything important you already know or have?

Avoid long questionnaires.

---

# 5. Initial Project Input

Minimum useful creation context:

## Goal

Natural-language description.

## Location

Broad project location.

## Time

Examples:

- this weekend
- within 3 weeks
- before monsoon
- October 10–12
- no strict deadline

## Funding Mode

- no money needed
- self-funded
- group-funded
- community-funded
- sponsor-supported
- mixed

## Known Context

Optional.

Examples:

- we already have 5 volunteers
- one NGO is helping
- we have a venue
- materials are already available

---

# 6. System Behavior — Project Creation

On submission:

1. Create Project record.
2. Persist original goal.
3. Persist creator-provided context.
4. Create initial project version.
5. Emit:

project.created

6. Activate relevant reasoning agents.

Potential initial concurrent agents:

- Goal Understanding Agent
- Project Scope Agent

The creator should immediately see that Hatcommways is beginning to structure the project.

---

# 7. Flow 2 — Goal Understanding

## Goal Understanding Agent

Transforms natural language into structured goal.

Example input:

> Build shelters for street dogs before monsoon.

Possible structured interpretation:

Goal:

Build and install weather-protective shelters.

Location:

Jaipur

Timeframe:

3 weeks

Funding mode:

community-funded

Target scale:

unknown

Known actors:

creator + 5 volunteers

The agent should identify only ambiguities that materially affect planning.

---

# 8. Minimal Clarification Flow

If important context is missing:

Agent asks only necessary questions.

Example:

> About how many shelters are you hoping to build?

This may matter significantly for:

- task scale
- actor count
- timeline
- support needs

But Hatcommways should not ask irrelevant domain questions merely because AI can.

Core rule:

> Ask only what materially affects execution planning.

---

# 9. Clarification Experience

The creator should remain on the same conversational creation surface.

Avoid:

Page 1
→ Page 2
→ Page 3
→ Page 4

Instead:

User goal
+
short AI clarification
+
project preview forming alongside

The execution model should visually grow as information becomes sufficient.

---

# 10. Flow 3 — AI Builds Initial Project Plan

Once sufficient planning context exists:

Multiple planning agents may operate.

Potentially:

- Task Decomposition Agent
- Dependency Reasoning Agent
- Project Scope Agent
- Actor Requirement Agent
- Actor Capacity Agent
- Timeline Planning Agent
- Parallelization Agent

These do not all need to run sequentially.

Some outputs depend on others.

Some can run concurrently.

---

# 11. Initial Planning Dependencies

Example orchestration:

Goal Understanding
+
Project Scope

↓

Task Decomposition

↓

Once initial tasks exist:

Dependency Reasoning
+
Actor Requirement

may begin.

Once task/dependency information is available:

Timeline Planning
+
Parallelization

may begin.

Once actor roles exist:

Actor Capacity
+
Role Specialization

may begin.

This is a dependency graph, not a fixed numbered agent chain.

---

# 12. Planning UI

The creator should see the project visually taking shape.

Potential sections:

## Goal

What are we trying to achieve?

## Tasks

What needs to happen?

## Timeline

When can it happen?

## People Needed

What actor roles are required?

## Events

What coordinated activities may be needed?

## Support

How will required support be handled?

The experience should feel like:

> The project is forming.

Not:

> AI returned a giant report.

---

# 13. Flow 4 — Creator Reviews the Plan

Before publication, creator sees an AI-generated plan.

Example:

Goal:
Build 20 shelters within 3 weeks.

Tasks:

1. Confirm suitable locations
2. Finalize shelter design
3. Organize required materials/work
4. Build shelters
5. Arrange transport
6. Install shelters
7. Review outcome

Actor Roles:

- Project Owner
- Coordinator
- Build Lead
- Executors
- Transport Lead
- Installation Lead
- Reviewer

Timeline:

Week 1:
Locations + design

Week 2:
Construction + logistics

Week 3:
Installation + review

This is a reviewable proposal.

---

# 14. Creator Review Actions

Creator may:

- approve plan
- edit project goal
- request plan change
- remove unnecessary tasks
- add known context
- change target time
- change funding mode
- change project visibility
- choose actor theme

If creator changes something material:

relevant planning agents rerun.

Do not rebuild unrelated parts unnecessarily.

---

# 15. Plan Approval

Creator selects:

> Approve Plan

System:

- validates current project version
- persists authoritative plan
- creates plan version
- emits:

project.plan_approved

The project can now move toward publication or private execution.

---

# 16. Flow 5 — Actor Theme Selection

Creator may optionally choose a theme.

Examples:

- Classic
- Heroes
- Change Makers
- Expedition
- Builders
- Custom Story

Example:

Canonical:

Project Owner

Hero Theme:

Captain

Canonical:

Executor

Hero Theme:

Hero

The creator previews the mapping.

System stores:

canonical role
+
display name

Permissions continue using canonical role.

---

# 17. Flow 6 — Project Visibility Setup

Before publication, creator chooses visibility.

Examples:

- Public
- Community Only
- Controlled
- Invite Only
- Private

The UI should explain consequences simply.

Example:

Public

> People can discover this project and see approved public information.

Controlled

> People can discover the project, but joining requires approval.

---

# 18. Visibility Setup Includes Maps

Creator may configure:

Action Map:
Public

Support Map:
Community members

Organization Map:
Public

Age Analytics:
Off

Exact location:
Members only

Defaults should be privacy conservative.

---

# 19. Flow 7 — Publish Project

Creator publishes.

System validates:

- plan approved
- visibility configured
- public location precision
- map configuration
- public organization attribution
- required project state

Then:

project.published

is emitted.

Project becomes discoverable according to policy.

---

# 20. Public Project Page

Public project view may show:

- project goal
- project story
- approved location
- timeline summary
- open responsibilities
- actor role structure
- Action Map
- approved Support Map
- approved Organization Map
- upcoming public events
- current outcome/progress
- approved organization/sponsor recognition

Visitors should immediately understand:

> What is happening?
> Who is needed?
> How can I help?

---

# 21. Flow 8 — Discover Projects

Users may discover projects through:

- geographic map
- local list
- communities
- search
- categories
- shared project link

Discovery map answers:

> What are people trying to make happen around me?

Pins may show:

- project
- broad location
- category
- open roles
- timing

---

# 22. Flow 9 — Visitor Opens Project

A visitor opens a public project.

They see:

Goal

Timeline

Action Map

Open Roles

Upcoming Events

Approved support information

They should not need to understand internal project-management terminology.

The UI should focus on:

> How can you participate?

---

# 23. Flow 10 — User Chooses a Responsibility

Instead of a generic:

Join Project

the user sees open actor responsibilities.

Example:

Open Roles:

Mission Lead
1 needed

Heroes
4 needed

Guardian
1 needed

Each role explains canonical meaning.

Example:

Mission Lead

Canonical:
Task Owner

Expected commitment:
3–4 hours/week

Related work:
Construction branch

---

# 24. Responsibility Details

Before requesting/accepting:

User may see:

- role purpose
- project scope
- relevant tasks
- expected time
- expected dates
- location
- required skills if any
- number of people needed
- whether project approval is required

This makes commitment meaningful.

---

# 25. Self-Claim Flow

User chooses:

> I can help with this.

Depending on policy:

Option A:

responsibility.requested

Project owner approves.

Then:

responsibility.accepted

Option B:

Open self-join role.

User confirms commitment.

Then:

responsibility.accepted

In both cases the human explicitly chooses.

---

# 26. Responsibility Acceptance Effects

When responsibility.accepted occurs:

Deterministic services update:

- filled role count
- responsibility state
- actor readiness
- affected task readiness

Several processes may activate concurrently:

- Responsibility Intelligence Agent
- Parallelization Agent
- Acceleration Agent
- Participation Intelligence Agent
- Project Memory Agent

---

# 27. Flow 11 — Actor Joining Changes Timeline

Example:

Task A and Task B are independent.

Initially one person owns both.

Timeline:

A
→ B

New actor accepts responsibility for B.

Hatcommways detects:

- dependencies allow parallel work
- independent actor capacity now exists

Parallelization Agent proposes:

A + B

Timeline recalculates.

Expected completion may move earlier.

The user may see:

> Project timeline improved by 2 days because another execution branch can now run in parallel.

This is a core Hatcommways experience.

---

# 28. Flow 12 — User Joins Without Formal Responsibility

Some project participation does not require formal accountability.

Example:

Community cleanup event.

User wants to attend as participant.

They may:

- RSVP
- join event
- participate

without becoming:

Task Owner
Coordinator
Reviewer

Participation and responsibility remain separate.

---

# 29. Flow 13 — Creator Invites Someone

Project owner may invite a known person.

Example:

> Invite Riya as Event Coordinator.

System sends invitation.

State:

responsibility.offered

Riya chooses:

Accept
or
Decline

Only after acceptance:

responsibility.accepted

---

# 30. Flow 14 — AI Suggests a Participant

Actor Fit Agent may recommend:

> Arjun may be a good fit for Event Coordinator because he has volunteered as an event coordinator previously and has shared availability this weekend.

This is a suggestion.

Possible creator action:

> Invite Arjun

The AI does not automatically assign him.

---

# 31. Flow 15 — Temporary Group Formation

A project may need a dedicated working group.

Example:

Shelter Build Team.

The Community and Group Structure Agent may suggest:

> This project has 18 active participants across several tasks. Creating a temporary project group may simplify coordination.

Creator approves.

group.created

Participants may join.

The group remains attached to the project.

---

# 32. Flow 16 — Existing Community Starts a Project

Permanent Community opens:

> Create Project

Example:

Green Park Residents Community.

Project inherits appropriate community context.

Possible reuse:

- community location
- creator authorization
- known membership
- community visibility preference

Do not automatically reuse private historical information unnecessarily.

---

# 33. Flow 17 — Organization Joins Project

An NGO, school, community organization, or company may discover or be contacted about a project.

Organization Representative selects:

> Participate in Project

Possible participation types:

- provide people
- host event
- provide expertise
- accept responsibility
- sponsor/support
- provide equipment
- review work

System records organization relationship.

No organization commitment exists until an authorized representative confirms it.

---

# 34. Organization Offer Flow

Example:

Organization says:

> We can provide 4 volunteers and one field coordinator.

System interprets offer.

Organization Participation Agent may map:

Organization:
Green Paws

Provides:

- 4 Executors
- 1 Coordinator

Human representative reviews.

Once accepted:

organization role / responsibility records are created.

---

# 35. Flow 18 — Company / Sponsor Contact

A project creator may decide to contact a company.

Hatcommways does not search for sponsors automatically.

Creator chooses company/contact.

Hatcommways may help:

- draft email
- send authorized email
- propose meeting
- schedule follow-up
- record response
- attach accepted support

---

# 36. Sponsor Contact Flow

Creator:

> Contact Company X about supporting the installation event.

AI may draft:

- concise project summary
- support request
- meeting request

Creator approves sending where required.

Company responds.

Hatcommways records the conversation/commitment state.

---

# 37. Flow 19 — Sponsor Supports Project

Company chooses to support.

Support may include:

- money
- venue
- people
- equipment
- expertise

Example:

Company X:

₹50,000 support
+
2 employees for event

These become separate structures.

Financial contribution:
Support record

Employees:
Actor participation

Do not collapse both into sponsorship.

---

# 38. Flow 20 — Manual Funding Update

Project admin receives an external financial contribution.

The actual transaction occurred outside Hatcommways.

Admin enters:

Amount:
₹5,000

Source:
Community contribution

State:
reported

Authorized project admin confirms.

Then:

support.contribution_confirmed_by_project

System clearly states:

> Confirmed by project, not independently verified by Hatcommways.

---

# 39. Flow 21 — Payment Instructions

If project needs financial contribution:

Authorized project admin may configure payment instructions.

Example:

UPI:
projecthelp@upi

Visibility:

Approved project members

This data remains restricted.

A public Money Map never exposes this value.

---

# 40. Flow 22 — Action Map Update

As responsibilities are accepted and execution begins:

Action Map updates.

Example:

North Jaipur:
12 active participants

Central Jaipur:
5 active participants

South Jaipur:
2 participants

The map may also show role distribution.

It reflects real execution participation.

---

# 41. Flow 23 — Money / Support Map Update

Financial support state changes.

Privacy pipeline:

raw contribution
→ authorized confirmation
→ privacy aggregation
→ threshold check
→ map projection

Public map may show:

North Jaipur:
strong support

South Jaipur:
moderate support

It should not show:

Ravi — ₹1,250 — exact address

---

# 42. Flow 24 — Event Creation

Project needs a time-bound coordinated activity.

Example:

Installation Day.

Event Planning Agent may propose:

Event:
Shelter Installation Day

Prerequisites:

- shelters built
- locations confirmed
- transport ready

Actors:

- Event Coordinator
- Installation Leads
- Executors

Creator reviews.

Event created.

---

# 43. Flow 25 — Schedule Event

Scheduling Agent examines:

- task readiness
- relevant actor availability
- participant availability
- project timeline
- location availability

It proposes:

Saturday:
9 AM–2 PM

Sunday:
8 AM–1 PM

Relevant humans choose.

Then:

scheduled_event.scheduled

---

# 44. Flow 26 — Event Is Scheduled but Not Ready

Example:

Installation event scheduled for Saturday.

But transport task remains incomplete.

State:

scheduled = true

ready = false

Hatcommways should surface:

> Installation Day is scheduled, but transport is still blocking readiness.

This distinction is important.

---

# 45. Flow 27 — Event Becomes Ready

Transport completes.

All event prerequisites are satisfied.

System emits:

scheduled_event.ready

Participants may receive:

> Installation Day is ready to proceed.

---

# 46. Flow 28 — Task Execution

Task owner opens task.

Sees:

- task objective
- responsible people
- dependencies
- timeline
- relevant event
- progress
- blockers

Task owner selects:

Start

task.started

Execution state updates.

---

# 47. Flow 29 — Progress Update

Task owner may report:

> 12 of 20 shelters completed.

System records progress.

Progress may affect:

- task estimate
- timeline
- downstream event readiness

Avoid requiring constant micro-updates.

---

# 48. Flow 30 — Task Completes

Task owner completes work.

If validation is not required:

task.completed

If review is required:

task submitted for review

Reviewer checks.

Then:

task.completed

Downstream dependencies update automatically.

---

# 49. Flow 31 — Multiple Tasks Unlock

Task A completes.

This unlocks:

Task B
Task C
Task D

System emits relevant readiness changes.

If actors exist:

B, C, D may all become execution-ready.

Hatcommways should not artificially start them one at a time.

---

# 50. Flow 32 — Actor Becomes Unavailable

Actor selects:

> I won't be available this week.

actor.unavailable

System determines:

- active responsibilities
- affected tasks
- affected events
- timeline impact

Blocker Detection Agent may activate.

---

# 51. Flow 33 — Responsibility Withdrawal

Actor chooses:

> Leave this responsibility.

The UI should explain impact if known.

Example:

> Leaving this role may pause the transport branch until another owner joins.

User confirms.

responsibility.withdrawn

The responsibility becomes vacant.

History remains.

---

# 52. Flow 34 — Local Blocker

Example:

Transport lead withdraws.

Affected:

Transport task
Installation event

Unaffected:

Construction
Public communication

Hatcommways continues unaffected branches.

Do not show:

Project stopped

unless it truly is project-wide.

---

# 53. Flow 35 — Blocker Detection

Blocker Detection Agent identifies:

Blocker:

Transport responsibility vacant

Impact:

Installation branch

Severity:

High

System creates:

blocker.created

The project owner sees:

> Installation is at risk because transport ownership is vacant.

---

# 54. Flow 36 — Replanning

Replanning Agent reasons only about affected region.

Potential proposal:

1. Keep construction active.
2. Open transport responsibility.
3. Move installation event by one day if vacancy remains after deadline.
4. Do not change unrelated project tasks.

This is better than rebuilding the entire plan.

---

# 55. Flow 37 — Replacement Actor Joins

New actor accepts Transport Lead.

responsibility.accepted

System:

- resolves vacancy
- recalculates readiness
- reevaluates blocker

blocker.resolved

Timeline may return to original date or improve.

---

# 56. Flow 38 — Acceleration

No blocker exists.

But execution capacity improves.

Example:

Four additional executors join.

Acceleration Agent detects:

> Construction can be divided into two teams.

Possible effect:

Expected task duration:
4 days → 2.5 days

Timeline compresses.

The system may automatically apply safe deterministic changes or request review for major changes depending on policy.

---

# 57. Flow 39 — Project Scope Expands

Creator changes:

20 shelters
→ 35 shelters

The UI warns:

> This may affect tasks, people, timeline, and support requirements.

Creator confirms.

project.scope_changed

Relevant agents rerun:

- Task Decomposition
- Dependency Reasoning
- Actor Requirement
- Actor Capacity
- Replanning
- Timeline

Previous plan remains in history.

---

# 58. Flow 40 — Event Rescheduled

Event organizer changes date.

System checks authority.

scheduled_event.rescheduled

Effects may include:

- participant availability recheck
- event readiness update
- task timing update
- notifications
- timeline recalculation

Project Memory records meaningful schedule revision.

---

# 59. Flow 41 — Support Becomes Insufficient

Example:

Material costs increase.

Project admin updates funding state:

insufficient

Only tasks depending on money should be affected.

Example:

Material purchase:
blocked

Volunteer recruitment:
continues

Location confirmation:
continues

Support State Reasoning Agent identifies affected work.

---

# 60. Flow 42 — Support Becomes Sufficient

New contribution is confirmed.

Funding state:

sufficient

Affected task becomes eligible for readiness recalculation.

Unrelated tasks remain unchanged.

Timeline recalculates if necessary.

---

# 61. Flow 43 — Project Decision Inbox

Hatcommways should have a compact decision surface.

Possible items:

- Approve project plan
- Riya wants to take Event Coordinator responsibility
- Company X offered venue support
- AI suggests moving installation event to Sunday
- Enable Support Map publicly?
- Revised plan needs approval

The product should surface real decisions rather than every background process.

---

# 62. Decision Item Structure

Each decision should explain:

## What happened?

Example:

Transport lead withdrew.

## What is affected?

Installation branch.

## What Hatcommways recommends

Invite replacement transport lead.

## What happens if I do nothing?

Installation may move by approximately one day.

## Action

Approve
Decline
Edit

This is much better than presenting raw agent output.

---

# 63. Flow 44 — Notifications

Notifications should be meaningful.

Examples:

Good:

> Your responsibility is ready to start.

> Saturday event moved to Sunday.

> Construction is complete; transport can begin.

> Your team needs one more executor before installation is ready.

Avoid:

> Agent 8 completed reasoning.

Users should see project meaning, not orchestration internals.

---

# 64. Flow 45 — Project Pause

Project owner chooses:

Pause Project

System explains consequences.

On confirmation:

project.paused

The system preserves:

- tasks
- responsibilities
- actors
- events
- history

Execution expectations pause.

---

# 65. Flow 46 — Project Resume

Creator resumes.

System revalidates:

- actor availability
- event dates
- support state
- task assumptions
- current timeline

The old schedule should not simply restart blindly.

Then:

project.resumed

and timeline may be recalculated.

---

# 66. Flow 47 — Project Completion Readiness

Hatcommways evaluates:

- required tasks
- required events
- required reviews
- unresolved critical blockers
- required outcome state

If completion conditions are satisfied:

project may enter:

completing

The creator reviews final outcome.

---

# 67. Flow 48 — Partial Outcome

Example:

Goal:
20 shelters

Completed:
16

Creator decides project should close.

Outcome records:

Target:
20

Achieved:
16

Status:
partial outcome

Remaining:
4

Reason:
location approvals unavailable

Hatcommways must preserve reality rather than forcing "success" or "failure."

---

# 68. Flow 49 — Final Outcome

At completion:

Outcome and Blueprint Agent analyzes:

- intended goal
- actual result
- tasks
- events
- actors
- organizations
- timeline
- blockers
- revisions
- support state

It produces a structured outcome proposal.

Creator/admin verifies appropriate public summary.

---

# 69. Completed Project Page

The completed project may show:

- what the community intended
- what was achieved
- timeline
- people/groups involved
- organizations involved
- approved support summary
- project maps
- photos/evidence where appropriate
- appreciation
- lessons/public story

Core message:

> This is what people made happen together.

---

# 70. Flow 50 — Appreciation

Hatcommways may generate appreciation drafts.

Examples:

For participants:

> 24 people helped execute this project across construction, logistics, and installation.

For organization:

> Green Paws Welfare Society coordinated field execution and supported installation.

For sponsor:

> Company X supported the installation phase.

Project owner reviews when required.

Then:

appreciation.sent

---

# 71. Flow 51 — Sponsor Private Impact Update

After project completion:

Sponsor's private dashboard may update.

Company X sees:

Project:
Shelter Build Jaipur

Support:
₹50,000

Other participation:
2 employees

Outcome:
16 shelters installed

Public visibility remains governed separately.

---

# 72. Flow 52 — Project Memory Creation

During execution, memory has already recorded meaningful changes.

At completion:

Project Memory Agent compacts:

- original plan
- revisions
- important responsibility changes
- blockers
- event changes
- support changes
- outcome

Raw events remain intact.

---

# 73. Flow 53 — Reusable Blueprint

Outcome and Blueprint Agent may generate a privacy-safe blueprint.

Example:

Community Shelter Installation Blueprint

Contains:

- typical task sequence
- actor structure
- parallelizable branches
- likely timing
- common blockers
- event pattern
- lessons

It excludes:

- private names
- payment instructions
- private contribution records
- exact sensitive locations

---

# 74. Flow 54 — Start Similar Project

Future creator enters a similar goal.

Agents may retrieve relevant execution blueprint.

Instead of blindly copying it:

AI compares:

- current scale
- location
- actor availability
- timeline
- project conditions

Then adapts the blueprint.

Historical pattern is input, not current truth.

---

# 75. Flow 55 — Community Reuses Experience

Permanent community starts another project.

Hatcommways may know:

- common project size
- roles community often fills
- execution patterns
- prior event structure

Where permissions allow, this can reduce repeated planning work.

But previous members are never automatically committed.

---

# 76. Flow 56 — Temporary Group After Completion

When project completes:

Temporary group may remain archived.

Hatcommways may suggest:

> This group completed a project together. Would you like to continue it as a permanent community?

Humans decide.

If approved:

group.converted_to_community

This should never happen automatically.

---

# 77. Flow 57 — Returning Participant

A participant sees a new local project.

Hatcommways may recommend:

> Event Coordinator may fit your interests based on roles you previously chose to carry.

The user decides whether to engage.

Past participation does not create obligation.

---

# 78. Flow 58 — Public Discovery After Completion

Completed projects remain discoverable where creator policy permits.

Discovery can show:

- outcome
- community action
- project history
- public maps
- reusable story

Hatcommways should make completed action visible, not only currently trending projects.

---

# 79. Flow 59 — Mobile Experience

Mobile is optimized for action.

Primary mobile flows:

- create goal
- review plan
- discover projects
- view map
- accept responsibility
- see "What needs me now?"
- update task progress
- attend event
- respond to decisions
- receive meaningful notifications

Complex graph editing may be simplified.

---

# 80. Flow 60 — Desktop Experience

Desktop may provide richer project control.

Potential views:

- task graph
- dependency graph
- dynamic timeline
- actor graph
- map dashboard
- blocker panel
- decision inbox
- organization relationships
- project history

Desktop is useful for project organizers and larger projects.

---

# 81. Core Home Experience — Participant

Participant home should answer:

> What can I help with?

Possible sections:

- Nearby projects
- Responsibilities that fit me
- Upcoming events
- My active responsibilities
- Decisions waiting for me
- Communities I belong to
- Projects I helped complete

Do not optimize around follower counts.

---

# 82. Core Home Experience — Project Owner

Owner dashboard should answer:

> What needs attention?

Possible sections:

- current execution health
- open critical responsibilities
- blocked branches
- upcoming events
- support-related blockers
- decisions waiting
- timeline changes
- recently completed work

---

# 83. Core Home Experience — Organization

Organization dashboard may show:

- projects currently joined
- responsibilities carried
- representatives
- upcoming meetings/events
- support offers
- pending decisions
- private impact history

---

# 84. Core Home Experience — Sponsor

Sponsor/company view may show:

- project participation requests
- active supported projects
- meetings
- commitments
- private impact map
- completed outcomes
- appreciation received

This should not become a sponsor popularity leaderboard.

---

# 85. What Hatcommways Should Automate

Agents should absorb repetitive coordination such as:

- decomposing projects
- watching dependencies
- recalculating timeline
- identifying open role bottlenecks
- identifying new parallelization
- detecting blockers
- summarizing changes
- drafting messages
- proposing schedules
- maintaining project memory

Humans should mainly receive:

- choices
- commitments
- approvals
- exceptions
- meaningful changes

---

# 86. What Hatcommways Should Not Automate Silently

Do not silently:

- accept responsibilities
- commit organizations
- publish projects
- expose private data
- expose optional demographics
- send consequential commitments
- cancel projects
- change major goal scope
- claim financial verification
- promise sponsor support

---

# 87. Background Agent Experience

The user should not feel they are managing 24 agents.

They should feel:

> Hatcommways is keeping the project moving.

Agents remain mostly invisible.

The UI surfaces:

- plans
- decisions
- warnings
- opportunities
- outcomes

not:

- agent conversations
- chain-of-thought
- orchestration logs

---

# 88. Example Full Flow

User enters:

> We want to build 20 shelters for street dogs before monsoon in Jaipur. We have five volunteers and plan to collect money within our community.

Hatcommways structures:

Goal
Location
Time
Funding mode
Known actors

Planning agents create:

- task graph
- dependency graph
- actor requirements
- initial timeline

Creator approves.

Project publishes.

Action Map begins.

Open roles appear:

- Coordinator
- Build Lead
- Transport Lead
- Executors
- Reviewer

People join.

New responsibilities unlock parallel work.

Construction and location confirmation run together.

A welfare organization joins and provides field support.

Community contributions are entered manually.

Support Map shows aggregated contribution strength.

Installation event is created.

Scheduling Agent coordinates timing.

Transport Lead withdraws.

Hatcommways identifies only the affected branch.

Replanning Agent proposes replacement.

New Transport Lead joins.

Timeline recalculates.

Installation event proceeds.

16 of planned 20 shelters are installed.

Project closes with partial outcome.

Hatcommways records:

- target
- actual outcome
- actors
- organization participation
- support
- blocker
- revised timeline
- lessons

Community receives project story.

Sponsor/organization receives approved appreciation.

A privacy-safe blueprint is created for future similar projects.

That is Hatcommways.

---

# 89. Product Flow Invariants

## Invariant 1

The first interaction starts with a human goal, not a project-management form.

## Invariant 2

AI-generated planning remains reviewable.

## Invariant 3

Joining a project and accepting responsibility are different.

## Invariant 4

Humans explicitly accept responsibility.

## Invariant 5

Organization participation requires authorized representation.

## Invariant 6

Independent branches continue when unrelated branches are blocked.

## Invariant 7

New actors can change timeline parallelism.

## Invariant 8

Payment processing happens outside Hatcommways initially.

## Invariant 9

Public maps use governed/aggregated data.

## Invariant 10

Project history survives replanning.

## Invariant 11

Agents operate in the background; users see meaningful decisions.

## Invariant 12

Completion records actual outcome, including partial outcomes.

---

# 90. Final Product Experience

A Hatcommways user should experience the following transformation:

> I have an idea.

becomes:

> I understand what needs to happen.

then:

> I can see who we need.

then:

> People are choosing responsibilities.

then:

> Work is happening in parallel.

then:

> Hatcommways is handling changes and blockers.

then:

> We know what needs attention.

and finally:

> We made something real.

That is the core product journey behind:

> From “someone should” to “we did.”