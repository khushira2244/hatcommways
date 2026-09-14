# Hatcommways — Execution and Timeline Model

> Design/planning reference, not a deployed feature inventory. For current behavior and boundaries, see the [implementation documentation index](README.md). Broader capabilities below remain proposals unless confirmed there.

## 1. Purpose

This document defines how Hatcommways turns a planned project into a live execution system.

It explains:

- how tasks become executable
- how dependencies affect readiness
- how actor responsibility affects execution
- how timelines are calculated
- how parallel work is discovered
- how actor availability changes timing
- how delays and blockers affect the project
- how replanning works
- how events fit into execution
- how execution history is preserved

This document is authoritative for execution behavior.

Core principle:

> Tasks shape the timeline.
> Actors carry responsibility.
> Execution emerges from the interaction between both.

---

# 2. Execution Is Dynamic

Hatcommways must not treat a project plan as a fixed schedule.

A plan is only the best-known execution structure at a particular moment.

Execution reality may change because:

- new actors join
- actors withdraw
- responsibilities remain unfilled
- tasks finish early
- tasks finish late
- dependencies change
- events move
- project scope changes
- support-state changes, including optional externally arranged funding where relevant
- organizations join
- new information appears
- blockers appear
- parallel work becomes possible

Therefore:

> The Hatcommways timeline is continuously derived from current project reality.

---

# 3. Core Execution Structures

The execution system connects five primary structures:

## 3.1 Goal

Defines the real-world outcome.

## 3.2 Task Graph

Defines:

- what must happen
- which work depends on other work
- which work is independent

## 3.3 Actor / Responsibility Graph

Defines:

- what actor roles are required
- who has accepted responsibility
- where responsibility remains vacant

## 3.4 Dynamic Timeline

Defines:

- what can happen now
- what may happen next
- what is waiting
- what can run in parallel
- expected project duration

## 3.5 Event Stream

Records everything that changes execution state.

Examples:

- actor joined
- responsibility accepted
- task completed
- blocker created
- event rescheduled
- project scope changed

The event stream causes the execution model to be recalculated.

---

# 4. Task Graph

The Task Graph is the structural representation of project work.

Each task may contain:

- task id
- project id
- title
- description
- estimated duration
- dependency relationships
- required actor-role relationships
- current task state
- logical readiness
- execution readiness
- start time
- completion time
- scheduling information
- branch relationship
- parent/child relationship
- execution history

The graph may contain:

- sequential work
- parallel work
- branching paths
- merging paths
- optional work
- conditional work

Hatcommways must not assume a single linear task chain.

---

# 5. Dependency Model

A Dependency describes a condition that affects when a task may proceed.

Typical example:

Task B cannot begin until Task A completes.

Conceptually:

Task A
→ Task B

But projects may also contain:

Task A
→ Task C

Task B
→ Task C

meaning Task C waits for both A and B.

Or:

Task A
Task B
Task C

may all be independent.

Dependencies determine logical execution possibility.

They do not alone determine actual execution.

---

# 6. Logical Readiness

Logical Readiness answers:

> According to the task graph, is this task allowed to begin?

Example:

Task:
Install shelters

Dependencies:

- shelters built
- installation locations confirmed

If both dependencies are complete:

logical_ready = true

If either remains incomplete:

logical_ready = false

Logical readiness should usually be deterministic.

---

# 7. Responsibility and Capacity Readiness

## Responsibility Readiness

Responsibility Readiness answers:

> Do the required responsibilities exist, and have authorized actors accepted them?

Possible conditions:

- required responsibility exists
- required responsibility has been accepted
- required specialist responsibility is filled
- required organization responsibility is accepted

## Capacity Readiness

Capacity Readiness answers:

> Is sufficient available execution capacity present for the task to begin?

Possible conditions:

- responsible actors are currently available
- minimum actor counts are satisfied
- specialist capacity is sufficient
- organization capacity is sufficient
- actor contention does not consume the required capacity

Example:

Task:
Installation

Required:

- 1 Task Owner
- minimum 4 Executors

Current:

- Task Owner: filled
- Executors: 2

Therefore:

responsibility_ready = true

capacity_ready = false

Even if:

logical_ready = true

---

# 8. Execution Readiness

Execution Readiness answers:

> Can this task actually start now?

Conceptually:

