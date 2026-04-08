# Architecture — Collaborative Cloud Agent Runtime v1

A detailed explanation of how the surface-agnostic collaborative agent runtime works.

---

## Surface-Agnostic Design

The architecture is **intentionally surface-agnostic**. Any workflow surface can create Tasks.

### Adapter Pattern

Each surface implements a thin **Event Normalizer** that converts surface-specific events into TaskRequest:

```
GitHub Webhook          → GitHubEventNormalizer    → TaskRequest → Task
Slack Event            → SlackEventNormalizer     → TaskRequest → Task
Web POST               → APIRequestNormalizer     → TaskRequest → Task
Cron Trigger           → CronEventNormalizer      → TaskRequest → Task
CLI Invocation         → CLIArgumentNormalizer    → TaskRequest → Task
```

**All end up at the same place: TaskManager.create_task(request)**

### Why Surface-Agnostic?

**Problem:** Enterprise teams use multiple workflow surfaces. Building a different system for each creates:
- Duplicate work (state management, approval logic, audit trails)
- Inconsistent user experience (different UIs, different approval paths)
- Security gaps (different verification, different audit trails)

**Solution:** One durable Task model, multiple ingress adapters.

### Example: Multi-Surface Workflow

```python
# User starts in Slack
task = await slack_normalizer.normalize(slack_event)
task_id = await task_manager.create_task(task)
# Task created with source surface = "slack_thread"

# Task executes in AgentCore sandbox
await task_manager.update_task(task_id, TaskUpdate(state=TaskState.RUNNING))

# Agent generates PR as artifact
artifact = TaskArtifact(task_id=task_id, artifact_type=TaskArtifactType.GITHUB_PR, content_url=pr_url)

# Slack callback posts result back to original thread
await slack_callback.post_thread_update(task.trigger_id, f"PR ready: {pr_url}")

# User can also see same task in web UI
# Web UI shows task.id, task.state, task.artifacts, task.created_at, etc.
# All surfaces point to same Task record
```

### GitHub as v1 Example

GitHub is the **primary v1 surface** because:
1. Code-centric workflows (pull requests, reviews, commits)
2. Existing event stream (webhooks available)
3. Strong authentication (GitHub App OAuth)
4. Clear approval path (PR reviews)

But the architecture is **not GitHub-specific**. Slack, web, and automation are equally supported.

### Multi-Surface Sync (v1.5)

When a task is created from one surface, results flow back to **all interested surfaces**:

```
GitHub webhook creates task
    ↓
Task executes
    ↓
Result artifact created (e.g., code diff)
    ↓
GitHub callback posts comment ─────┐
Slack callback posts thread reply ─┼─ Same TaskResult
Web callback updates dashboard ───┘

User can:
- Review on GitHub PR
- Approve in Slack thread
- Monitor on web dashboard
- All interactions sync back to Task record
```

Design not yet implemented (v1.5 scope), but model supports it.

---

## System Overview

```
GitHub                AWS Account (Customer's)          AWS Bedrock (Managed)
────────              ──────────────────────           ──────────────────────

User Comments    →    [GitHub Webhook]
PR Assignment          └─→ [Lambda]                     
PR Open                    └─→ [Event Normalizer]
Mention @claude            └─→ [Task Manager]
                               ├─→ [Task DB / State]
                               ├─→ [GitHub Adapter]     →  [Claude Code]
                               │                        →  [AgentCore]
                               ├─→ [Tool Gateway]       
                               │   ├─→ [Authorization]  
                               │   └─→ [Tool Connector] →  [Internal Services]
                               │
                               ├─→ [Validation]        →  [CodeBuild / AgentCore]
                               │
                               ├─→ [Observability]     →  [CloudWatch]
                               │                       →  [CloudTrail]
                               │
                               └─→ [GitHub Callback]   →  Post Result to GitHub
                                   ├─→ Comment
                                   ├─→ PR Link
                                   └─→ Review
```

