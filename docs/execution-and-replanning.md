# Execution and selective replanning

[Documentation index](README.md) · [Detailed API contract](human-updates-and-blockers.md)

1. An approved actor reports a change against an allowed assignment; the original report is preserved.
2. Interpretation structures it. Blocker assessment evaluates concrete impact; lateness alone is not a blocker.
3. A deterministic resolver follows the confirmed graph to identify affected work and boundaries.
4. Coordination uses supplied eligible actors. Invented or unrelated references are rejected.
5. If coordination suffices, the organizer can mark handling WORKING while condition stays OPEN. Clearing is explicit.
6. If replanning is needed, proposals stay within affected scope; unrelated work remains frozen.
7. Organizer approval validates scope/versions and synchronizes affected state transactionally; rejection does not mutate the plan.

Approval does not prove a road reopened or a resource arrived: blockers can remain OPEN. Actor Dashboard reads authoritative work/timing and messages. Human Updates remains selectable history; derived UI progress is not a new persisted lifecycle. This sequence does not imply automatic execution of every step.
