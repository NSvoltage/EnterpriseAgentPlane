# Codex Build Brief

Use this brief as the top-level instruction set for implementation work.

## Product target
Extend the current Claude Code on Bedrock guidance repo into a **GitHub-first enterprise deployment foundation**
for Claude Code on Bedrock.

## Non-negotiable constraints
- Preserve the existing auth/federation/monitoring foundation
- Do not claim universal heavy sandbox support
- Do not make Slack a first-class v1 product surface
- Do not center the product narrative on MCP
- Keep repo changes reviewable in small PRs

## v1 scope
- enterprise auth + attribution
- GitHub ingress
- background task state contract
- answer-only, PR-draft, and review workflows
- Enterprise Tool Gateway abstraction
- audit + observability extensions

## v1 non-goals
- Teams/Jira/ServiceNow first-class adapters
- universal heavy execution backend
- fully dynamic mutation-capable enterprise tool marketplace
- persistent session storage as a hard dependency

## Suggested Codex prompt template
You are modifying the `guidance-for-claude-code-with-amazon-bedrock` repo.

Your task is to implement **[PR NAME]** from the build plan.

Constraints:
1. Preserve all existing auth/federation/monitoring flows unless explicitly changed.
2. Keep changes small and reviewable.
3. Add or update docs first where the interface or product story changes.
4. Prefer interface definitions and scaffolding over speculative full implementations.
5. Do not introduce claims in README/docs that exceed what is implemented.
6. Use “Enterprise Tool Gateway” terminology instead of centering “MCP”.
7. Keep GitHub as the primary workflow surface in v1.

Deliver:
- modified files
- concise rationale
- follow-up TODOs
- test or validation notes if applicable

## First three Codex tasks to run

### Task 1
Rewrite README and add ROADMAP.md + SECURITY_BOUNDARIES.md to reflect the new v1 scope.

### Task 2
Add scenario docs, ADRs, and TASK_LIFECYCLE.md.

### Task 3
Create `source/taskplane/` with:
- `models.py`
- `api.py`
- `github_adapter.py`
- `tool_gateway.py`
- `validation.py`
as stubs with docstrings and data models only.

## Review checklist
- Is the repo still truthful?
- Is GitHub clearly the primary v1 workflow?
- Is AgentCore treated as control plane/light-medium runtime rather than universal sandbox?
- Is MCP positioned as support under an Enterprise Tool Gateway abstraction?
- Are out-of-scope items clearly marked?