logical readiness
+
responsibility readiness
+
capacity readiness
+
required project conditions
=
execution readiness

Possible project conditions may include:

- event readiness
- manual approval
- project state
- support state where applicable
- location/time availability
- organization confirmation

Example:

logical_ready = true

responsibility_ready = true

capacity_ready = true

required approval = true

approval_received = false

Therefore:

execution_ready = false

Execution readiness should be explicitly persisted.

---

# 9. Task Readiness States

A task may conceptually exist in states such as:

## Not Ready

Dependencies or required conditions are missing.

## Logically Ready

Dependencies are satisfied, but responsibility, capacity, or another execution condition is missing.

## Execution Ready

All required execution conditions are satisfied.

## Active

Execution has started.

## Blocked

Execution started or could start, but a blocker prevents progress.

## Completed

Required work has finished.

These distinctions should be visible to the orchestration system.

---

# 10. Timeline

The Timeline is derived from current execution state.

It is not manually authored as immutable truth.

The timeline may include:

- expected task start
- expected task completion
- active branch
- blocked branch
- parallel branch
- upcoming event
- expected project completion

Timeline calculations may use:

- dependency graph
- estimated duration
- responsibility readiness
- capacity readiness
- actor availability
- current active tasks
- event dates
- blockers
- current project time

---

# 11. Initial Timeline

When the project is first planned, Hatcommways produces an initial timeline.

This timeline is based on assumptions.

Example:

Task A:
2 days

Task B:
3 days
depends on A

Task C:
2 days
independent

Task D:
1 day
depends on B and C

If sufficient actors exist:

Day 1–2:
A + C

Day 3–5:
B

Day 6:
D

If only one execution actor exists for A, B, and C, initial reality may require:

Day 1–2:
A

Day 3–5:
B

Day 6–7:
C

Day 8:
D

Therefore:

> Task dependencies define possible parallelism.
> Actor capacity determines achievable parallelism.

---

# 12. Structural Parallelism

Structural Parallelism exists when tasks do not depend on each other.

Example:

A
B
C

have no mutual dependencies.

Therefore they are structurally parallelizable.

This does not mean they will all execute simultaneously.

Actual parallel execution depends on actors.

---

# 13. Execution Parallelism

Execution Parallelism exists when:

- tasks are structurally parallelizable
- sufficient independent responsible actors are available
- no project-wide constraint prevents execution

Example:

Three independent tasks exist.

One actor is initially available.

Execution:

A
→ B
→ C

Two new actors join later.

Now:

A
B
C

may run simultaneously.

Hatcommways should detect this and replan.

---

# 14. Actor-Driven Timeline Compression

New actors may reduce project duration.

Example:

Initial expected duration:
14 days

Two additional task owners join.

Three branches can now run simultaneously.

Replanned expected duration:
9 days

Hatcommways should be able to explain:

> Expected completion moved forward because two previously sequential branches now have independent responsible actors.

This is a core product capability.

---

# 15. Actor-Driven Timeline Expansion

Actors may also increase expected duration when they leave or become unavailable.

Example:

Three branches were active.

Two branch owners withdraw.

The system may need to:

- mark responsibilities vacant
- pause affected branches
- serialize remaining work
- seek replacement actors
- update expected completion

Timeline expansion should preserve the previous plan in history.

---

# 16. Responsibility Vacancy and Execution

A task should not disappear when an actor leaves.

Example:

Task exists:
Prepare event logistics

Responsible actor withdraws.

The correct state is:

Task remains.

Responsibility:
vacant

Task may become:

logical_ready = true

responsibility_ready = false

capacity_ready = false

execution_ready = false

The system then exposes the vacancy.

---

# 17. Capacity-Based Execution

Some tasks may require multiple actors.

Example:

Task:
Community installation

Actor requirement:

minimum executors = 4

ideal executors = 6

maximum useful executors = 8

If:

2 joined

execution may remain blocked.

If:

4 joined

execution becomes possible.

If:

6 joined

expected duration may improve.

If:

12 join

the task should not necessarily become faster.

The planner may determine that additional actors offer no useful capacity.

---

# 18. Actor Capacity Across Tasks

One actor may carry multiple responsibilities.

Example:

Actor A owns:

- Task 1
- Task 2
- Event coordination

Even if Task 1 and Task 2 are structurally independent, they may not execute simultaneously if Actor A is required for both.

