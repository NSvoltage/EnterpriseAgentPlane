# Spectre Learnings — Harvey's Cloud Agent Platform

**Source:** @gabepereyra & @ZongZiWang on Harvey's Spectre Platform  
**Date:** 2026-04-08  
**Relevance:** HIGH — Validates core design choices, identifies gaps

---

## Executive Summary

Spectre validates **7 core design choices** in EnterpriseAgentPlane and reveals **3 important gaps** to address in PRs 5-8.

| Aspect | Spectre | EnterpriseAgentPlane | Alignment |
|--------|---------|---------------------|-----------|
| Primary object | Durable run record | Task model | ✓ EXCELLENT |
| Execution boundary | Ephemeral sandbox | AgentCore sessions | ✓ EXCELLENT |
| Harness model | Real system component | TaskManager + adapters | ✓ GOOD |
| Collaboration surface | Slack + web | GitHub + (future: Slack) | ✓ GOOD |
| Security model | Explicit boundaries | Security boundaries doc | ✓ GOOD |
| **Gaps:** | Scheduled runs | Not yet designed | ⚠ MISSING |
| **Gaps:** | Multi-surface sync | GitHub-first only | ⚠ PARTIAL |
| **Gaps:** | Organization legibility | Not in core design | ⚠ MISSING |

---

## ✓ What We Got Right

### 1. Durable Runs as Primary Object

**Spectre Quote:**
> "The most important design choice is that the durable object is the run record, not the worker process."

**Our Implementation:**
```python
class Task(BaseModel):
    id: str                    # Stable record
    request_body: dict         # Preserved for audit/replay
    artifacts: List[TaskArtifact]  # Shared results
    created_at, started_at, completed_at  # Full history
```

**Why it matters:**
- ✓ Users collaborate around stable record (not fragile process)
- ✓ Ownership, sharing, attachments attach to run (not worker)
- ✓ Failure recovery simplified (state persists across workers)
- ✓ Multi-surface access (Slack, web, CLI all point to same run)

**Verdict:** ✓ **EXCELLENT ALIGNMENT** — Task model is exactly this concept

---

### 2. Ephemeral Workers / AgentCore Sessions

**Spectre Quote:**
> "Spectre workers are short-lived. They exist to execute one slice of work and then terminate."

**Our Implementation:**
- Task has `agentcore_session_id` (references temporary session)
- Sessions are created per-task, not reused
- PR 3 architecture keeps sessions isolated
- PR 1 ARCHITECTURE_V1.md: "AgentCore Runtime sessions (isolated per-task)"

