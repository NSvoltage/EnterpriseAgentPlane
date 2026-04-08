# Roadmap — Claude Code on Bedrock GitHub-First Enterprise

## Release Timeline

### v1.0 — GitHub-First Foundation (Q2 2026)

**Release goal:** Secure, auditable GitHub-driven coding agent workflows with enterprise identity and governed tool access.

#### Core Features

**A. Enterprise Identity & GitHub Integration**
- [x] Preserve AWS foundation (OIDC, temporary creds, Bedrock scoping)
- [ ] GitHub webhook ingress
- [ ] Issue/PR/comment event normalization
- [ ] User identity mapping (GitHub → AWS)
- [ ] Repo enable/disable controls

**B. Background Task Lifecycle**
- [ ] Task model (state machine, artifacts, lineage)
- [ ] Task manager interface (create, read, update, cancel, retry)
- [ ] AgentCore Runtime integration
- [ ] Session isolation per task/user
- [ ] Task status tracking in GitHub

**C. Answer-Only Workflows (S1)**
- [ ] "Explain this code/error" use case
- [ ] File/log analysis
- [ ] Result posted as GitHub comment
- [ ] No repo mutations

**D. PR Draft Generation (S2)**
- [ ] "Fix this bug and open a PR" use case
- [ ] Branch creation
- [ ] Code generation via Claude Code on Bedrock
- [ ] PR draft creation with summary
- [ ] Validation hooks (linting, tests)

**E. PR Review & Triage (S3)**
- [ ] Automated review comments on PRs
- [ ] Regression risk analysis
- [ ] Missing test detection
- [ ] Review comment posting

**F. Enterprise Tool Gateway**
- [ ] Tool registry abstraction
- [ ] Authorization enforcement
- [ ] Read-only tool access (curated set)
- [ ] Approval-gated mutations (narrow set)
- [ ] MCP as one connector type

**G. Validation Interface**
- [ ] Pluggable validation backends
- [ ] CodeBuild as reference backend (optional)
- [ ] Lint/test/security checks
- [ ] Deterministic result reporting

**H. Observability & Audit**
- [ ] Task-level metrics (OTEL extension)
- [ ] Tool invocation audit trail
- [ ] CloudWatch dashboards
- [ ] Task completion analytics
- [ ] User/repo/team dimensions

#### Scenarios Enabled

| Scenario | S1 | S2 | S3 | S4 | S5 | S6 |
|----------|----|----|----|----|----|----|
| Explain-only | ✓ | | | | | |
| PR draft | | ✓ | | | | |
| PR review | | | ✓ | | | |
| Tool lookup (read-only) | | | | ✓ | | |
| Tool mutation (gated) | | | | | ~ | |
| Heavy monorepo | | | | | | ✗ |

✓ = Fully supported | ~ = Limited/gated | ✗ = Not supported

#### Success Criteria

- [ ] GitHub event → task → result flow is end-to-end tested
- [ ] Scenario S1 works in reference deployment
- [ ] Scenario S2 works with deterministic validation
- [ ] Audit trail is complete (CloudTrail + task telemetry)
- [ ] Repo documentation is honest and non-overclaimed
- [ ] All out-of-scope items are explicitly marked (S6, Slack, Jira, etc.)

#### Effort Estimate

8 PRs over 8-12 weeks:
1. **Positioning & docs** (1-2 weeks) — README, ROADMAP, SECURITY_BOUNDARIES
2. **Design contracts** (1 week) — Scenarios, requirements, ADRs
3. **Task model** (1-2 weeks) — State machine, artifacts, lifecycle
4. **GitHub adapter** (1-2 weeks) — Event normalization, task routing
5. **Tool gateway** (1-2 weeks) — Registry, authorization, connectors
6. **Validation interface** (1 week) — Pluggable backends, result schema
7. **Observability** (1 week) — Metrics, dashboards, audit events
8. **End-to-end sample** (1-2 weeks) — S1 scenario, Lambda integration, docs

---

### v1.5 — Workflow & Tool Expansion (Q3-Q4 2026)

**Release goal:** Broader workflow surfaces and curated enterprise tool library.

#### New Features

