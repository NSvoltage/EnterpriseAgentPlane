# PR 3: Task Lifecycle Models — Pydantic Definitions

Production-ready Pydantic models for task lifecycle, artifacts, and state management.

**Location in repo:** `source/taskplane/models.py`

## Enum: TaskState

```python
from enum import Enum

class TaskState(str, Enum):
    """Task execution states in dependency order."""
    
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
```

### State Transition Rules

Valid transitions (enforced by TaskManager):

```
QUEUED → RUNNING
RUNNING → COMPLETED | FAILED | CANCELED
RUNNING → WAITING_FOR_APPROVAL → RUNNING | FAILED (if approval denied)
```

**Invalid transitions (reject):**
- COMPLETED → any
- FAILED → any
- CANCELED → any
- QUEUED → WAITING_FOR_APPROVAL (approval happens during RUNNING)
- QUEUED → COMPLETED

---

## Enum: WorkflowType

```python
class WorkflowType(str, Enum):
    """What kind of workflow this task is executing."""
    
    ANSWER_ONLY = "answer_only"       # S1: explanation, read-only
    PR_DRAFT = "pr_draft"              # S2: generate code, create PR
    REVIEW = "review"                  # S3: analyze PR, post review
    TOOL_LOOKUP = "tool_lookup"        # S4: read-only tool access
    TOOL_MUTATION = "tool_mutation"    # S5: approval-gated tool mutation
```

---

## Enum: TaskArtifactType

```python
class TaskArtifactType(str, Enum):
    """Kind of artifact this task produced."""
    
    GITHUB_COMMENT = "github_comment"
    GITHUB_PR = "github_pr"
    GITHUB_REVIEW = "github_review"
    VALIDATION_REPORT = "validation_report"
    TOOL_ACCESS_LOG = "tool_access_log"
    ERROR_SUMMARY = "error_summary"
```

---

## Model: TaskArtifact

```python
from datetime import datetime
from pydantic import BaseModel, Field

class TaskArtifact(BaseModel):
    """A result or output produced during task execution."""
    
    # Identity
    id: str = Field(..., description="UUID for this artifact")
    task_id: str = Field(..., description="Task that created this artifact")
    
    # Content
    artifact_type: TaskArtifactType = Field(..., description="Kind of artifact")
    content_url: str = Field(
        ..., 
        description="S3 URL, GitHub URL, or path where content is stored"
    )
    
    # Metadata
    metadata: dict = Field(
        default_factory=dict,
        description="Extra context (e.g., {'pr_number': 456, 'check_count': 3})"
    )
    
    # Lineage
    created_at: datetime = Field(..., description="When artifact was created")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "id": "artifact_abc123",
                "task_id": "task_xyz789",
                "artifact_type": "github_comment",
                "content_url": "https://github.com/org/repo/issues/42#issuecomment-999",
                "metadata": {"issue_number": 42},
                "created_at": "2026-04-08T10:30:00Z"
            }
        }
```

---

## Model: Task

