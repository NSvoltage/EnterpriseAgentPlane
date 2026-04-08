# Architecture Decision Records (ADRs)

## ADR-001 — Use the current AWS guidance repo as the foundation rather than starting from Open SWE

### Status
Accepted

### Context
The current AWS guidance repo already provides secure enterprise authentication for Claude Code on Bedrock,
including identity-provider integration, temporary credentials, scoped Bedrock access, user attribution, packaging,
and optional monitoring.

Open SWE is valuable as a reference architecture for internal async coding agents, but its purpose is to be forked
and customized by teams that want to own more of the harness/sandbox/workflow surface area.

### Decision
Extend the current guidance repo instead of starting from Open SWE.

### Consequences
- Faster path to something enterprise-safe and buildable
- Better alignment with AWS’s current right-to-win (identity, governance, audit, rollout)
- Less risk of overscoping into a universal harness too early

---

## ADR-002 — GitHub is the primary v1 workflow surface

### Status
Accepted

### Context
Claude Code Action already supports GitHub PRs and issues, including `@claude` mentions, issue assignments,
and Bedrock authentication. GitHub provides strong natural artifacts: issue, comment, branch, PR, review.

### Decision
Make GitHub the primary v1 ingress surface.

### Consequences
- Stronger and safer v1 claim
- Clear user workflows
- Simpler audit and artifact model
- Slack and other surfaces move to later phases

---

## ADR-003 — AgentCore is the control plane and light/medium runtime, not the universal heavy sandbox

### Status
Accepted

### Context
AgentCore Runtime is strong for async jobs, session isolation, and agent hosting. But it has hard limits around
image/package size, per-session compute, sync timeout, and async job duration.

### Decision
Use AgentCore for:
- task orchestration
- isolated sessions
- light/medium execution
- governed tool access workflows

Do not make v1 depend on AgentCore as a universal heavy sandbox.

### Consequences
- Honest product scope
- Easier v1 success
- Leaves room for pluggable heavier execution backends later

---

## ADR-004 — Model “hardened MCP” as an Enterprise Tool Gateway capability

### Status
Accepted

### Context
Customers do not actually need “MCP” as the product. They need safe, governed access to internal tools and systems.
AgentCore Gateway already provides a centralized layer for auth, observability, and policy enforcement for tools and MCP targets.

### Decision
Define an **Enterprise Tool Gateway** abstraction that:
- supports MCP targets
- supports non-MCP internal APIs
- centralizes auth, policy, and audit
- distinguishes read-only vs mutation-capable tools

### Consequences
- Keeps the product customer-outcome focused
- Avoids protocol-led overscoping
- Leaves room for multiple connector types

---

## ADR-005 — Persistent session storage is optional in v1

### Status
Accepted

### Context
AgentCore session storage is useful for coding workflows, but it is in Preview and should not become a hard dependency.

### Decision
Treat persistent session storage as:
- optional
- behind a feature flag
- not required for the first v1 workflows

### Consequences
- Reduces platform risk
- Makes v1 shippable sooner
- Keeps the repo honest about preview dependencies

---

## ADR-006 — Slack is a reference adapter, not a v1 product pillar

### Status
Accepted

### Context
AWS has a reusable Slack integration pattern, but the strongest validated enterprise coding workflow today is GitHub-first.

### Decision
Defer Slack to:
- sample / reference implementation
- later phase
- not part of the core external v1 claim

### Consequences
- Lower v1 product risk
- Simpler first build
- Stronger truthfulness in positioning
