# EnterpriseAgentPlane — Detailed Implementation Plan

## Build Thesis

Extend `guidance-for-claude-code-with-amazon-bedrock` (AWS) into a **GitHub-first enterprise deployment foundation** for Claude Code on Bedrock.

**Core principle**: Preserve proven foundation (auth, federation, monitoring). Add workflow + task layer on top.

---

## Phase 1: Positioning & Contracts (PRs 1-2)

### PR 1 — Positioning & Scope Truthfulness (Foundational)

**Goal**: Establish honest, coherent v1 narrative that prevents implementation drift.

**Key Files to Create/Modify:**
- `README.md` - New headline narrative, v1/v1.5/v2 callouts
- `ROADMAP.md` - Explicit multi-phase scoping
- `assets/docs/SECURITY_BOUNDARIES.md` - Threat model and what is/isn't protected
- `assets/docs/ARCHITECTURE_V1.md` - How GitHub ingress + task lifecycle layers work
- Update existing docs with v1-specific caveats

**Content Principles:**
- "GitHub-first enterprise deployment foundation" is the headline
- Explicitly call out what is NOT in v1 (heavy monorepo, Teams, Slack primary, persistent storage as hard requirement)
- Position AgentCore as "control plane + light/medium execution" with clear runtime limits
- Explain why we fork AWS repo instead of starting fresh
- Separate "foundation layer" (auth/monitoring/packaging) from "v1 workflow layer" (GitHub/task/tools)

**Artifacts:**
- [ ] New README.md (200-400 words, strategic positioning)
- [ ] ROADMAP.md (v1/v1.5/v2 phase definitions)
- [ ] SECURITY_BOUNDARIES.md (threat model, assumptions, what is out of scope)
- [ ] ARCHITECTURE_V1.md (layered architecture diagram in text/markdown)

**Acceptance Criteria:**
- README truthfully describes v1 scope
- Security claims are honest (no "universal sandbox")
- Roadmap is explicit about future phases
- AWS foundation repo is acknowledged as the base

---

### PR 2 — Land Design Contracts (Reference Documents)

**Goal**: Make scenario pack, requirements, ADRs, and fit matrix authoritative reference material in the repo.

**Changes:**
- Copy all files from EnterpriseAgentPlane build pack into `assets/docs/design/`
  - `01_scenario_pack.md` → `assets/docs/design/SCENARIOS.md`
  - `02_requirements_matrix.csv` → `assets/docs/design/REQUIREMENTS.csv`
  - `03_service_fit_matrix.md` → `assets/docs/design/SERVICE_FIT.md`
  - `04_adrs.md` → `assets/docs/design/ARCHITECTURE_DECISIONS.md`
- Create `assets/docs/GITHUB_WORKFLOWS.md` - How GitHub triggers map to task types
- Create `assets/docs/TASK_LIFECYCLE.md` - Placeholder (detail in PR 3)

**Acceptance Criteria:**
- All design docs are in the repo and linked from README
- Scenario contracts are the source of truth for what "in v1" means
- Developers can reference these when evaluating PRs

---

## Phase 2: Core Abstractions (PRs 3-5)

### PR 3 — Task Lifecycle Model

**Goal**: Define the async task abstraction that all workflows sit on top of.

**File Structure:**
```
source/taskplane/
├── __init__.py
├── models.py           # Pydantic models for Task, TaskResult, TaskArtifact
├── state.py            # Enum + FSM for task states
├── lifecycle.py        # TaskManager interface (abstract base)
├── errors.py           # TaskError, TaskTimeoutError, etc.
```

**Models to Define:**