Therefore timeline calculation must consider:

> actor contention

This is different from task dependency.

---

# 19. Actor Contention

Actor Contention occurs when the same required actor is needed by multiple otherwise parallel tasks.

Example:

Task A and Task B have no dependency.

Both require Specialist X.

Specialist X cannot perform both simultaneously.

Therefore:

A
→ B

or

B
→ A

may be necessary.

If another qualified specialist joins:

A
and
B

may run in parallel.

Actor contention should be represented separately from task dependency.

---

# 20. Timeline Recalculation Triggers

The timeline should be reconsidered when important execution events occur.

Examples:

- project plan approved
- task added
- task removed
- dependency added
- dependency removed
- responsibility accepted
- responsibility withdrawn
- actor availability changed
- actor capacity changed
- task started
- task completed
- task blocked
- blocker resolved
- event scheduled
- event postponed
- support state changed
- project scope changed
- organization joined
- project paused
- project resumed

Not every event must cause a full expensive replan.

The orchestrator may determine the affected execution region.

---

# 21. Incremental Replanning

Hatcommways should prefer incremental replanning where possible.

Example:

Task 12 changes.

Only downstream tasks 15, 16, and 19 depend on Task 12.

The system should not necessarily rebuild the entire project plan.

It can:

- identify affected graph region
- recalculate local readiness
- recalculate affected timeline branches
- preserve unaffected work

Core principle:

> A local problem should not freeze the whole project.

## Affected Execution Region

A project change must not automatically cause the entire project to be replanned.

Hatcommways first determines the affected execution region or subgraph. This region contains the tasks, dependencies, responsibilities, actor-capacity constraints, events, and timeline windows whose current execution assumptions may no longer hold.

Example:

A → B → C → D

E → F

G → H

If the actor responsible for B leaves, the likely affected region is:

B → C → D

The independent branches E → F and G → H remain stable unless another relationship makes the impact broader.

The affected-region calculation should consider:

- the changed object and its direct execution relationships
- upstream constraints that may limit available alternatives
- downstream tasks, events, and timeline windows that depend on the changed state
- responsibility readiness and actor availability
- actor capacity and contention across otherwise independent tasks
- project-wide conditions such as pause, cancellation, major scope change, or shared approval
- cross-branch resources or events that require the region to expand

## Readiness During Selective Replanning

Selective replanning must preserve the existing readiness distinctions:

- logical readiness
- responsibility readiness
- capacity readiness
- execution readiness

A task may remain logically ready while losing responsibility or capacity readiness. The affected region should include tasks whose readiness or achievable timing changes, without invalidating unrelated tasks.

Actor capacity is part of the calculation. If one actor becomes unavailable, Hatcommways should identify the tasks that depend on that actor or shared capacity. If new capacity joins, it should identify only the branches whose parallelism or duration may improve.

## Selective Timeline Recalculation

After the affected region is calculated, Hatcommways should:

1. preserve unaffected branches and their accepted execution state
2. selectively invalidate stale readiness or timing inside the affected region
3. update the relevant graph edges, responsibilities, capacity constraints, and event conditions
4. recalculate only the affected timeline windows and downstream completion impact
5. expand the region when validation discovers a wider dependency or project-wide consequence
6. persist the new revision with its source event, affected region, expansion reasons, and unchanged branches

Reasons to expand the affected region may include:

- a shared actor or specialist creates contention outside the initial branch
- a project-wide event, approval, location, or support condition changes
- a dependency edge connects the region to another branch
- the expected project completion or critical path changes
- a proposed local change violates a project-wide invariant

Selective invalidation must be explicit. A local change should invalidate only the assumptions and derived state that depend on it.

This approach reduces reasoning cost and latency, avoids unnecessary mutations, improves stability under concurrent events, and makes plan changes easier to explain and audit.

Core principle:

> Replan the affected execution region, not the entire project, unless the change has project-wide consequences.

---

# 22. Blockers

A Blocker represents a problem preventing expected execution.

Examples:

- responsible actor unavailable
- required responsibility vacant
- event cancelled
- location unavailable
- task delayed
- approval missing
- required project support unavailable or insufficient
- external dependency changed

A blocker should contain:

- blocker id
- affected task/event/project
- blocker type
- source
- severity
- detected time
- resolution state
- affected downstream work
- relevant actors

---

