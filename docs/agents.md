# Strands reasoning capabilities

[Documentation index](README.md)

Implementations in `services/agent_runtime/` use Strands `Agent` and `BedrockModel`, with model `us.amazon.nova-2-lite-v1:0` (Nova 2 Lite). Domain services build scoped context and validate typed output. A capability is not necessarily a queue handler.

| Capability | Module | Boundary |
| --- | --- | --- |
| Event planning | `event_planning.py` | Proposes stages; does not approve its plan. |
| Work design | `work_design.py` | Event/stage-scoped work proposals. |
| Actor requirements | `actor_requirement.py` | Work-specific responsibility requirements. |
| Governance assessment | `governance.py` | Advisory risk/approval reasoning; humans govern. |
| Participation guidance | `participation_advisory.py` | Role/availability advice; deterministic alternative also exists. |
| Human update interpretation | `human_update_interpretation.py` | Interprets without rewriting reports or schedules. |
| Blocker assessment | `blocker_assessment.py` | Execution impact, not lateness alone. |
| Coordination | `coordination.py` | Actions grounded in supplied eligible actors/work. |
| Selective replanning | `replanning.py` | Changes only within resolved scope. |
| Sponsor Fit | `sponsor_fit.py` | Tool-free offer/need/timing advisory; cannot approve support. |

Affected-work resolution is deterministic, not another agent. Smoke tests and transport proof handlers are not product agents. Allowed IDs, versions, lifecycle rules and approval are enforced outside models. Model success is not equivalent to accepted/applied changes.