## Layered Architecture

### Layer 1: Foundation (Existing AWS Guidance Repo)

**Purpose:** Secure enterprise identity, credentials, Bedrock access control.

**Components:**
- **OIDC Provider** — Integrates with customer's IdP (Okta, Azure AD, Auth0, Cognito)
- **IAM Role** — Scoped permissions for Bedrock model invocation, region constraints
- **STS Credentials** — Short-lived (1h) temporary credentials issued per session
- **CloudTrail** — Audit log of all AWS API calls, user attribution
- **Monitoring** — OpenTelemetry → CloudWatch for usage, token consumption, cost

**Not changed in v1:** All foundation components remain intact and operational.

---

### Layer 2: Workflow + Task (v1 New)

**Purpose:** Convert GitHub events to tasks, manage lifecycle, report back.

#### 2.1 GitHub Ingress

**Components:**
- **GitHub Webhook** — Configured by customer in repo settings
  - Events: issue_comment, pull_request_review_comment, pull_request, issues
  - Signature verification (GitHub signs all webhooks)
  - Delivery to Lambda or HTTP endpoint

- **Event Normalizer** — Pydantic-validated parsing
  - Converts GitHub payload → GitHubTaskRequest
  - Extracts: user, repo, comment, branch, command intent
  - Validates: repo is enabled, user is authorized (GitHub permissions)

- **Intent Parser** — Detects command from comment
  - "@claude explain X" → answer_only workflow
  - "@claude fix X and open PR" → pr_draft workflow
  - "@claude review this" → review workflow
  - Structured parameter extraction

#### 2.2 Task Lifecycle Management

**Components:**
- **Task Model** — Pydantic dataclass
  ```python
  Task:
    id: UUID
    user_id: str (from GitHub)
    repo_id: str (full GitHub identifier)
    workflow_type: Literal["answer_only", "pr_draft", "review", "tool_lookup"]
    state: TaskState (queued → running → completed/failed/canceled)
    created_at, started_at, completed_at: datetime
    artifacts: List[TaskArtifact]
    approval_required: bool
    ...
  ```

- **Task Manager** — Interface for CRUD operations
  - `create_task(request)` → Task
  - `get_task(id)` → Task
  - `update_task(id, updates)` → Task
  - `cancel_task(id, reason)` → Task

- **State Machine** — Explicit transitions
  ```
  queued → running → waiting_for_approval → completed
                  ↓
                failed
                  ↓
              canceled
  ```

- **Task Storage** — Persistent (database or S3)
  - Must be queryable by task_id, repo_id, user_id
  - Must support state filtering
  - Artifacts are stored and linked

#### 2.3 GitHub Adapter

**Purpose:** Bridge task execution to GitHub events and results.

**Components:**
- **GitHub Event Handler** — Receives webhook, creates task
  ```
  GitHub Event
    → Verify Signature
    → Normalize to TaskRequest
    → Check Repo Enabled?
    → Create Task
    → Return 202 Accepted (webhook completes immediately)
    → Process async (task execution in background)
  ```

- **GitHub Status Callback** — Reports task result back
  ```
  Task Complete
    → Generate summary (status, artifacts, duration)
    → Post GitHub comment with results
    → Link to task ID (for audit)
    → Add PR link (if pr_draft workflow)
    → Add review comment (if review workflow)
  ```

- **Repo Enable/Disable** — Admin control
  ```
  Customer configures: "enable tasks for repos: [frontend, backend, infra]"
  Task creation checks: is repo in enabled list? If not, reject.
  ```

#### 2.4 Task Execution Flow

**Example: PR Draft Workflow (S2)**