**A. Slack Reference Adapter**
- [ ] Slack bot integration pattern
- [ ] Event normalization (Slack → task)
- [ ] Status/result posting back to Slack
- [ ] Documentation for custom deployment

**B. Extended Tool Library**
- [ ] Common enterprise tools (deployment status, incident management, service catalogs)
- [ ] Tool onboarding templates
- [ ] Tool schema versioning
- [ ] Policy composition examples

**C. Admin & Observability UI**
- [ ] Web dashboard for task monitoring
- [ ] Tool access audit viewer
- [ ] Policy configuration UI
- [ ] Cost and usage analytics

**D. Repo Sensitivity Tiers**
- [ ] Preset policies for "public" / "internal" / "restricted" repos
- [ ] Automatic tool filtering by repo tier
- [ ] Audit log retention policies by tier

#### Effort Estimate

4-6 PRs over 12-16 weeks

---

### v2 — Extensibility & Heavy Backends (2027)

**Release goal:** Pluggable agent adapters, broader enterprise surfaces, heavier execution backends.

#### Major Changes

**A. Pluggable Agent Adapters**
- [ ] Contract for different agent types (not just Claude Code)
- [ ] Provider interface for agent selection
- [ ] Model/provider switching

**B. Broader Workflow Surfaces**
- [ ] Teams integration (first-class)
- [ ] Jira / ServiceNow adapters
- [ ] Internal chat platforms
- [ ] Email-driven workflows

**C. Heavier Execution Backends**
- [ ] CodeBuild integration (reserved capacity)
- [ ] Custom container runners
- [ ] Support for long-running builds (4h+, 8h+ limits)
- [ ] Large monorepo workflows
- [ ] Mobile / native toolchain support

**D. Persistent Session Features**
- [ ] Session storage as core feature (no longer optional)
- [ ] Multi-step coding workflows
- [ ] Session resumption across boundaries
- [ ] Artifact caching and state

**E. Advanced Policy & Governance**
- [ ] Dynamic policy composition (Cedar-like)
- [ ] Principal-level fine-grained auth
- [ ] Conditional approval gates
- [ ] Cost allocation and quota enforcement

#### Effort Estimate

6-8 months of sustained development

---

## Non-Goals (Will Not Ship)

### In v1, v1.5, or v2

- **Universal AI SDLC platform** — We build for code assistants on Bedrock, not a generic AI control plane
- **One-click SaaS product** — This is a deployment foundation, not a managed service
- **Hardened MCP marketplace** — MCP is a protocol; we build governance abstractions, not a marketplace
- **Zero-configuration enterprise adoption** — Customers will need to curate tools, set policies, and tune their deployment

## Deployment Targets

| Platform | v1 | v1.5 | v2 |
|----------|----|----|-----|
| AWS Lambda (GitHub webhooks) | ✓ | ✓ | ✓ |
| AWS ECS Fargate (long-running task orchestration) | ✓ | ✓ | ✓ |
| AWS CodeBuild (validation backend) | ~ (optional) | ✓ | ✓ |
| Private VPC deployment | ~ (advanced docs) | ✓ | ✓ |
| AWS GovCloud / China regions | ⧰ | ⧰ | ~ |

✓ = Supported | ~ = Partial/advanced | ⧰ = Future consideration

## Breaking Changes

### v1 to v1.5
None expected (additive features only).

### v1.5 to v2
Possible structural changes:
- AgentCore session storage may become required (lifting from optional flag)
- Policy model may change to support fine-grained auth
- Workflow surface abstraction may be refactored

These will be detailed in v2 RFD.

## Feedback & Issues

- **Report bugs** — GitHub issues on this repo
- **Request features** — Check [REQUIREMENTS.csv](./assets/docs/design/REQUIREMENTS.csv) first
- **Suggest architecture changes** — Open an RFD (Request for Discussion)

## Support Timeline

| Version | Status | Support Until |
|---------|--------|-----------------|
| v1.0 | In Development | 2027-04-01 |
| v1.x | Maintenance (v1.5 available) | 2027-10-01 |
| v2.0 | Not yet released | TBD |

---

**Last updated:** 2026-04-08  
**Prepared by:** Principal Engineer team
