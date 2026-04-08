# Scenario Pack — Work Backwards from Customer Reality

## 1. Product frame

### What we are actually building
A **secure enterprise deployment foundation for coding agents**, starting with **Claude Code on Bedrock**,
exposed through **existing developer workflows**, with governed access to repos and internal tools.

### What we are not building in v1
- A universal AI SDLC control plane for every workflow surface
- A new end-user chat product
- A universal heavy sandbox service
- A promise that every internal tool will be available through MCP on day one

---

## 2. Personas

### Buyer / operator
**Head of Platform / DevEx / Security Engineering**

What they care about:
- enterprise auth and rollout
- policy and approvals
- repo scoping
- blast radius
- auditability
- usage visibility
- support burden

### End user
**Engineer / tech lead / on-call engineer**

What they care about:
- can I invoke the agent from where I already work?
- can it answer or produce a patch/PR?
- can I tell what it did?
- can I trust the result and iterate?

---

## 3. Scenario inventory

We use these scenarios to derive requirements and scope decisions.

| ID | Scenario | Why it matters |
|---|---|---|
| S1 | Explain-only from GitHub | Lowest-risk, highest-trust starting point |
| S2 | Small patch to PR draft | Core “delegated coding” use case |
| S3 | PR review / triage | Common enterprise adoption motion |
| S4 | Read-only internal tool lookup | Validates governed enterprise tool access |
| S5 | Guarded mutation through internal tool | Forces approval/policy model |
| S6 | Heavy monorepo / long build / mobile workflow | Negative control to keep v1 honest |

---

## 4. Scenario contracts

## S1 — Explain-only from GitHub

### User story
A developer comments on a PR or issue:
`@claude explain why this service fails when config X is enabled`

### Desired outcome
The system posts an answer in GitHub with:
- explanation
- relevant evidence (files, logs, comments, or analysis summary)
- no code changes
- no external mutations

### Trigger surface
GitHub issue comment, PR comment, or issue assignment

### Allowed tools
- repo read
- metadata read
- optional read-only internal tools approved for this repo

### Side effects allowed
- comment back into GitHub only

### Trust boundary
Low risk. No repo writes, no external mutations.

### Acceptance criteria
- task is attributable to a user
- task state is visible
- answer is posted back to the same GitHub thread
- references to accessed files/tools are preserved in task artifacts
- operator can audit who invoked the task and what tool access occurred

### Why this is in v1
This is the safest wedge to prove:
- GitHub ingress
- background tasking
- read-only tool access
- audit + observability

### Failure modes to test
- repo not enabled
- unauthorized commenter
- tool unavailable
- task timeout
- model returns insufficient answer
- stale branch / stale PR context

---

## S2 — Small patch to PR draft

### User story
A developer assigns a bug issue or comments:
`@claude fix the null handling in the validation path and open a PR`

### Desired outcome
The system:
1. creates a task
2. checks repo permissions
3. runs the coding workflow
4. produces a branch + PR draft
5. posts task summary, validation status, and links back to the original issue

### Trigger surface
GitHub issue assignment or comment

### Allowed tools
- repo read/write for enabled repos
- build/test hooks
- optional read-only internal tools

### Side effects allowed
- create branch
- create PR draft
- post status / summary

### Trust boundary
Medium risk. Repo mutations are allowed, but no direct external-system mutations.

### Acceptance criteria
- task is attributable to the user
- branch and PR provenance are recorded
- validation output is artifacted
- PR contains a generated summary and known limitations
- org admin can disable repo write mode per repo/team

### Why this is in v1
This is the core “enterprise coding agent” workflow customers expect.

### Failure modes to test
- repo permission denied
- validation failure
- PR creation failure
- branch protection conflict
- unsupported build size / runtime constraints
- rate limiting / quota exhaustion

---

## S3 — PR review / triage

### User story
A maintainer asks:
`@claude review this for likely regression risk and missing tests`

### Desired outcome
The system comments with:
- risk summary
- specific concerns
- suggested missing tests
- no code mutation by default

### Trigger surface
GitHub PR comment or automated trigger on PR open