# 23. Blocker Impact Analysis

When a blocker appears, Hatcommways should determine:

- what directly stops
- what indirectly stops
- what remains unaffected
- what can continue
- what could be parallelized instead
- whether another actor can take responsibility
- whether timeline changes are required

Example:

Task B blocked.

Task C is independent.

Correct behavior:

Task B waits.

Task C continues.

Incorrect behavior:

Pause the whole project.

---

# 24. Critical Path Awareness

For larger projects, Hatcommways may identify critical execution branches.

A critical branch is one where delay may directly affect expected project completion.

The system may use this to:

- prioritize actor recruitment
- identify dangerous blockers
- prioritize replanning
- surface urgent decisions

Critical path analysis should be deterministic where possible.

Agent reasoning may interpret ambiguous planning alternatives.

---

# 25. Priority and Urgency

Priority and urgency are different.

Priority:

How important is the work?

Urgency:

How soon must action occur?

A task may be:

high priority
low urgency

or:

medium priority
high urgency

Timeline decisions may consider both.

---

# 26. Task Start

A task may begin when:

execution_ready = true

and an authorized actor or workflow starts execution.

Starting a task should create an execution event.

Example:

task.started

The system records:

- actual start time
- responsible actors
- timeline version
- active dependencies
- current plan revision

---

# 27. Task Completion

Completion should record:

- actual completion time
- responsible actors
- outcome/evidence where required
- deviations from estimate
- follow-on tasks becoming ready

Completion may immediately unlock multiple downstream branches.

Example:

Task A completes.

This may simultaneously make:

Task B ready
Task C ready
Task D partly ready

Relevant agents may activate in parallel.

---

# 28. Early Completion

If a task finishes earlier than estimated, Hatcommways may:

- move downstream work earlier
- activate newly ready responsibilities
- propose earlier events
- compress expected project completion

The system should not wait for the original planned date.

---

# 29. Late Completion

If a task is late, Hatcommways should evaluate:

- downstream impact
- whether downstream work can still begin partially
- whether parallel branches can continue
- whether actor capacity can be increased
- whether event timing changes
- whether expected completion changes

Late status should not automatically mean project failure.

---

# 30. Partial Execution

Some tasks may support partial progress.

Example:

Task:
Prepare 100 community kits

40 are complete.

The model may support:

progress = 40%

If downstream work can begin with partial completion, the task planner may define a partial dependency.

The first implementation does not need every complex partial dependency type, but the architecture should not assume all tasks are binary.

---

# 31. Events and Timeline

Events participate in project execution.

An event may depend on:

- tasks
- responsibility readiness
- capacity readiness
- participant count
- schedule availability
- organization confirmation

Example:

Installation Event

requires:

- construction complete
- transport ready
- event organizer accepted
- minimum participants confirmed

The event should not become execution-ready merely because a date has been chosen.

---

# 32. Event Scheduling

Event scheduling may involve:

- proposed time
- actor availability
- participant availability
- project prerequisites
- location availability
- organization constraints

The scheduling agent may propose candidate times.

Humans approve consequential scheduling decisions where required.

---

# 33. Event Rescheduling

When an event moves:

- related responsibilities may change
- participant availability may change
- dependent tasks may change
- timeline may need recalculation
- communications may need updating

The previous event schedule remains in history.

---

# 34. Project-Level Pause

A project may be paused.

Pause may:

- stop new execution
- preserve active state
- retain accepted responsibilities
- suspend timeline expectations

When resumed:

- actor availability may need rechecking
- stale dependencies may need revalidation
- timeline should be recalculated

---

# 35. Branch-Level Pause

A single execution branch may pause without pausing the project.

Example:

Support-dependent branch blocked.

Volunteer coordination branch remains active.

Hatcommways should support branch-level execution state.

---

# 36. Scope Change

The project creator may revise the goal or scope.

Example:

Initial goal:
Install 20 shelters.

Updated goal:
Install 35 shelters.

This may require:

- additional tasks
- additional actors
- longer timeline
- new events
- changed support requirements

Scope changes must create a new plan revision.

Do not silently mutate history.

---

# 37. Plan Revision

Every major execution replan should have a revision identity.

Example:

Plan v1:
initial project

Plan v2:
additional actors joined

Plan v3:
event postponed

Plan v4:
project scope expanded

A revision may contain:

- reason
- triggering event
- changed tasks
- changed dependencies
- changed timeline
- changed actor requirements
- changed expected completion

---

# 38. Revision History

Hatcommways must preserve:

- original plan
- subsequent plans
- reasons for changes
- actor changes
- timing changes
- dependency changes
- blocker responses

The final successful state must not erase earlier failed or obsolete plans.

This history becomes part of Project Memory.

---

# 39. Execution Event Model

The execution system should be event-driven.

Potential events include:

- project.plan_created
- project.plan_approved
- task.created
- task.ready
- task.started
- task.blocked
- task.completed
- dependency.satisfied
- dependency.invalidated
- responsibility.opened
- responsibility.accepted
- responsibility.withdrawn
- actor.available
- actor.unavailable
- event.proposed
- event.scheduled
- event.rescheduled
- blocker.created
- blocker.resolved
- timeline.recalculated
- plan.revised

The exact event taxonomy will be defined in a dedicated document.

---

# 40. Event-Driven Reactions

An event can activate multiple independent reactions.

Example:

responsibility.accepted

may cause:

- responsibility-readiness recalculation
- capacity-readiness recalculation
- task readiness recalculation
- timeline recalculation
- open-role count update
- Action Map update

These reactions may execute concurrently when safe.

---

# 41. Concurrent Agent Execution

Agents should react to relevant execution events.

Agents must not be chained unnecessarily.

Example:

Task completion may independently activate:

- Dependency Agent
- Timeline Agent
- Actor Requirement Agent
- Map/Analytics Agent
- Memory Agent

If they do not depend on one another's result, they may run in parallel.

The orchestrator must manage:

- concurrency
- versioning
- stale results
- conflict detection

---

# 42. Stale Agent Results

Concurrent agents may reason from state that changes before they finish.

Example:

Timeline Agent begins planning.

Meanwhile:

a new actor joins.

The timeline result may now be stale.

Before applying a consequential result, the system should check:

- project version
- task graph version
- actor graph version
- relevant state revision

Stale results may be:

- discarded
- recomputed
- merged where safe

---

# 43. Idempotency

Execution events may occasionally be delivered or processed more than once.

System behavior should be idempotent where appropriate.

Example:

responsibility.accepted

should not create duplicate responsibility acceptance if processed twice.

Deterministic state transitions must protect against duplicate execution.

---

# 44. Human Decisions

Agents should autonomously perform safe planning and coordination work.

Human approval should remain required for consequential decisions such as:

- accepting responsibility
- publishing major scope changes
- committing an organization
- cancelling a project
- removing another participant
- changing visibility
- approving certain public information
- making commitments on behalf of a person/company

Core principle:

> AI coordinates execution.
> Humans retain authority over commitments.

---

# 45. Timeline Confidence

AI-generated timing is an estimate.

Tasks may have:

- estimated duration
- confidence level
- uncertainty range

Example:

Estimated:
3 days

Likely range:
2–5 days

As Hatcommways accumulates execution history, estimates may improve.

The system should not falsely present uncertain predictions as guarantees.

---

# 46. Historical Timing Memory

Completed projects can provide timing knowledge.

Examples:

- similar tasks usually took 2 days
- community events of this size required 3 coordinators
- actor recruitment often took longer than task execution
- some task category regularly caused delays

Where privacy permits, this history may improve future planning.

---

# 47. Execution Strength

Hatcommways may derive execution-health indicators.

Potential signals:

- responsibilities filled
- actor availability
- active task ratio
- blocker count
- critical-path health
- parallel execution capacity
- schedule variance

These indicators are internal execution intelligence.

They should not become simplistic popularity scores.

---

# 48. Action Map Relationship

Execution state feeds the Action Map.

Example inputs:

- active responsibilities
- participant concentration
- role distribution
- task execution
- geographic participation

When actors join or responsibilities become active, Action Map data may change.

The map is a view over execution state.

It does not control execution.

---

# 49. Support Relationship

Support state may affect the timeline only where a project explicitly marks a particular support condition as an execution prerequisite.

Support may include:

- materials
- venue
- equipment
- transport
- expertise
- organization support
- people/capacity
- optional externally arranged funding

Example:

Task:
Purchase materials

requires:
required material support = available

Another task:

Design poster

does not require that support condition.

Therefore missing support should block only affected work, not the whole project.

---

# 50. Project Completion

