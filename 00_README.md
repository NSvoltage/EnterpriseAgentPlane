# Enterprise Coding Agent Deployment Foundation — Working-Backwards Build Pack

This pack is designed to help you **scope, validate, spec, and build** the next evolution of the
`guidance-for-claude-code-with-amazon-bedrock` repo using Codex.

## What this pack contains

1. `01_scenario_pack.md` — customer-first scenario contracts and simulation notes
2. `02_requirements_matrix.csv` — build-oriented requirement matrix
3. `03_service_fit_matrix.md` — what AWS assets fit now, what is partial, what is future work
4. `04_adrs.md` — architecture decision records for the most important scope calls
5. `05_repo_evolution_and_pr_plan.md` — how to evolve the current repo into a credible v1
6. `06_codex_build_brief.md` — concise build brief and PR sequence you can hand to Codex

## Recommended build thesis

Build **GitHub-first** and **Claude-first**.

Use the current AWS guidance repo as the **foundation** for:
- enterprise identity/federation
- Bedrock access control
- user attribution
- monitoring and audit

Add a new layer for:
- GitHub-native task ingress
- background task lifecycle
- governed internal tool access
- task-level artifacts and status

Do **not** make v1 depend on:
- Slack/Teams as first-class production surfaces
- universal heavy coding sandboxes
- persistent session storage as a hard requirement
- “hardened MCP servers” as the center of the product

## Core build artifact to target

**Claude Code on Bedrock — Enterprise Deployment Foundation (v1)**

A GitHub-first deployment pattern that extends the current guidance repo with:
- secure enterprise auth and attribution
- GitHub issue / PR / comment driven workflows
- background task orchestration
- optional governed internal-tool access
- auditability and observability

## Primary source set used

- AWS guidance repo for Claude Code on Bedrock
- Anthropic Claude Code Action / GitHub Actions docs
- Amazon Bedrock AgentCore Runtime docs
- Amazon Bedrock AgentCore Gateway docs
- Amazon Bedrock AgentCore policy limitations docs
- Amazon Bedrock AgentCore VPC docs
- AWS Slack integration blog
- AWS CodeBuild fleet docs

The downstream docs include a source appendix where relevant.
