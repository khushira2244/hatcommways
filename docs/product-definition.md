# Hatcommways — Product Definition

## 1. Product Summary

Hatcommways is an AI-powered community execution platform.

A person, group, community, organization, welfare group, school, or company can bring a real-world goal. Hatcommways converts that goal into a structured execution system made of:

- tasks
- dependencies
- dynamic timelines
- actor roles
- responsibilities
- events
- groups
- organizations
- support/funding states
- maps
- progress
- project memory

The purpose of Hatcommways is not mainly discussion, posting, fundraising, or generic project management.

Its purpose is:

> Turn community ideas into coordinated real-world execution.

Core punch line:

> From “someone should” to “we did.”

---

# 2. Core Philosophy

Hatcommways is built around several product principles.

## 2.1 Ideas are not posts

A project does not remain a social-media post.

An idea becomes:

Goal
→ Tasks
→ Dependencies
→ Timeline
→ Actor Roles
→ Responsibilities
→ Execution
→ Outcome

The project is a living execution network.

---

## 2.2 Tasks and responsibilities are different

This distinction is fundamental.

### Task

A task describes:

> What needs to happen?

Tasks define the work structure.

Tasks influence:

- dependencies
- ordering
- duration
- parallel execution
- timeline

Example:

- choose event location
- organize transport
- prepare materials
- conduct installation
- review final result

### Responsibility

Responsibility describes:

> Who is accountable for making something happen?

Actors carry responsibilities.

A task may involve:

- one responsible actor
- multiple responsible actors
- one lead plus executors
- specialist responsibility
- organization responsibility
- sponsor/company responsibility
- reviewer responsibility

Tasks must never be treated as equivalent to people.

---

## 2.3 Tasks define timeline; actors define responsibility

The task graph determines the possible execution timeline.

Actor availability determines whether the work can actually execute.

Example:

Task A and Task B may be independent.

If only one suitable actor exists, they may initially execute sequentially.

If another actor joins later, Hatcommways may move them into parallel execution.

Therefore:

> The timeline is dynamic.

It must be recalculated when:

- actors join
- actors leave
- responsibilities are accepted
- tasks complete
- dependencies resolve
- blockers appear
- events change
- execution capacity increases
- execution capacity decreases

---

## 2.4 Independent work should run in parallel

Hatcommways must not use a fixed linear workflow such as:

Agent 1
→ Agent 2
→ Agent 3
→ Agent 4

The system is dependency-driven.

If different tasks, actors, or agents have the inputs they require, they should be able to proceed independently and in parallel.

Core rule:

> Hatcommways is dependency-driven, not sequence-driven.

---

# 3. Who Uses Hatcommways

Hatcommways supports several types of participants.

## 3.1 Individual Users

Individuals can:

- propose ideas
- create projects
- join projects
- take responsibilities
- organize work
- participate in events
- support projects
- join temporary groups
- join permanent communities

---

## 3.2 Temporary Groups

Temporary groups are created around a particular project or event.

Example:

“Street Dog Shelter Project — Jaipur”

The group may disappear or become inactive after the project is complete.

Temporary groups may be location-based.

---

## 3.3 Permanent Communities

Permanent communities remain active across multiple projects.

Examples:

- neighborhood community
- animal welfare community
- school community
- resident association
- maker community
- environmental group
- local volunteer network

Projects may be attached to permanent communities.

---

## 3.4 Organizations

Organizations may include:

- NGOs
- welfare groups
- schools
- nonprofits
- local organizations
- resident bodies
- community organizations

Organizations can:

- create projects
- join projects
- provide actors
- provide expertise
- organize events
- carry responsibilities
- communicate with project owners
- participate in project execution

---

## 3.5 Companies / Sponsors

Companies have proper accounts.

They are not treated only as money sources.

A company may provide:

- sponsorship
- people
- employees
- expertise
- equipment
- spaces
- services
- event participation
- organizational support

Companies may discover public projects and choose to engage.

Users may also choose to contact companies.

Hatcommways may help coordinate:

- contact
- communication
- email
- meetings
- scheduling
- commitments
- follow-ups

Hatcommways does not automatically find sponsors on behalf of users.

---

# 4. Initial Project Creation

Hatcommways should not start with a large multi-step form.

The project creation experience should feel conversational and visual.

The user provides only the minimum useful information initially.

Core inputs:

1. Goal
2. Location
3. Expected timeframe or duration
4. Funding mode
5. Any important context already known

Funding modes may include:

- no money required
- self-funded
- group-funded
- community-funded
- sponsor-supported
- mixed

The UI should then show the project being built visually.

The user should feel:

> My idea is becoming an execution plan.

Not:

> I am filling in project-management paperwork.

---

# 5. Task Planning

After receiving the goal, Hatcommways generates the task structure.