```
1. User comments: "@claude fix the null handling in services/payment.ts and open a PR"

2. Event Normalizer
   - GitHub event → GitHubTaskRequest
   - Extract: command="fix", file="services/payment.ts", intent="pr_draft"

3. Task Manager
   - Create Task (state=queued, workflow_type=pr_draft)
   - Task stored in database

4. Execution Engine (async)
   - Set state → running
   - Emit telemetry: task.started

5. GitHub Adapter
   - Fetch repo context (file list, recent commits, open issues)
   - Prepare prompt for Claude

6. Claude Code Invocation (via AgentCore)
   - AgentCore session created
   - Prompt sent to Claude on Bedrock
   - Claude generates code patch
   - Session closed

7. Validation (if enabled)
   - Run lint/test checks on generated code
   - Store validation report as artifact

8. Branching & PR Creation
   - Create branch from base (usually main)
   - Commit generated code
   - Open PR in draft mode (not ready for review)

9. Callback
   - Post comment to original issue/PR
   - Summary: "Created draft PR #456 with changes; see validation report"
   - Link to PR

10. Task Complete
    - Set state → completed
    - Emit telemetry: task.completed
    - Artifact: GitHub PR URL, validation report

11. Human Action
    - User reviews PR draft
    - Iterates if needed
    - Merges when satisfied
```

---

### Layer 3: Tool Governance

**Purpose:** Centralized authorization and audit for internal tool access.

#### 3.1 Enterprise Tool Gateway

**Components:**
- **Tool Registry** — Curated list of approved tools
  ```python
  Tool:
    id: str
    name: str
    description: str
    capability: Literal["read_only", "mutate", "approve_required"]
    required_org_role: Optional[str]
    approval_gate: bool
    schema_url: str
    connector_type: Literal["mcp", "rest_api", "internal_service"]
    connector_config: dict
  ```

- **Authorization Engine**
  - Input: user, user_roles, tool_id
  - Check: is user in required_org_role? Is tool read_only? Does approval exist?
  - Output: Permit or Deny

- **Tool Connectors** — Pluggable implementations
  - **MCP Connector** — For tools exposed via Model Context Protocol
  - **REST Connector** — For internal HTTP APIs
  - **Internal Service Connector** — For AWS services (Lambda, DynamoDB, etc.)

#### 3.2 Example: Read-Only Tool Lookup (S4)

```
Task: "What's the deploy status of service-a in staging?"

1. Intent Recognition
   - Parse: tool="deployment_status", service="service-a", env="staging"

2. Tool Gateway Authorization
   - User ID: github_user_123
   - User roles: [engineer, team-frontend]
   - Tool: deployment_status (read_only, required_role=engineer)
   - Check: user has engineer role? YES → Permit

3. Tool Invocation
   - Connector type: REST
   - Endpoint: https://internal.company.com/api/deploys
   - Request: GET /deploys/service-a?env=staging
   - Response: { status: "healthy", last_deploy: "2024-04-08T10:30Z", ... }

4. Result Processing
   - Sanitize response (no exposed secrets)
   - Summarize: "Service A is healthy; last deploy 10:30 UTC today"

5. Callback
   - Post to GitHub: "Status: Healthy (last deploy 10:30 UTC)"
   - Log: tool invocation in CloudWatch

6. Audit
   - CloudTrail: who accessed what tool when
   - Tool gateway metrics: invocation count, duration
```

#### 3.3 Example: Approval-Gated Mutation (S5, Narrow)

