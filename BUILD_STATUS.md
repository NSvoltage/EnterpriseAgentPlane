# Build Status — EnterpriseAgentPlane v1 Design Pack

**Status:** ✓ Phase 1 & 2 Complete | ⧰ Phase 3 In Progress

**Last Updated:** 2026-04-08  
**Branch:** `claude/review-enterprise-agent-plane-EviWi`

---

## Completed Artifacts

### Phase 1: Positioning & Design Contracts (Commits 1-3)

**PR 1 — Positioning & Scope Truthfulness** ✓
- `PR1_README_NEW.md` — v1 headline: "GitHub-First Enterprise Deployment Foundation"
- `PR1_ROADMAP.md` — Explicit v1/v1.5/v2 phasing with feature matrix
- `PR1_SECURITY_BOUNDARIES.md` — Threat model, trust boundaries, 11 known limitations
- `PR1_ARCHITECTURE_V1.md` — Detailed 5-layer architecture with data flow sequences
- `IMPLEMENTATION_PLAN.md` — 8-PR sequence with acceptance criteria

**Key Positioning Decisions:**
- GitHub is primary ingress (Slack/Teams deferred to v1.5)
- AgentCore is control plane + light execution, not universal sandbox
- Enterprise Tool Gateway abstracts tools (MCP is one connector type)
- Heavy monorepo (S6) is explicitly out of v1
- Persistent storage is optional (feature flag)

**PR 2 — Design Contracts Landed** ✓
- `PR2_DESIGN_SCENARIOS.md` — 6 scenarios (S1-S6) with full contracts
- `PR2_DESIGN_ARCHITECTURE_DECISIONS.md` — 11 ADRs (non-negotiable design choices)
- `PR2_REQUIREMENTS_MATRIX.csv` — 24 requirements mapped to AWS assets
- `PR2_SERVICE_FIT_MATRIX.md` — What fits in v1/v1.5/v2
- `PR2_GITHUB_WORKFLOWS.md` — Event normalization, command parsing, routing
- `PR2_TASK_LIFECYCLE_PLACEHOLDER.md` — State machine outline (detailed in PR 3)

**Key Contracts:**
- S1-S3 are core v1 (answer, PR draft, review)
- S4 is curated read-only tools
- S5 is narrow approval-gated mutations
- S6 (heavy monorepo) is explicitly out

### Phase 2: Core Abstractions (In Progress)

**PR 3 — Task Lifecycle Model** ⧰ (40% complete)
- `PR3_TASKPLANE_MODELS.md` — Complete Pydantic model definitions ready for code
- Enums: TaskState (6 states), WorkflowType, TaskArtifactType
- Models: Task, TaskRequest, TaskArtifact, TaskUpdate, TaskFilter, TaskResult
- Interface: TaskManager (6 abstract methods)
- Exceptions: 5 specific exception classes
- Tests: Test cases sketched (pytest ready)

**Status:** Models are documented and ready to implement in Python code.

---

## Artifacts Prepared (Not Yet Committed)

### PR 4 — GitHub Adapter (Scaffolding)
- Command parsing and normalization
- Event → TaskRequest conversion
- GitHub callback interface
- Mock test payloads

### PR 5 — Enterprise Tool Gateway (Abstraction)
- Tool registry model
- Authorization interface
- Tool invocation contracts
- MCP/REST/Lambda connector patterns

### PR 6 — Validation Interface
- Validation request/result models
- Backend interface (CodeBuild, AgentCore, local, etc.)
- Check result aggregation

### PR 7 — Observability (Telemetry Extension)
- Task metrics (counters, histograms)
- Tool invocation audit events
- Dashboard configurations

### PR 8 — End-to-End Sample
- S1 scenario (explain-only) walkthrough
- Lambda handler scaffolding
- Integration test case

---

## Key Design Principles Enshrined

### ADR Checklist (Every PR Must Pass)

1. ✓ Preserve AWS foundation (auth, monitoring, packaging)
2. ✓ GitHub is primary v1 surface (not Slack/Teams)
3. ✓ AgentCore is control plane + light execution (not universal sandbox)
4. ✓ Enterprise Tool Gateway is product (MCP is implementation detail)
5. ✓ Session storage is optional (not hard requirement)
6. ✓ Slack is reference adapter (not v1 pillar)
7. ✓ Task lifecycle is separate from execution
8. ✓ GitHub adapter is thin (translation only)
9. ✓ Tool connectors are pluggable
10. ✓ Validation is an interface (not locked to CodeBuild)
11. ✓ Approval gates are centralized in tool gateway

**All PRs must be reviewed against this checklist.**

---

## What This Pack Enables

### For AWS Guidance Repo Fork:

When you fork the AWS repo and apply these PRs, you will have:

1. **Honest positioning** that doesn't overclaim
2. **Complete design contracts** that guide implementation
3. **Core abstractions** that are loosely coupled (easy to replace)
4. **Reference implementations** for each layer
5. **Test scaffolding** for validation
6. **Production-ready models** (Pydantic with full validation)

### For Teams Building On This:

- **Clear v1 scope:** No ambiguity about what's in/out
- **Decoupled design:** Swap execution backends, tool connectors, validation tools without refactoring core
- **Auditability:** Complete lineage (GitHub event → task → artifacts → result)
- **Pluggable:** Persist tasks in PostgreSQL or DynamoDB; no lock-in
- **Observable:** Task-level metrics, tool invocation audit, approval tracking