The AI should reason about:

- what needs to happen
- what must happen first
- what can happen independently
- what can happen in parallel
- approximate timing
- what work is blocked
- what work can start immediately

Tasks create the foundation for the dynamic timeline.

Example:

Goal:

“Build shelters for street dogs before monsoon.”

Possible tasks:

- identify suitable locations
- decide shelter design
- prepare build plan
- organize required work
- construct shelters
- organize transport
- install shelters
- review final result

The exact task structure depends on the goal.

Hatcommways should not create domain-specific rigid templates when intelligent decomposition is possible.

---

# 6. Actor Planning

After tasks are understood, Hatcommways determines what actor roles are required.

Actor requirements depend on:

- project size
- project type
- duration
- complexity
- task structure
- location
- execution stage
- specialist requirements
- participating organizations

A small event may require:

- creator
- organizer
- participants

A larger project may require:

- project lead
- coordinators
- task owners
- executors
- specialists
- reviewers
- organization representatives
- company representatives
- sponsors
- event hosts
- communication leads

Actors are execution roles.

Resources such as money, equipment, venue, and material are not actors.

---

# 7. Actor Naming / Story System

Hatcommways may allow project creators to choose themed names for actor roles.

The system keeps canonical role semantics internally.

Example internal roles:

- project_owner
- organizer
- coordinator
- task_owner
- executor
- specialist
- reviewer

The UI may rename them according to a project theme.

Example — Hero Theme:

- Project Owner → Captain
- Coordinator → Strategist
- Task Owner → Mission Lead
- Executor → Hero
- Reviewer → Guardian

Example — Change Maker Theme:

- Project Owner → Initiator
- Coordinator → Mobilizer
- Task Owner → Action Lead
- Executor → Change Maker
- Reviewer → Observer

The creator may choose:

- Classic
- Heroes
- Change Makers
- Expedition
- Builders
- Custom Story

Important rule:

> Theme changes presentation, never permissions or responsibility semantics.

---

# 8. Joining a Project

Users should not only press:

“Join Project”

They should see the actual actor roles and responsibilities available.

Example:

- Organizer — filled
- Task Owner — 1 open
- Specialist — 1 open
- Executors — 4 of 8 joined
- Reviewer — open

A user chooses how they want to participate.

The system then updates execution capacity.

If a newly joined actor makes previously waiting work possible, the timeline may change automatically.

---

# 9. Dynamic Timeline

The timeline is never permanently fixed.

It reacts to project state.

Inputs affecting the timeline include:

- task dependencies
- actor availability
- responsibility acceptance
- actor withdrawal
- new actors joining
- completed tasks
- delayed tasks
- event timing
- blockers
- project revisions

Hatcommways should continuously reason:

- What can start now?
- What is waiting?
- What is blocked?
- What can run in parallel?
- Has additional execution capacity appeared?
- Can the completion time improve?
- Does a responsibility need to be reassigned?

---

# 10. Project and Event Relationship

Hatcommways supports both projects and events.

## Project

A project is a persistent goal.

Examples:

- restore a neighborhood playground
- build shelters for street dogs
- create a local accessibility map
- organize a recurring educational initiative

A project may last:

- days
- weeks
- months

## Event

An event is time-bound.

Examples:

- cleanup day
- installation day
- workshop
- meeting
- build session
- volunteer session
- testing event
- community gathering

Events can exist inside projects.

A project may contain multiple events.

The scheduling system should respect task dependencies before scheduling events.

---

# 11. Money and Funding

Hatcommways is not initially a payment processor.

Hatcommways does not directly collect or distribute project money.

The product supports financial coordination as part of execution.

Projects may be:

- no-money-needed
- self-funded
- community-funded
- group-funded
- sponsor-supported
- mixed

Payment instructions may be stored privately.

Examples:

- UPI/payment address
- external payment link
- payment contact
- instructions

These details must not be publicly exposed by default.

The project/group may manually update funding state.

Examples:

- target amount
- achieved amount
- remaining amount
- support status

Money matters because it can affect task readiness.

Hatcommways tracks money as execution state, not as the center of the product.

---

# 12. Action Map

Every suitable public project should support an Action Map.

The Action Map represents the human execution around the project.

It may show:

- where participants are coming from
- geographic concentration of action
- communities involved
- actor types participating
- open responsibility areas
- execution strength
- where participation is weak
- where participation is strong

The Action Map answers:

> Who is actually helping make this happen?

This is a foundational map.

---

# 13. Money / Support Map

When money is relevant, a project may show a Money / Support Map.

The public map must not expose:

- payment addresses
- private donor identities
- transaction references
- private financial details

Instead it shows aggregated patterns such as:

- geographic contribution strength
- community contribution strength
- company/sponsor contribution
- support by contributor type
- financial participation intensity