```python
from typing import List, Optional

class Task(BaseModel):
    """A unit of work triggered by a GitHub event."""
    
    # === Identity ===
    id: str = Field(..., description="UUID for this task")
    
    # === User & Repo Context ===
    user_id: str = Field(..., description="GitHub user ID who triggered the task")
    user_email: str = Field(..., description="GitHub user email (for attribution)")
    repo_id: str = Field(..., description="GitHub repo (owner/repo)")
    repo_owner: str = Field(..., description="GitHub org/user owner")
    repo_name: str = Field(..., description="Repository name")
    
    # === Workflow & Intent ===
    workflow_type: WorkflowType = Field(..., description="What kind of task is this")
    command_type: str = Field(
        ..., 
        description="Parsed command (explain, fix, review, status, etc.)"
    )
    
    # === GitHub Trigger Context ===
    trigger_type: str = Field(
        ..., 
        description="Event type (issue_comment, pr_comment, pr_opened, etc.)"
    )
    trigger_id: str = Field(
        ..., 
        description="Comment ID, issue #, or PR # that triggered this"
    )
    issue_number: Optional[int] = Field(None, description="Issue # if on issue")
    pr_number: Optional[int] = Field(None, description="PR # if on PR")
    
    # === Execution State ===
    state: TaskState = Field(..., description="Current state of the task")
    created_at: datetime = Field(..., description="When task was created")
    started_at: Optional[datetime] = Field(None, description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When execution completed")
    
    # === Approval (for mutations) ===
    approval_required: bool = Field(
        default=False, 
        description="Does this task need human approval?"
    )
    approved_by: Optional[str] = Field(None, description="Who approved (if applicable)")
    approved_at: Optional[datetime] = Field(None, description="When approved")
    
    # === Execution Details ===
    agentcore_session_id: Optional[str] = Field(
        None, 
        description="AgentCore session ID if one was created"
    )
    
    # === Artifacts ===
    artifacts: List[TaskArtifact] = Field(
        default_factory=list,
        description="All outputs/results from this task"
    )
    
    # === Error Handling ===
    error_message: Optional[str] = Field(None, description="If failed, the error")
    
    # === Request Preservation ===
    request_body: dict = Field(
        ..., 
        description="Original GitHub webhook payload (for audit/replay)"
    )
    
    # === Metadata ===
    metadata: dict = Field(
        default_factory=dict,
        description="Extra context (tags, labels, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "task_abc123",
                "user_id": "github_user_123",
                "user_email": "engineer@company.com",
                "repo_id": "myorg/backend-api",
                "repo_owner": "myorg",
                "repo_name": "backend-api",
                "workflow_type": "answer_only",
                "command_type": "explain",
                "trigger_type": "issue_comment",
                "trigger_id": "999",
                "issue_number": 42,
                "pr_number": None,
                "state": "completed",
                "created_at": "2026-04-08T10:30:00Z",
                "started_at": "2026-04-08T10:30:05Z",
                "completed_at": "2026-04-08T10:31:30Z",
                "approval_required": False,
                "approved_by": None,
                "approved_at": None,
                "agentcore_session_id": "session_xyz789",
                "artifacts": [
                    {
                        "id": "artifact_a1",
                        "task_id": "task_abc123",
                        "artifact_type": "github_comment",
                        "content_url": "https://github.com/myorg/backend-api/issues/42#issuecomment-123",
                        "metadata": {"issue_number": 42},
                        "created_at": "2026-04-08T10:31:30Z"
                    }
                ],
                "error_message": None,
                "request_body": {/* GitHub webhook payload */},
                "metadata": {"duration_seconds": 90.0}
            }
        }
```

---

## Model: TaskRequest

```python
from typing import Optional

class TaskRequest(BaseModel):
    """Input to create a new task (normalized from GitHub event)."""
    
    # === User & Repo ===
    user_id: str
    user_email: str
    repo_id: str
    repo_owner: str
    repo_name: str
    
    # === Trigger Context ===
    trigger_type: str  # issue_comment, pr_comment, pr_opened, etc.
    trigger_id: str    # comment_id, issue #, pr #
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    
    # === Workflow Intent ===
    workflow_type: WorkflowType
    command_type: str
    command_text: Optional[str] = None
    
    # === GitHub Event (for audit) ===
    github_event: dict = Field(..., description="Raw GitHub webhook payload")
```

---

## Model: TaskUpdate

```python
class TaskUpdate(BaseModel):
    """Partial update to an existing task."""
    
    state: Optional[TaskState] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    artifacts: Optional[List[TaskArtifact]] = None
    metadata: Optional[dict] = None
    
    class Config:
        # Allow partial updates (all fields optional)
        extra = "forbid"
```

---

## Model: TaskFilter

```python
from typing import List

class TaskFilter(BaseModel):
    """Query parameters for listing tasks."""
    
    repo_id: Optional[str] = None
    user_id: Optional[str] = None
    state: Optional[TaskState] = None
    workflow_type: Optional[WorkflowType] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
```

---

## Model: TaskResult

```python
class TaskResult(BaseModel):
    """Final result of a task (for callbacks and reporting)."""
    
    task_id: str
    state: TaskState
    output_summary: str = Field(
        ..., 
        description="Human-readable summary of what happened"
    )
    artifacts: List[TaskArtifact]
    error: Optional[str] = None
    duration_seconds: float = Field(..., description="Total execution time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "state": "completed",
                "output_summary": "Analyzed the issue and posted explanation in GitHub",
                "artifacts": [
                    {
                        "id": "artifact_a1",
                        "task_id": "task_abc123",
                        "artifact_type": "github_comment",
                        "content_url": "https://github.com/myorg/backend-api/issues/42#issuecomment-123",
                        "metadata": {},
                        "created_at": "2026-04-08T10:31:30Z"
                    }
                ],
                "error": None,
                "duration_seconds": 90.0
            }
        }
```

---

## Interface: TaskManager

