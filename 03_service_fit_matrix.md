# Service Fit Matrix — What Fits Now vs Later

This section is the hostile diligence layer: map customer requirements to real AWS assets and call out
where the fit is strong, partial, or not yet appropriate to center in the v1 story.

## Legend
- **Green** — safe to position for v1
- **Yellow** — usable with caveats, reference pattern, or limited scope
- **Red** — do not center in v1

| Area | Candidate AWS / adjacent asset | Fit | What it supports well | Hard reality / caveat | Positioning decision |
|---|---|---|---|---|---|
| Enterprise auth | Current guidance repo + IAM OIDC / Cognito | Green | SSO, temporary creds, Bedrock access control, user attribution | Current flow is native-app / local-machine oriented today | Keep as foundation |
| Bedrock invocation governance | Current guidance repo | Green | Region scoping, model invocation controls, attribution in CloudTrail | Primarily focused on Claude Code local/CLI use today | Keep as foundation |
| Monitoring | Current OTEL + ALB + ECS Fargate + CloudWatch stack | Green | Usage, token, cost, user attribute visibility | Need to extend with task-level workflow metrics | Extend in v1 |
| GitHub workflow entry | Claude Code Action / GitHub App patterns | Green | PR/issues/comments driven activation, Bedrock auth supported | Requires integration and repo policy work | Primary v1 ingress |
| Background task control plane | AgentCore Runtime | Green | Async jobs, isolated sessions, strong control-plane fit | Need to build task service; respect runtime limits | Core v1 build |
| Session isolation | AgentCore Runtime sessions | Green | Strong per-session isolation for multi-user workflows | Backend must manage session↔user/task mapping | Core v1 build |
| Persistent coding workspace | AgentCore session storage | Yellow | Resume coding work; keep files/build artifacts between stops | Preview; resets after inactivity/version update; not a hard dependency | Optional / feature-flag |
| Enterprise tool access | AgentCore Gateway | Yellow | Central auth/policy/observability layer for tools and MCP targets | Needs careful connector curation and policy design | Build as abstraction |
| MCP support | AgentCore Gateway MCP targets | Yellow | Good target type for curated tools | Product should not become “MCP server platform” | Support, not center |
| Fine-grained policy | AgentCore Policy / Cedar | Yellow | Useful for contextual/tool-input controls | Current limitations; do not oversell principal-level granularity | Limited v1 |
| Private connectivity | AgentCore VPC + PrivateLink | Yellow | Needed for stricter customers | Advanced deployment path; subnet/AZ/networking constraints | Advanced mode docs |
| Slack ingress | Slack integration pattern with Lambda | Yellow | Reusable integration layer, useful later | Reference pattern, not strong enough as primary v1 product surface | v1.5 / sample |
| Heavy validation backend | CodeBuild | Yellow | Deterministic build/test/lint backend | Reserved fleets cost money while provisioned; cache visibility within same account is a real concern | Use as optional validation backend |
| Universal heavy sandbox | AgentCore alone | Red | N/A | Hard limits on package/image size, compute, timeouts | Do not claim |
| Teams/Jira/ServiceNow first-class surfaces | Custom future adapters | Red | N/A in current validated scope | Not validated strongly enough for v1 | Defer |

---

## Fit details that matter to the build

### 1. Keep the current repo as the foundation
The current AWS guidance repo already gives you:
- enterprise identity integration
- temporary credentials
- scoped Bedrock access
- user attribution through session tags
- packaging for local rollout
- optional monitoring

That is not something to replace. It is the foundation to extend.

### 2. GitHub is the cleanest wedge
GitHub is the best place to start because:
- developers already work there
- Claude Code Action already supports GitHub PR/issues/comments
- Bedrock is already a supported auth path
- the workflow artifacts (issues, comments, branches, PRs) are inherently auditable

### 3. AgentCore is best treated as the control plane + light/medium execution path
Use it for:
- task orchestration
- isolated sessions
- async workflows
- some coding tasks
- read-only / governed tool lookups

Do **not** treat it as the universal answer for:
- giant monorepos
- multi-hour native/mobile builds
- every heavy toolchain

### 4. MCP should be hidden behind an Enterprise Tool Gateway concept
The product outcome customers want is:
- approved tools
- centralized auth
- policy
- audit

Some of those tools may be reached through MCP. That is support for a target type, not the center of the product.

---

## Recommended fit-based scope

### v1
- Foundation repo preserved
- GitHub-first ingress
- Task lifecycle / background execution
- PR draft + answer-only + review workflows
- Optional curated read-only tools
- Narrow, approval-gated mutation tools
- Extended observability

### v1.5
- Slack reference adapter
- More curated enterprise tools
- Better admin UX

### v2
- Pluggable agents
- Heavier execution backends
- Broader enterprise workflow surfaces

---

## Source appendix

- AWS guidance repo architecture / deployment / monitoring / quick start docs
- Anthropic Claude Code Action README and GitHub Actions docs
- Amazon Bedrock AgentCore Runtime docs (sessions, how it works, quotas)
- Amazon Bedrock AgentCore persistent filesystem docs (Preview)
- Amazon Bedrock AgentCore Gateway auth-code-flow blog
- Amazon Bedrock AgentCore policy limitations docs
- Amazon Bedrock AgentCore VPC docs
- AWS Slack integration blog
- AWS CodeBuild reserved capacity / create-project docs
