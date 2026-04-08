# Repo Evolution and PR Plan

## 1. Build target

Evolve:

`guidance-for-claude-code-with-amazon-bedrock`

from:

**secure enterprise Claude Code access on Bedrock**

to:

**GitHub-first enterprise deployment foundation for Claude Code on Bedrock**

without breaking the existing value proposition.

---

## 2. Design principle

Keep the repo’s existing strength as the **foundation layer**:
- identity / federation
- Bedrock access control
- user attribution
- optional monitoring
- packaging / rollout

Add a new **workflow + task layer**:
- GitHub ingress
- task lifecycle
- artifacts
- approvals
- governed tool access

---

## 3. Proposed repo structure evolution

```text
guidance-for-claude-code-with-amazon-bedrock/
├─ README.md
├─ QUICK_START.md
├─ CHANGELOG.md
├─ assets/
│  ├─ docs/
│  │  ├─ ARCHITECTURE.md
│  │  ├─ DEPLOYMENT.md
│  │  ├─ MONITORING.md
│  │  ├─ GITHUB_WORKFLOWS.md          # new
│  │  ├─ TASK_LIFECYCLE.md            # new
│  │  ├─ TOOL_GATEWAY.md              # new
│  │  ├─ VALIDATION.md                # new
│  │  ├─ ROADMAP.md                   # new
│  │  └─ SECURITY_BOUNDARIES.md       # new
│  ├─ samples/
│  │  ├─ github-enterprise-flow/      # new
│  │  ├─ slack-reference-adapter/     # later
│  │  └─ tool-gateway/                # new or later
│  └─ diagrams/
├─ source/
│  ├─ ccwb/                           # existing CLI / setup
│  ├─ taskplane/                      # new: control-plane abstractions
│  │  ├─ api.py
│  │  ├─ models.py
│  │  ├─ github_adapter.py
│  │  ├─ tool_gateway.py
│  │  ├─ policy.py
│  │  ├─ telemetry.py
│  │  └─ validation.py
│  └─ infra/
│     ├─ auth/                        # existing
│     ├─ monitoring/                  # existing
│     ├─ github/                      # new
│     ├─ task_runtime/                # new
│     ├─ tool_gateway/                # new
│     └─ validation/                  # new
```

---

## 4. PR sequence

## PR 1 — Positioning and scope truthfulness
### Goal
Rewrite the repo story so it truthfully reflects:
- what exists today
- what v1 adds
- what is not yet part of the product claim

### Changes
- README rewrite
- ROADMAP.md
- SECURITY_BOUNDARIES.md
- explicit v1 / v1.5 / v2 scoping
- add “GitHub-first enterprise deployment foundation” messaging

### Why first
If the story is wrong, the implementation will drift.

---

## PR 2 — Scenario pack and requirement docs
### Goal
Land the working-backwards artifacts in the repo.

### Changes
- add scenario docs
- add requirement matrix
- add ADRs
- add GITHUB_WORKFLOWS.md
- add TOOL_GATEWAY.md

### Why second
Codex and reviewers need the contract before building.

---

## PR 3 — Task lifecycle contract
### Goal
Define the new background task abstraction.

### Output
- task model
- state machine
- artifact schema
- cancellation / retry semantics
- task-to-GitHub-thread linking rules

### Suggested deliverables
- `source/taskplane/models.py`
- `assets/docs/TASK_LIFECYCLE.md`

### Minimum states
- queued
- running
- waiting_for_input
- waiting_for_approval
- completed
- failed
- canceled

---

## PR 4 — GitHub adapter scaffolding
### Goal
Create a concrete first ingress path.

### Output
- GitHub webhook / action adapter contract
- comment / issue / assignment trigger handling
- normalized task request object
- status callback contract

### Notes
This PR can stop at scaffolding + docs if needed.
Do not try to solve all task execution in the same PR.

---

## PR 5 — Enterprise Tool Gateway abstraction
### Goal
Add governed tool access without protocol-led overscope.

### Output
- tool registry model
- read-only vs mutating tool classification
- policy hook interface
- audit fields
- MCP target support as one backend type

### Important
The product artifact should say **Enterprise Tool Gateway**.
“MCP” appears inside the implementation and compatibility story, not the headline.

---

## PR 6 — Validation interface
### Goal
Separate generation from deterministic verification.

### Output
- validation interface
- result schema
- “pass / fail / warnings / skipped”
- artifact linkage
- optional CodeBuild backend notes

### Important
Do not hardcode the product to one heavy execution backend.

---

## PR 7 — Observability extension
### Goal
Extend the existing monitoring model to task-level operations.

### Output
- task metrics
- workflow metrics
- repo/team dimensions
- PR outcome metrics
- tool invocation audit events

---

## PR 8 — End-to-end sample
### Goal
Show the simplest credible v1 flow:
GitHub comment → task created → Claude Code answer or PR draft → status back to GitHub.

### Important
This should be a sample, not a claim that every production workflow is turnkey.

---

## 5. Build boundaries for Codex

### Good Codex tasks
- docs rewrites
- ADRs
- state machine models
- dataclasses / Pydantic models
- interface stubs
- directory restructuring
- sample config scaffolding
- GitHub event normalization layer
- telemetry event schemas

### Bad Codex tasks (too early / too broad)
- fully functioning enterprise Slack product
- universal task orchestrator across all workflow surfaces
- heavy sandbox subsystem
- generic enterprise policy engine
- broad multi-agent platform

---

## 6. Acceptance gate for “v1 ready”

Do not call the evolved repo v1-ready until all are true:
1. GitHub-first flows are documented and internally coherent
2. Task lifecycle is explicit
3. Security boundaries are explicit
4. Tool access is governed through a clear abstraction
5. README and quick start do not overclaim beyond what is built
