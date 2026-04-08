# Claude Code on Bedrock — GitHub-First Enterprise Deployment Foundation

A production-grade, **GitHub-first** deployment pattern for Claude Code on Amazon Bedrock with enterprise identity integration, background task orchestration, and governed access to internal tools.

## What This Is

This repository extends the AWS guidance for secure Claude Code on Bedrock with a new **workflow + task layer** that enables:

- **GitHub-native task ingress** — Issues, PRs, comments, assignments trigger coding tasks
- **Background task lifecycle** — Async execution, status tracking, cancellation, retry
- **Enterprise tool governance** — Centralized auth, policy, and audit for internal tool access
- **Audit and observability** — Complete trace of who invoked what, with what intent, and what happened

**Built on a proven foundation:**
- Enterprise identity (SSO/OIDC federation with temporary credentials)
- Bedrock access control and scoped model invocation
- Per-user attribution and CloudTrail integration
- Monitoring infrastructure (OpenTelemetry + CloudWatch)
- Multi-platform distribution (macOS, Linux, Windows)

## What This Is Not (v1)

Explicitly out of v1 scope:

- ❌ **Heavy monorepo / long build workflows** — AgentCore has hard limits on compute, timeouts, and package size. Use heavier backends (CodeBuild, custom runners) for those workloads.
- ❌ **Slack/Teams/Jira/ServiceNow as first-class surfaces** — GitHub is the primary v1 ingress. Other workflow surfaces come in v1.5+.
- ❌ **Persistent coding sessions as a hard requirement** — AgentCore session storage is in preview. We don't depend on it for v1 core workflows.
- ❌ **"Hardened MCP server platform"** — MCP is one connector type within an Enterprise Tool Gateway. The product is "approved tools with central auth/audit," not a protocol.
- ❌ **Universal enterprise policy engine** — AgentCore policy has known limits. We support curated tool sets with approval gates, not dynamic principal-level fine-grained auth in v1.

## v1 Scope — GitHub-First Workflows

### Scenario S1: Answer-Only (Low-Risk Wedge)
```
@claude explain why service X fails with config Y
→ Task created, repo analyzed
→ Explanation posted in GitHub
→ No code mutations, no external calls
```

### Scenario S2: PR Draft Generation (Core Value)
```
@claude fix the null handling in validation and open a PR
→ Task created, code analyzed
→ PR draft branch created
→ PR opened with validation report
→ Ready for code review
```

### Scenario S3: PR Review & Triage (High-Value, Low-Risk)
```
@claude review this PR for regression risk
→ Analysis posted as review comment
→ No code mutations
→ Audit trail of files accessed
```

### Scenario S4: Read-Only Tool Lookup (Governed Access)
```
@claude what's the deploy status of service-a in staging?
→ Query approved tool with policy enforcement
→ Result posted in GitHub
→ Tool access is logged and auditable
```

### Scenario S5: Guarded Mutation (Narrow & Approval-Gated)
```
@claude rerun the deploy check (user has approval policy)
→ Approval is verified
→ Tool mutation is executed with governance
→ Outcome is logged and attributed
```

**Out of core v1:** Heavy monorepo builds, multi-hour CI/CD chains, mobile native toolchains.

## Architecture — Layered Design

```
┌─────────────────────────────────────────────────┐
│  Workflow Layer (v1 new)                        │
│  ├─ GitHub adapter (event → task)               │
│  ├─ Task lifecycle (state machine, artifacts)   │
│  ├─ Enterprise Tool Gateway (auth + policy)     │
│  └─ Validation interface (pluggable backends)   │
├─────────────────────────────────────────────────┤
│  Execution Layer (AgentCore Runtime)            │
│  ├─ Session isolation                           │
│  ├─ Async job orchestration                     │
│  ├─ Light/medium compute (~8h max, 15m sync)    │
│  └─ Optional persistent storage (feature flag)  │
├─────────────────────────────────────────────────┤
│  Foundation Layer (Existing AWS guidance repo)  │
│  ├─ Enterprise identity (OIDC federation)       │
│  ├─ Temporary credentials                       │
│  ├─ Bedrock access control                      │
│  ├─ User attribution + CloudTrail               │
│  ├─ Monitoring (OTEL + CloudWatch)              │
│  └─ Distribution (cross-platform binaries)      │
└─────────────────────────────────────────────────┘
```

## Security Boundaries