```python
from abc import ABC, abstractmethod

class TaskManager(ABC):
    """Abstract interface for task lifecycle management."""
    
    @abstractmethod
    async def create_task(self, request: TaskRequest) -> Task:
        """Create a new task from a normalized request.
        
        Args:
            request: Normalized task request (from GitHub adapter)
            
        Returns:
            Created task with state=queued
            
        Raises:
            TaskCreationError: If task cannot be created
        """
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID.
        
        Args:
            task_id: UUID of the task
            
        Returns:
            The task
            
        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        pass
    
    @abstractmethod
    async def list_tasks(self, filters: TaskFilter) -> List[Task]:
        """List tasks matching filters.
        
        Args:
            filters: Query parameters
            
        Returns:
            List of matching tasks (paginated)
        """
        pass
    
    @abstractmethod
    async def update_task(self, task_id: str, updates: TaskUpdate) -> Task:
        """Update a task's state and metadata.
        
        Args:
            task_id: UUID of the task
            updates: Partial update (only specified fields are updated)
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task doesn't exist
            InvalidStateTransition: If state transition is invalid
        """
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str, reason: str) -> Task:
        """Cancel a task (move to CANCELED state).
        
        Args:
            task_id: UUID of the task
            reason: Why the task is being canceled
            
        Returns:
            Updated task with state=canceled
            
        Raises:
            TaskNotFoundError: If task doesn't exist
            CannotCancelError: If task is already terminal
        """
        pass
    
    @abstractmethod
    async def retry_task(self, task_id: str) -> Task:
        """Retry a failed task (move back to QUEUED).
        
        Args:
            task_id: UUID of the task
            
        Returns:
            Task reset to state=queued
            
        Raises:
            TaskNotFoundError: If task doesn't exist
            CannotRetryError: If task is not in FAILED state
        """
        pass
```

---

## Exception Classes

```python
class TaskError(Exception):
    """Base exception for task operations."""
    pass

class TaskNotFoundError(TaskError):
    """Task with given ID does not exist."""
    pass

class TaskCreationError(TaskError):
    """Task could not be created."""
    pass

class InvalidStateTransition(TaskError):
    """Task state transition is invalid."""
    pass

class CannotCancelError(TaskError):
    """Task cannot be canceled (already terminal)."""
    pass

class CannotRetryError(TaskError):
    """Task cannot be retried (not in FAILED state)."""
    pass
```

---

## Testing

### Test Cases (pytest)

```python
# test_task_models.py

def test_task_state_enum():
    """TaskState enum has expected values."""
    assert TaskState.QUEUED.value == "queued"
    assert TaskState.RUNNING.value == "running"
    assert TaskState.COMPLETED.value == "completed"

def test_task_artifact_serialization():
    """TaskArtifact serializes to JSON deterministically."""
    artifact = TaskArtifact(
        id="a1",
        task_id="t1",
        artifact_type=TaskArtifactType.GITHUB_COMMENT,
        content_url="https://example.com/comment",
        created_at=datetime.utcnow()
    )
    json_str = artifact.model_dump_json()
    assert "github_comment" in json_str
    assert "a1" in json_str

def test_task_serialization_round_trip():
    """Task can be serialized and deserialized losslessly."""
    task = Task(
        id="t1",
        user_id="u1",
        user_email="user@example.com",
        repo_id="org/repo",
        repo_owner="org",
        repo_name="repo",
        workflow_type=WorkflowType.ANSWER_ONLY,
        command_type="explain",
        trigger_type="issue_comment",
        trigger_id="c1",
        state=TaskState.QUEUED,
        created_at=datetime.utcnow(),
        request_body={},
    )
    json_str = task.model_dump_json()
    task2 = Task.model_validate_json(json_str)
    assert task2.id == task.id
    assert task2.workflow_type == task.workflow_type

def test_task_invalid_state_transition():
    """Invalid state transitions are detected."""
    # COMPLETED -> RUNNING should be invalid
    # (This is enforced at TaskManager level, not model level)
    task = Task(..., state=TaskState.COMPLETED)
    # Can create the object, but TaskManager.update_task() would reject the transition
```

---

## Design Rationale

### Why These Models?

1. **TaskState** — Explicit state machine prevents invalid workflows
2. **Task** — Complete lineage (preserves original GitHub event for audit/replay)
3. **TaskArtifact** — Decoupled from Task so artifacts can be retrieved independently
4. **TaskManager interface** — Pluggable: can be backed by PostgreSQL, DynamoDB, in-memory, etc.
5. **Exceptions** — Specific exceptions allow callers to handle different errors

### What's NOT in the Model?

- **Execution details** — Task doesn't know about Claude Code, validation, tools (those are separate concerns)
- **Approval routing logic** — Task just tracks approval_required/approved_by (routing is in tool gateway)
- **GitHub integration** — Task is GitHub-agnostic; GitHub adapter handles conversion

---

## Next Steps (PR 4+)

- **PR 4:** GitHub adapter normalizes events → TaskRequest
- **PR 5:** Tool gateway uses tasks to track mutations
- **PR 6:** Validation interface creates artifacts
- **PR 7:** Telemetry emits events for each state transition

---

**File:** `source/taskplane/models.py`  
**Status:** Ready for implementation  
**Tests:** Required for all model methods  
**Doc reference:** See PR2_TASK_LIFECYCLE_PLACEHOLDER.md