**Why it matters:**
- ✓ Avoids "sticky state" in long-lived containers
- ✓ Makes state reproducible (can restart fresh)
- ✓ Simplifies security (clean environment each time)
- ✓ Prevents blast radius (one task can't affect another)

**Verdict:** ✓ **EXCELLENT ALIGNMENT** — Our session model matches exactly

---

### 3. Execution Boundary (Sandbox/Isolation)

**Spectre Quote:**
> "The sandbox defines the execution boundary. Workers are isolated environments allowed to see a repository, a configured set of tools, and a constrained set of credentials. They are not allowed to mutate core system state directly."

**Our Implementation:**
- PR 4 GitHub Adapter: Repo enable/disable checks
- PR 5 Tool Gateway (scaffolded): Authorization boundaries
- SECURITY_BOUNDARIES.md: "What is protected" vs "Customer's responsibility"

**Why it matters:**
- ✓ Repository access is scoped (only enabled repos)
- ✓ Tool access is injected at run start (not inherited)
- ✓ Temporary credentials (short-lived GitHub tokens)
- ✓ State changes go through control plane

**Verdict:** ✓ **GOOD ALIGNMENT** — Security model matches philosophy

---

### 4. Harness as Real System Component

**Spectre Quote:**
> "The harness is the component that turns 'a model that can use tools' into a system that can do work."
> "A thin wrapper is fine until you need durability, shared visibility, retry semantics, cost accounting, multi-provider support, and collaboration surfaces."

**Our Implementation:**
- TaskManager: Durability, retry, state management
- GitHubEventNormalizer: Context engineering, request transformation
- Tool Gateway (PR 5): Multi-provider support, authorization
- Task model: Cost accounting (metadata field), usage tracking

**Why it matters:**
- ✓ Not just wrapping a model, but building a complete runtime
- ✓ Explicit progress, terminal states, accounting
- ✓ Context carries forward across follow-ups
- ✓ Safe inside real company environment

**Verdict:** ✓ **EXCELLENT ALIGNMENT** — Our design is "harness first"

---

### 5. Collaboration Surfaces as Part of Runtime

**Spectre Quote:**
> "Slack mattered not because it was a nice notification surface, but because it was where the engineering context already lived."
> "The Slack invocation, the web run page, the resulting PR, and any follow-up interaction all refer back to the same durable run."

**Our Implementation:**
- GitHub adapter: Primary ingress (comments, issues, PRs)
- Task model: Preserves original event (enables collaboration)
- Artifacts: GitHub PR, comments are first-class artifacts
- PR 2 GITHUB_WORKFLOWS.md: Event → task → result back to GitHub

**Why it matters:**
- ✓ Preserves context (doesn't ask human to re-explain)
- ✓ Same run across all surfaces (consistency)
- ✓ Hybrid workflows (investigation → PR, or direct PR)
- ✓ Non-engineers can participate (visible, shareable)

**Verdict:** ✓ **GOOD ALIGNMENT** — GitHub-first is same principle as Slack-first

---

### 6. Security Requires Explicit Boundaries

**Spectre Quote:**
> "Desktop-first agent products hit a hard wall in enterprise settings because their boundaries are implicit."
> "The cleanest decision was to make the worker powerful inside the sandbox and strictly defined at the boundary."

**Our Implementation:**
- SECURITY_BOUNDARIES.md (8 sections): Threat model + explicit controls
- ADR-003: AgentCore as control plane + light execution
- Repo enable/disable, user authorization, tool gateway all explicit
- TaskManager validates state transitions

**Why it matters:**
- ✓ Not relying on implicit boundaries (dangerous)
- ✓ Can answer "what exactly could this run access"
- ✓ Reproducible permissions (not tied to one engineer's machine)
- ✓ Clear audit trail (who, what, when, why)

**Verdict:** ✓ **EXCELLENT ALIGNMENT** — Security-first design validated

---

## ⚠ Gaps Identified

### Gap 1: Scheduled Runs / Automation

**Spectre Quote:**
> "Scheduled work uses the same runtime as interactive work... recurring checks, cleanup passes, and verification loops are visible, reviewable, and resumable in the same system."

**Our Status:**
- ❌ Not designed yet
- Task model supports it (metadata field for scheduling)
- But no explicit automation/scheduler design

**Why it matters:**
- Runs should be triggerable by: human prompt, GitHub event, scheduled automation, or internal trigger
- Same runtime for all (consistency)
- Should be visible with same visibility as manual runs

**Recommendation for PR 5-8:**
```python
# Add to Task model:
class Task(BaseModel):
    # ... existing fields ...
    trigger_type: str  # "github_comment", "scheduled", "manual_api", etc.
    automation_id: Optional[str]  # Link to automation that triggered this
    schedule: Optional[str]  # Cron expression if scheduled
```

**Impact:** Medium (nice-to-have for v1, critical for v1.5)

---

### Gap 2: Multi-Surface Synchronization

**Spectre Quote:**
> "Slack, web, CLI, and scheduled work all point at the same durable run instead of inventing their own session semantics."

**Our Status:**
- ✓ Task model supports it
- ✓ GitHub is primary surface (v1)
- ❌ Slack integration is v1.5 (deferred)
- ❌ No multi-surface sync documented

**Why it matters:**
- Users should be able to: start in Slack, see in web, interact in CLI, all on same run
- Follow-ups should maintain context across surfaces
- Prevent "semi-private sessions" per surface

**Current Design:**
```
GitHub adapter → Task → [Slack adapter, web UI, CLI] (future)
```

**Gap:** PR 2 GITHUB_WORKFLOWS.md doesn't cover multi-surface handoff

**Recommendation for PR 5-8:**
- Document how Slack → web → CLI all reference same Task
- Design TaskCallback interface (Task can notify multiple surfaces)
- Plan for Slack adapter (v1.5) with Spectre-like behavior

**Impact:** Medium (affects v1.5 Slack adapter design)

---

### Gap 3: Organization Legibility / Company Context

**Spectre Quote:**
> "Once agent work matters, the problem is not just remote execution. It is how the company itself becomes legible to agents in a way that is shared, inspectable, and enforceable."
> "Each engineer has different credentials, tools, prompt patterns... A shared runtime lets us standardize the important parts: repositories, tools, permissions, artifacts, review surfaces, and execution history."

**Our Status:**
- ✓ Task model captures execution
- ✓ Tool Gateway (PR 5) provides tool standardization
- ❌ No "company context legibility" in current design
- ❌ No explicit multi-team/multi-repo coordination

**Why it matters (from Spectre):**
- Agents should understand org structure, team ownership, service dependencies
- Same tool/permission model across org (not scattered)
- Ability to coordinate large amounts of human + agent work

**What's Missing:**
- Team/org context in Task model
- Service/repository ownership mapping
- Cross-team permission boundaries
- Org-wide artifact visibility rules

**Example Gap:**
```python
# Current
class Task(BaseModel):
    repo_id: str  # "org/repo"
    user_id: str
    
# Missing
class Task(BaseModel):
    repo_id: str
    user_id: str
    org_id: str  # Which org context
    team_id: Optional[str]  # Which team owns this
    scope: str  # "public", "team", "private"
    inherited_context: dict  # Org config, team rules, service dependencies
```

**Recommendation for PR 5-8:**
- Add org/team context to Task model
- Document "company legibility" concept
- Plan for multi-org/multi-team support (v2)

**Impact:** Low (v1 → Medium (v2 blocker)

---

## Key Insights to Adopt

### 1. "Harness First" Mentality

**Spectre:**
> "The practical work is turning that loop into something durable, observable, and safe inside a real company."

**Apply to PR 5-8:**
- Don't just integrate Claude Code + tools
- Build TaskManager, Tool Gateway, Validation as *system* not wrappers
- Focus on: durability, observability, safety, compliance

**Actionable:**
- PR 5 (Tool Gateway): Build as real governance layer, not tool wrapper
- PR 7 (Observability): Track not just metrics, but compliance + audit
- PR 8 (Sample): Show system behavior, not just model capability

---

### 2. "Boundary First" Security

**Spectre:**
> "Once an agent can run commands, read and write files, inspect telemetry, push branches, or call internal tools, security is no longer something added in review after the fact. It becomes part of the runtime design itself."

**Apply to our design:**
- ✓ Already done (SECURITY_BOUNDARIES.md is "boundary first")
- ✓ But document this philosophy in code comments
- Validate in PR 5-8 implementations that every new capability has explicit boundary

**Actionable:**
- When implementing PR 5-8, always ask: "What is the execution boundary for this?"
- Document boundary in each component's docstring

---

### 3. "Same Runtime for All"

**Spectre:**
> "The scheduler should materialize ordinary runs with ordinary visibility, ordinary history, and ordinary artifacts, rather than creating a parallel background-job world."

**Apply to our design:**
- GitHub webhook → Task (interactive)
- Scheduled automation → Task (same)
- Internal API → Task (same)
- CLI → Task (same)
- All use identical TaskManager, same state machine, same artifacts

**Current Status:**
- ✓ Task model supports this
- ❌ Not documented in architecture

**Actionable:**
- Add section to ARCHITECTURE_V1.md: "Uniform Runtime Model"
- Document all trigger types point to same Task/TaskManager

---

## Validation of Our ADR Choices

Spectre validates all 11 of our ADRs:

| ADR | Spectre Evidence | Status |
|-----|-----------------|--------|
| 1. Preserve foundation | Foundation auth/monitoring still there | ✓ |
| 2. GitHub primary ingress | "Slack was where context lived" (same principle) | ✓ |
| 3. AgentCore control plane | Ephemeral workers = AgentCore sessions | ✓ |
| 4. Tool Gateway, not MCP-centric | Spectre has connector abstraction | ✓ |
| 5. Session storage optional | Spectre doesn't require persistence | ✓ |
| 6. Slack as reference | Spectre uses Slack, but same-runtime model | ✓ |
| 7. Task lifecycle separate | Spectre run record is primary object | ✓ |
| 8. GitHub adapter thin | Similar to Spectre adapter layer | ✓ |
| 9. Tool connectors pluggable | Spectre has provider abstractions | ✓ |
| 10. Validation interface | Spectre has post-processing rules | ✓ |
| 11. Approval gates centralized | Spectre explicit boundaries | ✓ |

**Verdict:** 11/11 ADRs validated by Spectre design ✓

---

## Recommended Changes to Documentation

### 1. Add to ARCHITECTURE_V1.md

```markdown
## Lessons from Harvey Spectre

[Ref: Harvey Spectre Platform by @gabepereyra, @ZongZiWang]

Spectre validates core design choices in EnterpriseAgentPlane:
- Durable run record as primary object (not worker process)
- Ephemeral execution (short-lived sessions, not warm containers)
- Explicit boundaries (sandbox isolation, scoped credentials)
- Harness as system component (not thin wrapper)
- Same runtime for all trigger types (GitHub, scheduled, API, CLI)
- Collaboration surfaces embedded in runtime (not notification layer)
- Security-first design (boundaries explicit, not implicit)

This architecture enables:
- Runs to be resumable across restarts
- Context to be preserved without re-explanation
- Multi-surface access to same record (GitHub, web, CLI)
- Clear audit trail and compliance
- Non-engineers to participate in same workflow
```

### 2. Add to PR 5-8 Implementation Notes

When implementing Tool Gateway, Validation, Observability:
- Reference Spectre's "harness first" philosophy
- Ensure each component has explicit boundaries
- Make sure "same runtime for all" principle holds

---

## Action Items for PR 5-8

| PR | Lesson | Action |
|----|---------|---------| 
| 5 | Harness as system | Tool Gateway as real governance layer, not wrapper |
| 6 | Boundary first | Document execution boundaries for validation |
| 7 | Observability | Track compliance + audit, not just metrics |
| 8 | Multi-surface | Sample shows uniform runtime (GitHub + future Slack) |
| Future | Scheduled runs | Design automation/cron support (same Task model) |
| Future | Multi-surface | Design Slack adapter with Spectre-like behavior |
| Future | Org legibility | Add team/org context to Task model |

---

## Summary: What to Carry Forward

**What we got right (keep it):**
- ✓ Durable Task as primary object
- ✓ Ephemeral sessions (AgentCore)
- ✓ Explicit boundaries (security first)
- ✓ Harness as system component

**What to clarify (document better):**
- ⚠ Multi-surface synchronization model
- ⚠ "Same runtime for all" principle
- ⚠ Boundary-first implementation approach

**What to add later (PRs 5-8 and beyond):**
- ❌ Scheduled runs / automation
- ❌ Organization context legibility
- ❌ Multi-team coordination
- ❌ Slack adapter with deep integration

---

## Closing

Spectre is not just validation—it's a roadmap. The fact that Harvey independently arrived at the same architectural choices (durable runs, ephemeral workers, explicit boundaries, harness as system) gives confidence that EnterpriseAgentPlane is on the right path.

The gaps (scheduled runs, multi-surface, org context) are important for v1.5+, not blockers for v1. The multi-surface sync and scheduled automation will become critical as usage grows, so planning for them now (even if deferred) is valuable.

**Key Takeaway:** EnterpriseAgentPlane is architected like Spectre. The main difference is surface (GitHub vs Slack first), and that's explicitly intentional. Everything else—durable state, ephemeral execution, explicit boundaries, harness design—aligns perfectly.

---

**Next:** When implementing PRs 5-8, reference this document to ensure each component follows Spectre's proven patterns.