```
Task: "Rerun the deploy check for service-a"

1. Intent Recognition
   - Parse: tool="deploy_control", operation="rerun_check", service="service-a"

2. Tool Gateway Authorization
   - User ID: github_user_123
   - User roles: [engineer, on-call]
   - Tool: deploy_control (mutate, approval_gate=true, required_role=on-call)
   - Check: user has on-call role? YES
   - Check: is approval required? YES → Wait for Approval

3. Approval Request
   - Generate: "User wants to rerun deploy check for service-a; approve?"
   - Route to: team-on-call or platform-team (configured)
   - Method: GitHub comment reply, Slack notification, or admin portal (future)

4. Approval Received
   - Mark: approval_granted=true, approved_by=platform-oncall, approved_at=2026-04-08T11:00Z

5. Tool Invocation (after approval)
   - Connector type: Internal Service
   - Call: invoke_deploy_check(service_id="service-a")
   - Response: { check_id: "chk_789", status: "queued" }

6. Result Processing
   - Return: "Initiated deploy check; tracking ID: chk_789"

7. Callback
   - Post to GitHub: "Deploy check started (ID: chk_789)"
   - Edited into original comment: status updates as check progresses

8. Audit
   - CloudTrail: who requested, who approved, what action was taken
   - Tool gateway: mutation logged with full context
```

---

### Layer 4: Validation

**Purpose:** Deterministic verification of generated code before it reaches humans.

#### 4.1 Validation Interface

**Components:**
- **Validation Request** — What to check
  ```python
  ValidationRequest:
    task_id: str
    artifact_path: str (S3 URL or git ref)
    checks: List[str] (["lint", "test", "security"])
    timeout_seconds: int
    backend: Literal["codebuild", "agentcore", "local"]
  ```

- **Validation Result** — Deterministic outcome
  ```python
  ValidationResult:
    validation_id: str
    status: Literal["passed", "failed", "warnings", "skipped"]
    checks: List[CheckResult] (details per check)
    artifacts: List[str] (links to logs, reports)
    duration_seconds: float
  ```

#### 4.2 Validation Backends

**CodeBuild (v1 optional reference)**
- Useful for: lint, unit tests, security scans
- Limitation: requires setup (reserved fleet is paid)
- Usage: if customer has CodeBuild pipeline already

**AgentCore Runtime (v1 default lightweight)**
- Useful for: basic linting, quick tests
- Runs in: same session or new session
- Limitation: respects 8h async and 15m sync timeouts

**Local (Developer testing)**
- Useful for: development workflows
- Runs in: local environment (Docker if possible)

#### 4.3 Validation in PR Draft Workflow

```
Generated Code
  ↓
Validation Request: checks=[lint, test, security]
  ↓
Run Checks (CodeBuild or AgentCore)
  ├─ lint: python -m black --check; ruff check
  │ Result: ✓ Passed
  ├─ test: python -m pytest
  │ Result: ✓ Passed
  └─ security: bandit --severity medium
    Result: ⚠ 1 warning (hardcoded password-like string)
  ↓
ValidationResult:
  status: warnings
  summary: "2/3 checks passed; 1 security warning"
  artifacts:
    - s3://bucket/validations/task_123/lint_report.txt
    - s3://bucket/validations/task_123/test_results.xml
    - s3://bucket/validations/task_123/security_report.json
  ↓
PR Draft Created
  - Comment includes validation summary
  - Links to detailed reports
  - Human can decide if warnings are acceptable
```

---

### Layer 5: Observability

**Purpose:** Complete visibility into task execution, tool usage, and system health.

#### 5.1 Metrics Emitted

**Task Metrics:**
- `taskplane_tasks_created` (counter) — By workflow_type, repo, user
- `taskplane_tasks_completed` (counter) — By status, duration_bucket
- `taskplane_task_duration` (histogram) — Seconds, by workflow_type
- `taskplane_tasks_waiting_approval` (gauge) — Current count

**Tool Metrics:**
- `taskplane_tool_invocations` (counter) — By tool_id, user, status
- `taskplane_tool_authorization_denied` (counter) — By tool_id, reason
- `taskplane_tool_latency` (histogram) — Seconds, by tool_id

**Validation Metrics:**
- `taskplane_validation_checks_total` (counter) — By check_type, status
- `taskplane_validation_duration` (histogram) — Seconds, by backend

**System Metrics (from existing foundation):**
- Token usage (input/output)
- Bedrock model invocation count
- User session duration

#### 5.2 Dimensions