A project is not complete merely because time has expired.

Completion may require:

- required tasks completed
- required events completed
- critical responsibilities fulfilled
- project owner confirmation
- outcome state recorded

Some optional tasks may remain incomplete without preventing completion.

The completion policy should derive from the approved project plan.

---

# 51. Partial Outcome

Projects may end partially successful.

Example:

Goal:
Install 20 shelters

Result:
15 installed

The system should preserve:

- planned outcome
- actual outcome
- remaining work
- reason for difference

Do not force every project into binary success/failure.

---

# 52. Cancelled Projects

A cancelled project should preserve:

- completed work
- accepted responsibilities
- support received
- events
- reasons for cancellation
- final state

Cancellation must not erase execution history.

---

# 53. Execution Orchestrator

Hatcommways should have a governed orchestration/runtime layer.

The orchestrator is not necessarily a product agent.

Its responsibilities include:

- receive events
- persist state
- determine affected execution regions
- identify agents eligible to run
- run independent agents concurrently
- enforce permissions
- check state versions
- retry safe operations
- prevent duplicate execution
- persist audit/history
- surface human decisions

---

# 54. Deterministic vs Agentic Execution

Not everything should use an LLM agent.

Deterministic logic should handle:

- dependency satisfaction
- responsibility counts
- task state transitions
- actor capacity counts
- basic readiness calculation
- event state transitions
- timeline persistence
- concurrency guards
- version checks
- audit history

Agents should handle reasoning such as:

- task decomposition
- estimating task relationships
- discovering possible parallelization
- deciding when actor topology should change
- proposing replanning alternatives
- interpreting ambiguous blockers
- estimating timing where rules alone are insufficient

Core principle:

> Use agents for reasoning.
> Use deterministic software for truth.

---

# 55. Execution Model Invariants

## Invariant 1

A task may be logically ready but not execution-ready.

## Invariant 2

A task does not disappear when its actor leaves.

## Invariant 3

Actor availability can change timeline structure.

## Invariant 4

Independent work must not wait for unrelated blocked work.

## Invariant 5

Parallelizable does not mean currently parallel.

## Invariant 6

Actor contention is different from task dependency.

## Invariant 7

Timeline revisions must preserve history.

## Invariant 8

AI planning outputs do not override human commitments.

## Invariant 9

Execution readiness should be deterministic wherever possible.

## Invariant 10

Concurrent agent results must be checked against current project state before application.

## Invariant 11

Replanning preserves unaffected execution branches unless a validated broader dependency requires expansion.

---

# 56. Core Execution Formula

Conceptually:

Task Graph
+
Dependencies
=
Possible Work Structure

Possible Work Structure
+
Actor Responsibilities
+
Actor Availability
=
Executable Work Structure

Executable Work Structure
+
Duration
+
Events
+
Current Conditions
=
Dynamic Timeline

Dynamic Timeline
+
Meaningful State Change
→
Affected Execution Region
→
Selective Replanning
→
Revised Dynamic Timeline

---

# 57. Example

Goal:

Build 20 shelters for street dogs in 3 weeks.

Initial task graph:

A. Identify installation locations
B. Finalize shelter design
C. Build shelters
D. Organize transport
E. Install shelters
F. Final review

Dependencies:

A → E
B → C
C → D
D → E
E → F

A and B are independent.

Initial actors:

A owner = available
B owner = vacant

Therefore:

A can execute.

B is logically ready but not actor-ready.

Later:

a design actor joins.

Now:

A + B can execute in parallel.

B completes.

C becomes logically ready.

A second build team joins.

C starts while A continues.

Later:

A completes.

No need to wait because C is independent of A.

Eventually:

C → D

When D completes and A is complete:

E becomes ready.

The project timeline shortens because actors joined and parallel branches became executable.

This behavior represents the core intelligence of Hatcommways.

---

# 58. Final Principle

Hatcommways does not merely create a schedule.

It maintains a living execution model.

At every meaningful change, the system asks:

> What can happen now?
> What must wait?
> What has become possible?
> What has become blocked?
> Can independent work continue?
> Can new actors increase parallel execution?
> Does the expected completion time need to change?

The timeline is therefore the visible consequence of a deeper system:

> Tasks define possible work.
> Actors define execution responsibility.
> Dependencies constrain order.
> Current reality determines what actually happens next.
