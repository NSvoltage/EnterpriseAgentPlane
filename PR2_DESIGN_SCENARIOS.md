# Scenarios — Work Backwards from Customer Reality

Six scenarios that define the scope of v1-v2. Each scenario is **surface-agnostic**—can be triggered from GitHub, Slack, web, or automation.

Scenarios are organized by **permission level and state mutation**:
- **S1-S2:** Read-only and safe mutations (no approval required)
- **S3-S5:** Mutations requiring approval (approval gates, tool authorization)
- **S6:** Out of scope (too large, requires different architecture)

Each scenario defines the **contract** (input, processing, output) independent of surface. GitHub adapter is shown as v1 example, but Slack adapter, web adapter, and automation trigger would follow identical contracts.

---

## 1. Product Frame

### What We Are Actually Building

A **secure enterprise deployment foundation for coding agents**, starting with **Claude Code on Bedrock**,
exposed through **existing developer workflows**, with governed access to repos and internal tools.

### What We Are Not Building in v1

- A universal AI SDLC control plane for every workflow surface
- A new end-user chat product
- A universal heavy sandbox service
- A promise that every internal tool will be available through MCP on day one

---

## 2. Personas

### Buyer / Operator
**Head of Platform / DevEx / Security Engineering**

What they care about:
- enterprise auth and rollout
- policy and approvals
- repo scoping
- blast radius
- auditability
- usage visibility
- support burden

### End User
**Engineer / tech lead / on-call engineer**

What they care about:
- can I invoke the agent from where I already work?
- can it answer or produce a patch/PR?
- can I tell what it did?
- can I trust the result and iterate?

---

## 3. Scenario Inventory

We use these scenarios to derive requirements and scope decisions.

| ID | Scenario | Why It Matters |
|---|---|---|
| S1 | Explain-only from GitHub | Lowest-risk, highest-trust starting point |
| S2 | Small patch to PR draft | Core "delegated coding" use case |
| S3 | PR review / triage | Common enterprise adoption motion |
| S4 | Read-only internal tool lookup | Validates governed enterprise tool access |
| S5 | Guarded mutation through internal tool | Forces approval/policy model |
| S6 | Heavy monorepo / long build / mobile workflow | Negative control to keep v1 honest |

---

## 4. Scenario Contracts

### S1 — Explain-Only from GitHub

#### User Story
A developer comments on a PR or issue:
```
@claude explain why this service fails when config X is enabled
```

#### Desired Outcome
The system posts an answer in GitHub with:
- explanation
- relevant evidence (files, logs, comments, or analysis summary)
- no code changes
- no external mutations

#### Trigger Surface
GitHub issue comment, PR comment, or issue assignment

#### Allowed Tools
- repo read
- metadata read
- optional read-only internal tools approved for this repo

#### Side Effects Allowed
- comment back into GitHub only

#### Trust Boundary
Low risk. No repo writes, no external mutations.

#### Acceptance Criteria
- task is attributable to a user
- task state is visible
- answer is posted back to the same GitHub thread
- references to accessed files/tools are preserved in task artifacts
- operator can audit who invoked the task and what tool access occurred

#### Why This Is in v1
This is the safest wedge to prove:
- GitHub ingress
- background tasking
- read-only tool access
- audit + observability

#### Failure Modes to Test
- repo not enabled
- unauthorized commenter
- tool unavailable
- task timeout
- model returns insufficient answer
- stale branch / stale PR context

#### Surface Examples (Same Contract)

**GitHub (v1):**
```
User comments: "@claude explain this error"
  ↓
GitHubEventNormalizer converts to TaskRequest
  ↓
Task executes, LLM generates explanation
  ↓
GitHubStatusCallback posts comment with explanation
```

**Slack (v1.5):**
```
User mentions: "@claude explain this error"
  ↓
SlackEventNormalizer converts to TaskRequest (identical TaskRequest)
  ↓
Task executes (identical execution, same AgentCore)
  ↓
SlackStatusCallback posts thread reply with explanation
```

**Web (v1.5):**
```
User submits form on dashboard
  ↓
APIRequestNormalizer converts to TaskRequest
  ↓
Task executes (identical)
  ↓
WebStatusCallback updates run dashboard
```

**The TaskRequest, TaskManager, AgentCore, and TaskResult are identical. Only entry and exit differ.**

---

### S2 — Small Patch to PR Draft

#### User Story
A developer assigns a bug issue or comments:
```
@claude fix the null handling in the validation path and open a PR
```

#### Desired Outcome
The system:
1. creates a task
2. checks repo permissions
3. runs the coding workflow
4. produces a branch + PR draft
5. posts task summary, validation status, and links back to the original issue

#### Trigger Surface
GitHub issue assignment or comment

#### Allowed Tools
- repo read/write for enabled repos
- build/test hooks
- optional read-only internal tools

#### Side Effects Allowed
- create branch
- create PR draft
- post status / summary

#### Trust Boundary
Medium risk. Repo mutations are allowed, but no direct external-system mutations.

#### Acceptance Criteria
- task is attributable to the user
- branch and PR provenance are recorded
- validation output is artifacted
- PR contains a generated summary and known limitations
- org admin can disable repo write mode per repo/team