All metrics tagged with:
- `user_id` (from GitHub / AWS)
- `repo_id` (full GitHub identifier)
- `user_team` (from AWS role or GitHub team)
- `cost_center` (if available in identity token)
- `environment` (prod, staging, dev)

#### 5.3 Dashboards

**Task Health Dashboard:**
- Task success rate (%), trend
- Task latency (p50, p99)
- Active tasks (gauge)
- Waiting for approval (gauge)
- Failed tasks (recent)

**Tool Usage Dashboard:**
- Most-used tools (count)
- Tool authorization denials (count)
- Tool latency (by tool)
- Approval gates exercised (count)

**Validation Dashboard:**
- Check pass rates (by type)
- Most common failures (lint, test, security)
- Validation latency

**Audit Dashboard:**
- Tasks by user/team
- Tool mutations (count)
- PR drafts created
- Reviews triggered

#### 5.4 Events for Audit Log

**Emitted to CloudWatch & StreamedElsewhere:**

1. `task.created`
   - task_id, user_id, workflow_type, repo_id
   - timestamp, request_summary

2. `task.started`
   - task_id, agentcore_session_id
   - timestamp

3. `task.state_changed`
   - task_id, old_state, new_state
   - timestamp, reason

4. `task.completed`
   - task_id, final_status, artifact_count
   - duration, timestamp

5. `tool.invocation_requested`
   - task_id, user_id, tool_id, operation
   - approval_required, timestamp

6. `tool.authorization_check`
   - user_id, tool_id, permitted (bool), reason
   - timestamp

7. `tool.invoked`
   - task_id, user_id, tool_id, operation
   - result (success/error), duration
   - timestamp

8. `approval.requested`
   - task_id, approval_type, routing_target
   - timestamp

9. `approval.granted`
   - task_id, approved_by, timestamp

10. `validation.requested`
    - task_id, checks, backend
    - timestamp

11. `validation.completed`
    - validation_id, status, duration
    - timestamp

---

## Data Flow Sequences

### Sequence 1: Simple Explanation (S1)

```
1. GitHub: User comments "@claude explain this error"
2. GitHub Webhook → Lambda
3. Event Normalizer: extract command, repo, context
4. Task Manager: create Task(state=queued)
5. Async Worker picks up task
6. Set state→running, emit telemetry
7. GitHub Adapter: fetch repo files, error logs
8. Tool Gateway: any read-only tool queries needed?
9. Claude Code: send prompt via AgentCore
10. Bedrock: returns explanation
11. Validation: (none needed for answer-only)
12. GitHub Callback: post explanation as comment
13. Set state→completed, emit telemetry
14. Done (human reads explanation, may iterate)
```

**Duration:** 30-120 seconds  
**Artifacts:** GitHub comment URL  
**Audit trail:** CloudTrail (Bedrock call), CloudWatch (task events)

---

### Sequence 2: PR Draft with Validation (S2)

```
1. GitHub: User comments "@claude fix the null handling and open a PR"
2. GitHub Webhook → Lambda
3. Event Normalizer: extract command, file, intent
4. Task Manager: create Task(state=queued, workflow_type=pr_draft)
5. Async Worker picks up task
6. Set state→running, emit telemetry
7. GitHub Adapter: fetch repo context, checkout main
8. Tool Gateway: (none needed)
9. Claude Code: send fix prompt via AgentCore
10. Bedrock: returns code patch
11. Validation: run lint, test, security checks
12. Create branch, commit code, push
13. GitHub API: open PR in draft mode
14. GitHub Callback: post comment with PR link and validation summary
15. Set state→completed, emit telemetry
16. Done (human reviews PR, iterates or merges)
```

**Duration:** 2-10 minutes (depends on validation backend)  
**Artifacts:** GitHub PR URL, validation reports (S3 links)  
**Audit trail:** CloudTrail (Bedrock, GitHub), CloudWatch (task + validation events)