**What is protected by design:**
- User identity and attribution (OIDC → temporary AWS credentials)
- Bedrock access scoped by region and model
- Repo access controlled by GitHub permissions
- Tool invocation gated by approval policies
- All actions logged to CloudTrail

**What is not protected:**
- AgentCore Runtime itself is AWS-managed (not in scope)
- MCP connector security depends on target tool implementation
- Heavy monorepo scenarios require different infrastructure

**Threat model:** See [SECURITY_BOUNDARIES.md](./assets/docs/SECURITY_BOUNDARIES.md)

## Roadmap

### v1 (Current)
- Enterprise identity + GitHub ingress
- Background task orchestration
- Answer-only, PR-draft, review workflows
- Read-only tool access (curated)
- Narrow approval-gated mutations
- Audit and observability

### v1.5 (Next)
- Slack reference adapter
- More curated enterprise tools
- Richer task UI and status surfaces
- Admin dashboard enhancements

### v2 (Future)
- Pluggable agent adapters
- Broader workflow surfaces (Teams, Jira, etc.)
- Heavier execution backends (CodeBuild, custom)
- Richer approval and policy composition
- Persistent session storage as core feature

## Getting Started

### Prerequisites
- Python 3.10+
- AWS account with Bedrock access
- GitHub organization/repo for testing

### Development Setup
```bash
# Clone this repo
git clone https://github.com/your-org/guidance-for-claude-code-with-amazon-bedrock
cd guidance-for-claude-code-with-amazon-bedrock

# Install dependencies
poetry install

# Existing AWS guidance repo setup (unchanged)
poetry run ccwb init      # Configure OIDC + AWS
poetry run ccwb deploy    # Provision infrastructure

# New: Deploy task layer (coming in later PRs)
# poetry run ccwb task-gateway setup
```

### Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE_V1.md](./assets/docs/ARCHITECTURE_V1.md) | Detailed architecture and design |
| [SCENARIOS.md](./assets/docs/design/SCENARIOS.md) | Complete scenario contracts |
| [SECURITY_BOUNDARIES.md](./assets/docs/SECURITY_BOUNDARIES.md) | Threat model and security scope |
| [GITHUB_WORKFLOWS.md](./assets/docs/GITHUB_WORKFLOWS.md) | GitHub event → task flow |
| [TASK_LIFECYCLE.md](./assets/docs/TASK_LIFECYCLE.md) | Task state machine and artifact model |
| [TOOL_GATEWAY.md](./assets/docs/TOOL_GATEWAY.md) | Enterprise tool access and governance |
| [VALIDATION.md](./assets/docs/VALIDATION.md) | Validation interface and backends |
| [ROADMAP.md](./ROADMAP.md) | Feature roadmap and timeline |

## Contributing

This repo uses a working-backwards approach: design contracts first, implementation second.

1. **Understand the scenario** — Read [SCENARIOS.md](./assets/docs/design/SCENARIOS.md)
2. **Check the requirements** — See [REQUIREMENTS.csv](./assets/docs/design/REQUIREMENTS.csv)
3. **Review the architecture decision** — Check [ARCHITECTURE_DECISIONS.md](./assets/docs/design/ARCHITECTURE_DECISIONS.md)
4. **Make your change** — Keep PRs small and focused
5. **Reference the contract** — Your PR should implement a specific documented interface

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## Status

**v1 Development:** In progress
- ✓ Design contracts and scenarios (complete)
- ✓ Architecture decisions (complete)
- ⧰ Task lifecycle model (PR 3)
- ⧰ GitHub adapter (PR 4)
- ⧰ Tool gateway (PR 5)
- ⧰ Validation interface (PR 6)
- ⧰ Observability (PR 7)
- ⧰ End-to-end sample (PR 8)

## License

MIT (same as AWS guidance repo foundation)

## Support

For questions about:
- **AWS guidance repo foundation** → See upstream [aws-samples/guidance-for-claude-code-with-amazon-bedrock](https://github.com/aws-samples/guidance-for-claude-code-with-amazon-bedrock)
- **GitHub workflows in this v1 extension** → See [GITHUB_WORKFLOWS.md](./assets/docs/GITHUB_WORKFLOWS.md)
- **Task lifecycle and governance** → See [TASK_LIFECYCLE.md](./assets/docs/TASK_LIFECYCLE.md)

---

**Built by:** Principal Engineer team  
**Last updated:** 2026-04-08