### Allowed tools
- repo read
- diff analysis
- optional build/test metadata lookup

### Side effects allowed
- review comment or issue comment only

### Trust boundary
Low to medium risk.

### Acceptance criteria
- task links to the PR it evaluated
- review comment is deterministic enough to be useful
- audit trail shows which files/diffs were accessed
- admins can restrict this mode to selected repos or teams

### Why this is in v1
This is a high-value, low-blast-radius enterprise use case.

---

## S4 — Read-only internal tool lookup

### User story
A developer asks:
`@claude what is the latest deploy status for service-a in staging?`

### Desired outcome
The system uses an approved enterprise tool and posts a structured answer.

### Trigger surface
GitHub comment (v1)
Slack/other surfaces later

### Allowed tools
- Enterprise Tool Gateway
- read-only deployment/status/ownership tools

### Side effects allowed
- answer-only

### Trust boundary
Low risk if tools are truly read-only.

### Acceptance criteria
- tool access is policy gated
- user identity or workload identity is captured
- output clearly identifies the source tool
- tool schema/version is logged
- operator can revoke the tool centrally

### Why this is in v1
This proves the value of governed internal-tool access without taking on mutation risk.

### Failure modes to test
- OAuth delegation unavailable
- target tool schema drift
- policy deny
- stale cached schema
- ambiguous identity scope

---

## S5 — Guarded mutation through internal tool

### User story
A user asks:
`@claude rerun the failed deployment check and mark the incident note`

### Desired outcome
The system can prepare the action, but it must:
- verify permissions
- request approval if required
- execute through a governed tool path
- log the mutation with user context and result

### Trigger surface
GitHub comment in v1 (or internal admin surface later)

### Allowed tools
- mutation-capable Enterprise Tool Gateway targets only

### Side effects allowed
- only after policy + approval

### Trust boundary
High risk.

### Acceptance criteria
- mutation is impossible without explicit policy support
- approval event is recorded
- action outcome is recorded
- failure is visible to both user and operator

### Why this is **not** a broad v1 claim
This should be in the spec and simulation, but only enabled for a narrow set of curated tools in v1.

---

## S6 — Heavy monorepo / long build / mobile workflow (negative control)

### User story
A team wants the system to clone a very large monorepo, run multi-hour build/test chains, or perform mobile/native toolchain work.

### Desired outcome
The product responds honestly:
- this may exceed the default runtime envelope
- use a heavier validation or execution backend
- or treat this as a later execution-tier expansion

### Why this scenario exists
This scenario prevents us from claiming that AgentCore is already a universal heavy sandbox.
AgentCore Runtime has hard limits around image/package size, per-session compute, synchronous timeouts,
and async job duration.

### v1 decision
Out of core scope. Support as:
- explicit non-goal
- future pluggable execution backend
- documented escalation path

---

## 5. Simulation summary

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

## 6. Scope freeze recommendation

## v1
GitHub-first enterprise deployment foundation for Claude Code on Bedrock:
- enterprise auth and attribution
- GitHub-native task ingress
- background task lifecycle
- PR draft / review / answer-only workflows
- optional read-only internal tools
- narrow approval-gated mutation tools
- observability and audit

## v1.5
- reusable Slack adapter
- richer task UI / status surfaces
- broader internal tool catalog

## v2
- pluggable agent adapters
- broader workflow surfaces
- heavier execution backends
- richer approval and policy composition

---

## 7. Source appendix

### Official / primary sources used
- AWS guidance repo: `guidance-for-claude-code-with-amazon-bedrock`
- AWS guidance architecture, deployment, quick start, monitoring docs
- Anthropic `claude-code-action` README
- Claude Code GitHub Actions docs
- Amazon Bedrock AgentCore Runtime docs
- Amazon Bedrock AgentCore quotas docs
- Amazon Bedrock AgentCore persistent filesystem docs (Preview)
- Amazon Bedrock AgentCore Gateway auth-code-flow blog
- Amazon Bedrock AgentCore Slack integration blog
- Amazon Bedrock AgentCore policy limitations docs