#### Why This Is in v1
This is the core "enterprise coding agent" workflow customers expect.

#### Failure Modes to Test
- repo permission denied
- validation failure
- PR creation failure
- branch protection conflict
- unsupported build size / runtime constraints
- rate limiting / quota exhaustion

---

### S3 — PR Review / Triage

#### User Story
A maintainer asks:
```
@claude review this for likely regression risk and missing tests
```

#### Desired Outcome
The system comments with:
- risk summary
- specific concerns
- suggested missing tests
- no code mutation by default

#### Trigger Surface
GitHub PR comment or automated trigger on PR open

#### Allowed Tools
- repo read
- diff analysis
- optional build/test metadata lookup

#### Side Effects Allowed
- review comment or issue comment only

#### Trust Boundary
Low to medium risk.

#### Acceptance Criteria
- task links to the PR it evaluated
- review comment is deterministic enough to be useful
- audit trail shows which files/diffs were accessed
- admins can restrict this mode to selected repos or teams

#### Why This Is in v1
This is a high-value, low-blast-radius enterprise use case.

---

### S4 — Read-Only Internal Tool Lookup

#### User Story
A developer asks:
```
@claude what is the latest deploy status for service-a in staging?
```

#### Desired Outcome
The system uses an approved enterprise tool and posts a structured answer.

#### Trigger Surface
GitHub comment (v1)
Slack/other surfaces later

#### Allowed Tools
- Enterprise Tool Gateway
- read-only deployment/status/ownership tools

#### Side Effects Allowed
- answer-only

#### Trust Boundary
Low risk if tools are truly read-only.

#### Acceptance Criteria
- tool access is policy gated
- user identity or workload identity is captured
- output clearly identifies the source tool
- tool schema/version is logged
- operator can revoke the tool centrally

#### Why This Is in v1
This proves the value of governed internal-tool access without taking on mutation risk.

#### Failure Modes to Test
- OAuth delegation unavailable
- target tool schema drift
- policy deny
- stale cached schema
- ambiguous identity scope

---

### S5 — Guarded Mutation Through Internal Tool

#### User Story
A user asks:
```
@claude rerun the failed deployment check and mark the incident note
```

#### Desired Outcome
The system can prepare the action, but it must:
- verify permissions
- request approval if required
- execute through a governed tool path
- log the mutation with user context and result

#### Trigger Surface
GitHub comment in v1 (or internal admin surface later)

#### Allowed Tools
- mutation-capable Enterprise Tool Gateway targets only

#### Side Effects Allowed
- only after policy + approval

#### Trust Boundary
High risk.

#### Acceptance Criteria
- mutation is impossible without explicit policy support
- approval event is recorded
- action outcome is recorded
- failure is visible to both user and operator

#### Why This Is **Not** a Broad v1 Claim
This should be in the spec and simulation, but only enabled for a narrow set of curated tools in v1.

---

### S6 — Heavy Monorepo / Long Build / Mobile Workflow (Negative Control)

#### User Story
A team wants the system to clone a very large monorepo, run multi-hour build/test chains, or perform mobile/native toolchain work.

#### Desired Outcome
The product responds honestly:
- this may exceed the default runtime envelope
- use a heavier validation or execution backend
- or treat this as a later execution-tier expansion

#### Why This Scenario Exists
This scenario prevents us from claiming that AgentCore is already a universal heavy sandbox.
AgentCore Runtime has hard limits around image/package size, per-session compute, synchronous timeouts,
and async job duration.

#### v1 Decision
Out of core scope. Support as:
- explicit non-goal
- future pluggable execution backend
- documented escalation path

---

## 5. Simulation Summary

We score each scenario by:
- **customer value**
- **v1 feasibility**
- **trust / safety complexity**
- **fit with current AWS assets**

| Scenario | Customer Value | V1 Feasibility | Safety Complexity | Current AWS Fit | V1 Decision |
|---|---:|---:|---:|---:|---|
| S1 Explain-only | High | High | Low | High | In |
| S2 Small patch → PR draft | Very High | High | Medium | High | In |
| S3 PR review / triage | High | High | Low/Medium | High | In |
| S4 Read-only internal tool lookup | High | Medium | Medium | Medium | In, but curated |
| S5 Guarded mutation tool | Medium/High | Medium | High | Medium | Narrowly in / gated |
| S6 Heavy monorepo / long build | Medium | Low/Medium | Medium/High | Partial | Out of core v1 |

---

## 6. Scope Freeze Recommendation

### v1
GitHub-first enterprise deployment foundation for Claude Code on Bedrock:
- enterprise auth and attribution
- GitHub-native task ingress
- background task lifecycle
- PR draft / review / answer-only workflows
- optional read-only internal tools
- narrow approval-gated mutation tools
- observability and audit

### v1.5
- reusable Slack adapter
- richer task UI / status surfaces
- broader internal tool catalog

### v2
- pluggable agent adapters
- broader workflow surfaces
- heavier execution backends
- richer approval and policy composition

---

## Reference

**Source:** EnterpriseAgentPlane working-backwards build pack  
**Status:** Authoritative contract for v1  
**Last updated:** 2026-04-08