1. **TaskState** (Enum)
   - `queued` → `running` → one of: `completed`, `failed`, `canceled`, `waiting_for_approval`
   - Explicit transition rules (e.g., can't go from completed → running)

2. **Task** (Pydantic model)
   ```python
   class Task(BaseModel):
       id: str  # UUID
       user_id: str  # From GitHub user or AWS principal
       repo_id: str  # GitHub repo identifier
       trigger_type: Literal["issue_comment", "pr_comment", "issue_assignment", "pr_open"]
       trigger_id: str  # Comment ID, issue #, PR #, etc.
       
       state: TaskState
       workflow_type: Literal["answer_only", "pr_draft", "review", "tool_lookup"]
       
       # Execution
       agentcore_session_id: Optional[str]
       created_at: datetime
       started_at: Optional[datetime]
       completed_at: Optional[datetime]
       
       # Lineage
       request_body: dict  # Original GitHub event
       artifacts: List[TaskArtifact]
       
       # Governance
       approval_required: bool
       approved_by: Optional[str]
       approved_at: Optional[datetime]
   ```

3. **TaskArtifact** (Pydantic model)
   ```python
   class TaskArtifact(BaseModel):
       id: str
       task_id: str
       artifact_type: Literal["github_comment", "pr_link", "validation_report", "tool_access_log"]
       content_url: str  # S3 or GitHub link
       created_at: datetime
       metadata: dict  # Extra context
   ```

4. **TaskResult** (Pydantic model)
   ```python
   class TaskResult(BaseModel):
       task_id: str
       state: TaskState
       output_summary: str  # Human-readable summary
       artifacts: List[TaskArtifact]
       error: Optional[str]
       duration_seconds: float
   ```

5. **TaskManager** (Abstract Base)
   ```python
   class TaskManager(ABC):
       async def create_task(self, request: TaskRequest) -> Task
       async def get_task(self, task_id: str) -> Task
       async def list_tasks(self, filters: TaskFilter) -> List[Task]
       async def update_task(self, task_id: str, updates: dict) -> Task
       async def cancel_task(self, task_id: str, reason: str) -> Task
       async def retry_task(self, task_id: str) -> Task
   ```

**Documentation:**
- `assets/docs/TASK_LIFECYCLE.md` - Full state machine diagram, examples, error handling

**Tests:**
- State transition validation
- Artifact serialization
- Task model round-trip (JSON serialization)

**Acceptance Criteria:**
- State machine is explicit and testable
- All task types (S1–S5) can be represented in the model
- Serialization is deterministic (for audit/replay)
- TaskManager interface is clear (implementations TBD later)

---

### PR 4 — GitHub Adapter (Scaffolding)

**Goal**: Define how GitHub events map to Task lifecycle. This is the ingress contract.

**File Structure:**
```
source/taskplane/
├── github_adapter.py   # Event parsing and normalization
├── github_models.py    # Pydantic models for GitHub payloads
└── github_callbacks.py # Status update contracts
```

**Core Abstractions:**

1. **GitHubEventNormalizer**
   - Converts GitHub webhook payloads → TaskRequest
   - Handles: issue_comment, pull_request_review_comment, pull_request, issues
   - Extracts: user, repo, branch, content, trigger context

2. **GitHubTaskRequest** (Pydantic model)
   ```python
   class GitHubTaskRequest(BaseModel):
       event_type: Literal["comment", "assignment", "pr_opened", "review_requested"]
       user_login: str
       user_id: int
       repo_owner: str
       repo_name: str
       repo_full_name: str
       
       comment_id: Optional[int]
       comment_body: str
       issue_number: Optional[int]
       pr_number: Optional[int]
       
       # Branch info (for PR draft workflows)
       target_branch: Optional[str]
       
       # Parsed intent
       mentioned_claude: bool
       command_text: Optional[str]  # e.g., "@claude fix the null handling"
   ```

3. **GitHubStatusCallback** (Interface)
   - Methods: post_comment(), update_pr(), add_review_comment()
   - Used by task execution to report back status

**Documentation:**
- `assets/docs/GITHUB_WORKFLOWS.md` - Update with detailed event → task flow
- Include examples: "Explain this" → S1, "Fix and PR" → S2, etc.

**Tests:**
- Event normalization from real GitHub payloads
- Intent parsing (mentions, commands)
- Branch detection

**Acceptance Criteria:**
- GitHub event → TaskRequest conversion is testable
- No business logic here, only normalization
- Can be tested with mock GitHub payloads
- Interface is ready for implementation in later PRs

---

### PR 5 — Enterprise Tool Gateway (Abstraction)

**Goal**: Define how tools are registered, authorized, and invoked. Center on customer outcomes, not protocol.

**File Structure:**
```
source/taskplane/
├── tool_gateway.py     # Tool registry, authorization, invocation
├── tool_models.py      # Pydantic models for tool definitions
└── tool_connectors/    # Directory for connector implementations (future)
    ├── __init__.py
    └── mcp_connector.py  # Reference: how MCP is one connector type
```

**Core Models:**

1. **ToolCapability** (Enum)
   ```python
   class ToolCapability(str, Enum):
       READ_ONLY = "read_only"
       MUTATE = "mutate"
       APPROVE = "approve_required"
   ```

2. **Tool** (Pydantic model)
   ```python
   class Tool(BaseModel):
       id: str  # Unique identifier
       name: str
       description: str
       capability: ToolCapability
       
       # Governance
       required_org_role: Optional[str]  # "team-lead", "on-call", etc.
       approval_gate: bool
       
       # Discovery
       schema_url: str  # Link to tool definition (OpenAPI, MCP spec, etc.)
       connector_type: Literal["mcp", "rest_api", "internal_service"]
       connector_config: dict
       
       # Audit
       owner_email: str
       last_updated: datetime
       usage_quota: Optional[int]  # Per day/user
   ```

3. **ToolInvocationRequest** (Pydantic model)
   ```python
   class ToolInvocationRequest(BaseModel):
       task_id: str
       user_id: str
       user_roles: List[str]
       tool_id: str
       operation: str
       input_params: dict
       
       # Governance
       require_approval: bool = False
       requested_at: datetime
   ```

4. **ToolInvocationResult** (Pydantic model)
   ```python
   class ToolInvocationResult(BaseModel):
       invocation_id: str
       task_id: str
       tool_id: str
       status: Literal["success", "denied", "error", "timeout"]
       output: Optional[dict]
       error_message: Optional[str]
       
       # Audit
       executed_by: str  # Task executor identity
       executed_at: datetime
       duration_ms: float
   ```

5. **ToolRegistry** (Interface)
   ```python
   class ToolRegistry(ABC):
       async def list_available_tools(self, user_id: str, roles: List[str]) -> List[Tool]
       async def invoke_tool(self, request: ToolInvocationRequest) -> ToolInvocationResult
       async def authorize(self, user_id: str, roles: List[str], tool_id: str) -> bool
       async def get_tool_schema(self, tool_id: str) -> dict  # OpenAPI or equivalent
   ```

**Documentation:**
- `assets/docs/TOOL_GATEWAY.md` - Tool lifecycle, policy model, examples
- Explain: "MCP is one connector type; the product is 'approved tools with central auth/audit'"
- Show: S4 (read-only lookup) and S5 (guarded mutation) examples

**Tests:**
- Tool authorization with different user roles
- Schema fetching and validation

**Acceptance Criteria:**
- Tool model separates "what I can do" from "how it works"
- MCP appears as implementation detail, not product center
- Approval gates are explicit in the model
- Registry interface supports both read-only and mutating tools

---

## Phase 3: Validation & Observability (PRs 6-7)

### PR 6 — Validation Interface

**Goal**: Separate generation from deterministic verification. Support multiple backends.

**File Structure:**
```
source/taskplane/
├── validation.py       # Validation interface and schemas
└── validation_backends/
    ├── __init__.py
    └── codebuild.py    # Reference backend (scaffolding)
```

**Core Models:**

1. **ValidationRequest** (Pydantic model)
   ```python
   class ValidationRequest(BaseModel):
       task_id: str
       artifact_type: Literal["code", "docs", "config"]
       artifact_path: str  # S3 URL or git ref
       
       # What to validate
       checks: List[str]  # ["lint", "test", "security", "build"]
       timeout_seconds: int = 600
       
       # Backend selection
       backend: Literal["codebuild", "agentcore", "local"]
   ```

2. **ValidationResult** (Pydantic model)
   ```python
   class ValidationResult(BaseModel):
       validation_id: str
       task_id: str
       status: Literal["passed", "failed", "warnings", "skipped"]
       
       checks: List[CheckResult]
       summary: str
       
       duration_seconds: float
       backend_used: str
       
       artifacts: List[str]  # Links to logs, reports
   ```

3. **CheckResult** (Pydantic model)
   ```python
   class CheckResult(BaseModel):
       check_name: str
       status: Literal["passed", "failed", "warning", "skipped"]
       output: str
       details: Optional[dict]
   ```

4. **ValidationBackend** (Abstract Base)
   ```python
   class ValidationBackend(ABC):
       async def validate(self, request: ValidationRequest) -> ValidationResult
       async def get_status(self, validation_id: str) -> ValidationResult
       async def cancel(self, validation_id: str) -> None
   ```

**Documentation:**
- `assets/docs/VALIDATION.md` - When to validate, what checks exist, how to add backends

**Important:**
- Do not hardcode to CodeBuild
- Support pluggable backends (local, CodeBuild, future heavy sandboxes)
- Schema is the contract, not the implementation

**Acceptance Criteria:**
- Validation is async and returns deterministic results
- Multiple backends can be swapped without changing task code
- Results are auditable and can be included in PR drafts

---

### PR 7 — Observability & Telemetry Extensions

**Goal**: Extend existing OTEL + CloudWatch foundation with task-level visibility.

**File Structure:**
```
source/taskplane/
├── telemetry.py       # Task-level metrics and events
└── telemetry_models.py
```

**Core Events to Emit:**

1. **task.created** - Task instantiated
   - Dimensions: user_id, repo_id, task_type, workflow_type
   - Attributes: request_summary, estimated_complexity

2. **task.started** - Task execution begins
   - Session ID, backend info

3. **task.completed** - Task finished
   - Duration, result status, artifact count

4. **task.failed** - Task error
   - Error category, recoverable?, user-visible message

5. **tool.invoked** - Tool access attempt
   - Tool ID, user, outcome (allowed/denied/error), duration

6. **validation.completed** - Validation finished
   - Check results, duration, backend

**Metrics:**
- `taskplane_tasks_total` - Counter (by status, workflow_type, repo)
- `taskplane_task_duration_seconds` - Histogram
- `taskplane_tool_invocations_total` - Counter (by tool_id, status)
- `taskplane_validation_duration_seconds` - Histogram (by check type)

**Dashboard Updates:**
- Update existing CloudWatch dashboard to include task lifecycle metrics
- Add task success rate, tool invocation patterns, validation coverage

**Documentation:**
- Update `assets/docs/MONITORING.md` with task-level visibility guidance

**Acceptance Criteria:**
- Task events are emitted at state transitions
- Metrics are tagged with user/repo/workflow dimensions
- Dashboard shows task health at a glance
- Audit log can be reconstructed from telemetry

---

## Phase 4: Sample & Integration (PR 8)

### PR 8 — End-to-End Sample: GitHub Comment → Answer

**Goal**: Show the simplest credible v1 flow working end-to-end. This is a reference, not production claim.

**Components:**
```
assets/samples/github-enterprise-flow/
├── scenario_s1_explain.py        # Concrete example: explain-only workflow
├── lambda_handler.py             # AWS Lambda entry point
├── requirements.txt
├── README.md
└── terraform/                    # (Optional) IaC for sample setup
```

**What the Sample Does:**
1. Receives GitHub issue comment: `@claude explain why service X fails with config Y`
2. Normalizes event → TaskRequest
3. Creates Task (queued)
4. (Scaffolding: would invoke Claude via AgentCore)
5. Creates TaskArtifact (explanation)
6. Posts comment back to GitHub with result
7. Emits telemetry

**Code Structure:**
```python
# scenario_s1_explain.py
async def handle_explain_request(event: GitHubTaskRequest) -> TaskResult:
    """S1 workflow: explain-only"""
    task = await task_manager.create_task(...)
    
    # Fetch repo context
    repo_files = await github_client.list_files(...)
    
    # Would call: result = await agentcore_client.invoke(prompt)
    # For now: return mock result
    
    artifact = TaskArtifact(...)
    await github_callback.post_comment(artifact.content_url)
    
    await task_manager.update_task(task.id, state=TaskState.COMPLETED)
    return TaskResult(...)
```

**Key Points:**
- Explicitly marks places where AgentCore/Claude would be invoked (not implemented yet)
- Shows error handling (repo not enabled, auth failure, timeout)
- Demonstrates task → GitHub callback flow
- Includes telemetry emission

**Documentation:**
- Walkthrough guide: how to deploy the sample
- Mapping to scenario S1
- Known limitations (mock execution)

**Tests:**
- Mock GitHub events
- Verify task state transitions
- Verify telemetry emission

**Acceptance Criteria:**
- Sample is self-contained and runnable (or runnable with minor AWS setup)
- Demonstrates task lifecycle from GitHub event → result
- Clearly marked where real execution backends would plug in
- Is not positioned as "production-ready" but as "reference implementation"

---

## Implementation Principles

### Iterative & Reversible
- Each PR stands alone and adds clear value
- No big refactors in the middle; keep changes small
- Easy to review, easy to revert if needed

### Contract-First
- Define interfaces and data models before implementations
- Tests validate contracts, not full workflows
- Future PRs can plug in real execution without touching existing abstractions

### Honest Scoping
- Explicitly call out what is "scaffolding" vs "working"
- No false claims in docs
- Clearly mark "future work" sections

### Compound on Foundation
- Preserve all existing auth, monitoring, deployment flows
- Add task/workflow layer on top
- No breaking changes to existing CLI or deployment patterns

---

## Success Metrics

### After PR 1-2:
- [ ] Repo story is honest and coherent
- [ ] Design contracts are in the repo
- [ ] Developers understand v1 vs. future

### After PR 3-5:
- [ ] Task lifecycle is explicit
- [ ] GitHub ingress path is clear
- [ ] Tool access is governed through abstraction
- [ ] Models are testable

### After PR 6-7:
- [ ] Validation is pluggable
- [ ] Observability extends existing monitoring
- [ ] Audit trail is complete

### After PR 8:
- [ ] Simplest scenario (S1) is demonstrated end-to-end
- [ ] Reference implementation exists
- [ ] Integration points are clear

---

## Known Constraints & Future Decisions

### Will Revisit in Next Phase:
- AgentCore Runtime integration (actual session management)
- Claude Code / Bedrock invocation patterns
- Private deployment mode
- Slack adapter (v1.5)
- Heavy validation backends (CodeBuild, future)
- Persistent session storage (optional flag)

### Out of Scope (v1):
- Heavy monorepo/mobile toolchains
- Teams/Jira/ServiceNow first-class surfaces
- Universal enterprise policy engine
- Dynamic MCP marketplace

---

## Checkpoint: Before Starting PR 1

- [ ] AWS repo is accessible and understood
- [ ] Branch `claude/review-enterprise-agent-plane-EviWi` is ready for work
- [ ] CI/CD pipeline is operational
- [ ] Pre-commit hooks are configured
- [ ] This plan is reviewed and approved

Let's proceed.
