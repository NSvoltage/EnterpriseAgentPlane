# Architecture Decision Records — v1 Design Choices

This document captures the key architectural decisions made during design. These are **not** up for debate during implementation — they guide all PR reviews.

## ADR-001 — Use the Current AWS Guidance Repo as the Foundation

**Status:** Accepted  
**Date:** 2026-04-08

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
- Better alignment with AWS's current right-to-win (identity, governance, audit, rollout)
- Less risk of overscoping into a universal harness too early

---

## ADR-002 — GitHub Is the Primary v1 Workflow Surface

**Status:** Accepted  
**Date:** 2026-04-08

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

## ADR-003 — AgentCore Is the Control Plane and Light/Medium Runtime, Not the Universal Heavy Sandbox

**Status:** Accepted  
**Date:** 2026-04-08

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

## ADR-004 — Model "Hardened MCP" as an Enterprise Tool Gateway Capability

**Status:** Accepted  
**Date:** 2026-04-08

### Context
Customers do not actually need "MCP" as the product. They need safe, governed access to internal tools and systems.
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

## ADR-005 — Persistent Session Storage Is Optional in v1

**Status:** Accepted  
**Date:** 2026-04-08

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

## ADR-006 — Slack Is a Reference Adapter, Not a v1 Product Pillar

**Status:** Accepted  
**Date:** 2026-04-08

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

---

## ADR-007 — Task Lifecycle Is Explicit and Separate from Execution

**Status:** Accepted  
**Date:** 2026-04-08

### Context
Earlier designs conflated "what the task is" with "how we execute it." This creates tight coupling to AgentCore and makes it hard to plug in different execution backends.

### Decision
Define task lifecycle (state machine, artifacts, lineage) as a separate abstraction layer.
Task execution (Claude Code on Bedrock, validation, tool invocation) plugs into this abstraction.

### Consequences
- Clear contracts between orchestration and execution
- Future execution backends (CodeBuild, custom) fit naturally
- Easier to test task logic independently of Claude Code
- Observability is consistent across execution types

---

## ADR-008 — GitHub Adapter Is a Thin Translation Layer, Not a Workflow Engine

**Status:** Accepted  
**Date:** 2026-04-08

### Context
The GitHub adapter's job is to convert GitHub events to task requests and results back to GitHub. It should not contain workflow logic (that's in task definitions and the execution layer).

### Decision
GitHub adapter responsibilities:
- Verify webhook signature
- Normalize GitHub event → TaskRequest
- Parse intent (@claude <command>)
- Validate repo is enabled
- Post results back to GitHub

GitHub adapter does NOT:
- Decide whether to run a task (TaskManager decides)
- Execute code (task execution layer does)
- Implement approval workflows (tool gateway and approval system do)

### Consequences
- Adapter is small and reviewable
- Workflows can be triggered from other surfaces (CLI, Slack, etc.) without duplicating logic
- Testing is focused (mock GitHub events → verify TaskRequest shape)

---

## ADR-009 — Tool Connectors Are Pluggable, with MCP as One Example

**Status:** Accepted  
**Date:** 2026-04-08

### Context
We don't know what all the tools are yet. Some will be MCP servers, some will be REST APIs, some will be internal Lambda functions.

### Decision
Define a tool connector interface:
```python
class ToolConnector(ABC):
    async def invoke(self, request: ToolInvocationRequest) -> ToolInvocationResult
    async def get_schema(self) -> dict
```

MCP, REST, Lambda, etc. are all implementations of this interface.
Tool registry doesn't care about the underlying connector type.

### Consequences
- Tool library is not locked to MCP
- Can add new connector types without changing core system
- Tool selection and invocation are decoupled from connector details

---

## ADR-010 — Validation Is an Interface, Not a Product Feature

**Status:** Accepted  
**Date:** 2026-04-08

### Context
We need deterministic verification of generated code, but we don't know yet what the best backend is. CodeBuild is one option, but there are others.

### Decision
Define a validation interface:
```python
class ValidationBackend(ABC):
    async def validate(self, request: ValidationRequest) -> ValidationResult
```

Implementations can be CodeBuild, AgentCore light containers, local, custom, etc.
Task execution calls the validation interface, not specific backends.

### Consequences
- v1 can use a simple backend (e.g., AgentCore or local)
- CodeBuild is an optional/reference implementation, not required
- Future heavy backends fit naturally
- Customers can bring their own validation if needed

---

## ADR-011 — Approval Is Checked at Tool Gateway, Not Scattered Everywhere

**Status:** Accepted  
**Date:** 2026-04-08

### Context
Scenarios S5 require approval gates. These could be implemented in many places, leading to inconsistent authorization.

### Decision
All approval logic lives in the tool gateway.
Before a tool is invoked:
- Check: is this tool mutation-capable?
- Check: does it require approval?
- If yes: route to approval system (GitHub, admin portal, whatever)
- Wait for approval
- Only then invoke

### Consequences
- Consistent approval semantics
- Easy to audit (all approvals flow through one place)
- Easy to change approval routing (all tools see the new routing)

---

## Review Criteria (Using These ADRs)

When reviewing PRs, check:

1. **Does the code follow ADR-001?** — Foundation layer is preserved?
2. **Does the code follow ADR-002?** — GitHub is the primary surface?
3. **Does the code follow ADR-003?** — AgentCore is not positioned as universal sandbox?
4. **Does the code follow ADR-004?** — Tool Gateway is the product abstraction, not MCP?
5. **Does the code follow ADR-005?** — Session storage is optional?
6. **Does the code follow ADR-006?** — Slack is not claimed as v1 pillar?
7. **Does the code follow ADR-007?** — Task lifecycle is separate from execution?
8. **Does the code follow ADR-008?** — GitHub adapter is thin?
9. **Does the code follow ADR-009?** — Tool connectors are pluggable?
10. **Does the code follow ADR-010?** — Validation is an interface?
11. **Does the code follow ADR-011?** — Approvals are centralized?

If the answer to any is "no," the PR should not be merged.

---

**Document version:** 1.0  
**Last updated:** 2026-04-08  
**Status:** Authoritative for v1 implementation