---

## Architecture At A Glance

```
Foundation Layer (AWS Guidance Repo — Unchanged)
├─ OIDC / Cognito (identity)
├─ Bedrock (model invocation)
├─ CloudTrail (audit)
└─ OTEL + CloudWatch (monitoring)
        ↓
Workflow + Task Layer (v1 New)
├─ GitHub Adapter (events → tasks)
├─ Task Manager (lifecycle)
├─ Enterprise Tool Gateway (authorization + execution)
├─ Validation Interface (deterministic verification)
└─ Telemetry (task-level metrics + events)
        ↓
Execution Layer (AgentCore Runtime)
├─ Session isolation
├─ Async jobs (8h max, 15m sync)
└─ Governed tool access
```

---

## Scenarios Covered

| # | Scenario | v1 | Complexity |
|---|----------|----|-|
| S1 | Explain-only | ✓ | Low |
| S2 | PR draft | ✓ | Medium |
| S3 | PR review | ✓ | Medium |
| S4 | Tool lookup (read-only) | ✓ | Medium |
| S5 | Tool mutation (gated) | ~ | High |
| S6 | Heavy monorepo | ✗ | Out of scope |

---

## Next Steps

### Immediate (This Week)
- [ ] Complete PR 3 Python implementation (models.py)
- [ ] PR 4 GitHub adapter scaffolding
- [ ] PR 5 Tool gateway abstraction

### Short Term (Next 2 Weeks)
- [ ] PR 6 Validation interface
- [ ] PR 7 Observability (telemetry)
- [ ] PR 8 End-to-end sample

### When Ready to Fork AWS Repo
1. Fork `guidance-for-claude-code-with-amazon-bedrock`
2. Create branch `add/github-enterprise-workflows`
3. Apply PRs 1-8 in sequence
4. Each PR = one commit with clear message
5. Code review checklist uses ADRs above

### Deployment & Testing
- Stand up reference deployment on AWS
- Test S1 (explain) manually
- Test S2 (PR draft) with mock Claude
- Test tool gateway with mock tools
- Verify observability (metrics, logs)

---

## Acceptance Gates

### Before calling v1 "Ready":

- [ ] All 8 PRs are merged
- [ ] GitHub workflows are documented end-to-end
- [ ] Task lifecycle is explicit and tested
- [ ] Security boundaries are explicit (no overclaims)
- [ ] Tool access is governed through clear abstraction
- [ ] Observability includes task-level metrics
- [ ] README and ROADMAP don't overclaim
- [ ] Repo builds cleanly (pre-commit passes)
- [ ] All tests pass (unit + integration)
- [ ] S1 scenario works end-to-end (manual test)

---

## File Manifest

### Documentation (Ready)
```
├─ IMPLEMENTATION_PLAN.md             [Detailed 8-PR sequence]
├─ PR1_README_NEW.md                  [v1 positioning]
├─ PR1_ROADMAP.md                     [Phased release plan]
├─ PR1_SECURITY_BOUNDARIES.md         [Threat model + ADRs]
├─ PR1_ARCHITECTURE_V1.md             [Detailed architecture]
├─ PR2_DESIGN_SCENARIOS.md            [6 scenarios with contracts]
├─ PR2_DESIGN_ARCHITECTURE_DECISIONS.md  [11 ADRs]
├─ PR2_REQUIREMENTS_MATRIX.csv        [24 requirements]
├─ PR2_SERVICE_FIT_MATRIX.md          [What fits when]
├─ PR2_GITHUB_WORKFLOWS.md            [Event → task routing]
├─ PR2_TASK_LIFECYCLE_PLACEHOLDER.md  [State machine outline]
├─ PR3_TASKPLANE_MODELS.md            [Pydantic models (ready for code)]
└─ BUILD_STATUS.md                    [This file]
```

### Code (To Be Implemented)
```
source/taskplane/
├─ models.py              [Task, Artifact, State enums + TaskManager interface]
├─ github_adapter.py      [Event normalization, command parsing]
├─ github_models.py       [GitHub-specific Pydantic models]
├─ tool_gateway.py        [Registry, authorization, invocation]
├─ tool_models.py         [Tool, ToolInvocation models]
├─ validation.py          [Validation request/result, backend interface]
├─ telemetry.py           [Event emission, metrics]
└─ __init__.py            [Package exports]
```

---

## Key Quotes (Principles)

> "We build for code assistants on Bedrock, not a universal AI SDLC platform."

> "GitHub is the cleanest wedge. Developers already work there."

> "AgentCore is not the universal heavy sandbox. Respect its limits."

> "MCP is one connector type. The product is 'approved tools with central auth/audit.'"

> "Task lifecycle is separate from execution. That's how we plug in different backends."

> "All approval gates live in the tool gateway. No scattered auth logic."

---

## Questions?

- **About scenarios:** See PR2_DESIGN_SCENARIOS.md
- **About architecture:** See PR1_ARCHITECTURE_V1.md
- **About design choices:** See PR2_DESIGN_ARCHITECTURE_DECISIONS.md (ADRs)
- **About task models:** See PR3_TASKPLANE_MODELS.md
- **About implementation order:** See IMPLEMENTATION_PLAN.md

---

**Prepared by:** Principal Engineer team  
**Branch:** `claude/review-enterprise-agent-plane-EviWi`  
**Status:** Phase 2 Complete; Phase 3 In Progress