The map answers:

> How is the community supporting this project financially?

The purpose is not fundraising pressure.

It is to show how people are supporting execution.

---

# 14. Sponsor / Organization Map

Projects involving companies or organizations may expose an organization/support map.

It can show:

- organizations involved
- sponsors participating
- geographic support
- type of involvement

Full sponsor history should not automatically become public.

Recognition should primarily remain attached to the project where the contribution happened.

Core rule:

> Recognition follows the work.

---

# 15. Optional Analytics Maps

Project creators may optionally enable additional aggregated maps.

Examples:

- age-band distribution
- community-type distribution
- participant-type distribution
- local vs outside-area participation
- recurring vs first-time contributors

These are optional.

They should not automatically appear.

Normal project pages should usually expose only 2–3 meaningful map views.

Large projects may expose up to approximately 4.

Core hierarchy:

1. Action Map — foundational
2. Money / Support Map — when relevant
3. Sponsor / Organization Map — when relevant
4. Optional analytics — creator controlled

---

# 16. Sponsor Impact Experience

Companies/sponsors may have a private impact dashboard/map.

They may see:

- projects they supported
- where those projects happened
- contribution amount
- roles or work enabled
- project outcome
- participants involved
- people/community affected
- appreciation generated by the project

This aggregated sponsor history is private to the sponsor unless they explicitly publish something.

A public visitor should not automatically see a sponsor’s full support history.

---

# 17. Project Recognition and Appreciation

Completed projects may create:

- thank-you messages
- appreciation messages
- outcome summaries
- sponsor/organization acknowledgements
- participant recognition

Recognition belongs primarily to the project/event.

Hatcommways should avoid turning sponsorship or participation into generic profile popularity.

The system should reward meaningful contribution rather than follower count.

---

# 18. AI Role

Hatcommways agents are execution-intelligence agents.

They are not primarily domain-specific agents such as:

- dog agent
- environment agent
- school agent

Instead they reason about execution.

Likely reasoning areas include:

- goal understanding
- project decomposition
- task planning
- dependency reasoning
- timeline planning
- parallelization
- actor-role planning
- responsibility structure
- project scale
- scheduling
- event coordination
- blocker detection
- execution readiness
- replanning
- project progress
- completion reasoning
- outcome history
- memory

Expected architecture is approximately 22–24 specialized agents initially.

The exact number must be derived from real responsibility boundaries.

Do not create agents only to increase agent count.

An agent should exist only if it has meaningful separation in one or more of:

- reasoning
- state
- tools
- permissions
- trigger conditions
- failure boundaries

Otherwise use deterministic application logic.

---

# 19. Memory Philosophy

Hatcommways should not use one giant undifferentiated AI memory.

Potential memory categories include:

- project memory
- actor/contributor memory
- organization memory
- relationship memory
- execution-pattern memory
- failure/revision memory
- temporary agent working memory

Project memory should preserve:

- original goal
- task structure
- actor structure
- responsibility acceptance
- timeline changes
- project decisions
- blockers
- failed attempts
- revisions
- events
- outcomes

Completed projects should become reusable execution histories where privacy allows.

---

# 20. Product UI Philosophy

Hatcommways should initially be a mobile-first responsive web application / PWA.

The UI should not feel like a traditional enterprise project-management system.

The user speaks naturally.

The system creates structured execution state underneath.

Core principle:

> Natural human input in front. Structured execution intelligence underneath.

Mobile should prioritize:

- project creation
- discovery
- maps
- responsibilities
- joining
- action updates
- events
- decisions

Desktop may expose richer:

- task graphs
- timelines
- maps
- project control
- execution views
- memory/history

---

# 21. What Hatcommways Is Not

Hatcommways must not become:

- another social media feed
- generic task manager
- crowdfunding clone
- sponsor marketplace
- volunteer job board
- generic event platform
- payment processor
- follower/reputation competition platform

Those capabilities may exist around execution, but none of them are the product center.

The product center is:

> Community execution.

---

# 22. Core System Model

The core project structure is:

Goal
→ Tasks
→ Dependencies
→ Dynamic Timeline

alongside:

Project
→ Actor Roles
→ Responsibilities
→ Participants / Organizations

supported by:

- groups
- communities
- events
- financial support state
- organizations
- maps
- memory
- agent coordination

The execution engine continuously keeps these structures synchronized.

---

# 23. Product Definition

Hatcommways is an AI-powered community execution platform that turns a real-world goal into a dynamic task graph, timeline, and project-specific responsibility structure.

People, communities, organizations, and companies choose the roles they want to carry, while autonomous agents continuously coordinate dependencies, parallel execution, schedules, events, blockers, changing participation, and project history until the community reaches an outcome.

Core punch line:

> From “someone should” to “we did.”