---

### Sequence 3: Approval-Gated Tool Mutation (S5)

```
1. GitHub: User comments "@claude rerun the deploy check"
2-6. (same as S1)
7. Tool Gateway: look up "deploy_check" tool
8. Authorization: user has on-call role? YES
9. Check: approval_gate=true? YES → enter approval workflow
10. Create approval request (route to on-call team)
11. Set state→waiting_for_approval, emit telemetry
12. Approval system: human reviews and approves
13. Set state→running (after approval), emit telemetry
14. Tool Invocation: call deploy_check tool via connector
15. Tool returns: check initiated (ID: chk_789)
16. GitHub Callback: post "Deploy check started (ID: chk_789)"
17. Set state→completed, emit telemetry
18. Done (task completes, human monitors check progress separately)
```

**Duration:** depends on approval time (minutes to hours)  
**Artifacts:** GitHub comment with check ID  
**Audit trail:** CloudTrail, CloudWatch (includes approval decision)

---

## API Contracts (Scaffolding)

### Task Manager API

```python
class TaskManager(ABC):
    async def create_task(self, request: TaskRequest) -> Task
    async def get_task(self, task_id: str) -> Task
    async def list_tasks(self, filters: TaskFilter) -> List[Task]
    async def update_task(self, task_id: str, updates: TaskUpdate) -> Task
    async def cancel_task(self, task_id: str, reason: str) -> Task
    async def retry_task(self, task_id: str) -> Task
```

### Tool Gateway API

```python
class ToolRegistry(ABC):
    async def list_available_tools(self, user_id: str, roles: List[str]) -> List[Tool]
    async def authorize(self, user_id: str, roles: List[str], tool_id: str) -> bool
    async def invoke_tool(self, request: ToolInvocationRequest) -> ToolInvocationResult
    async def get_tool_schema(self, tool_id: str) -> dict
```

### GitHub Adapter API

```python
class GitHubAdapter(ABC):
    async def post_comment(self, repo: str, issue_number: int, body: str) -> str
    async def create_pr(self, repo: str, branch: str, title: str, body: str) -> PullRequest
    async def add_review_comment(self, repo: str, pr_number: int, comment: str) -> str
```

---

## Implementation Notes

### In v1: Scaffolding
- Interfaces and data models are production-ready
- Implementations are reference/sample (can be replaced)
- PostgreSQL or DynamoDB for task storage (pluggable)
- Lambda for webhook handler (can be ECS if needed)

### Not in v1: Deferred
- Full AgentCore Runtime integration (async job manager)
- Claude Code / Bedrock invocation details
- Multi-repo policy composition
- Team/org hierarchy enforcement
- Fine-grained approval workflows

### Out of Scope (v1)
- Heavy monorepo support (S6)
- Slack as primary surface (v1.5)
- Dynamic policy engine
- MCP marketplace

---

## Deployment Topology

**Minimum viable v1 deployment:**

```
AWS Account
├─ Lambda (GitHub webhook handler)
├─ RDS / DynamoDB (task store)
├─ CloudWatch (logs, metrics)
├─ Bedrock (Claude Code)
├─ AgentCore Runtime (task execution)
└─ CloudTrail (audit)

GitHub Organization
├─ Webhook configured for enabled repos
└─ GitHub App (optional, for PR creation)

Customer's IdP
└─ OIDC provider (Okta, Azure, Auth0, Cognito)

Internal Services (optional, for S4/S5)
└─ Tool Gateway (MCP, REST, or custom connectors)
```

**Operational requirements:**
- CloudWatch dashboard for monitoring
- CloudTrail enabled and exported to S3
- GitHub webhook secret securely stored (AWS Secrets Manager)
- Tool connector configurations (per tool)
- Approval workflow configuration (who approves what)

---

**Document version:** 1.0  
**Last updated:** 2026-04-08  
**Status:** Approved for v1 implementation
