"""
Task lifecycle models — Pydantic definitions for task management.

This module defines the core data structures for task orchestration:
- TaskState: explicit state machine
- Task: complete task record with lineage
- TaskArtifact: decoupled artifact storage
- TaskManager: pluggable backend interface
- Exceptions: specific error handling

Design rationale:
- Task preserves original GitHub webhook for audit/replay
- Artifacts are separate entities (can be retrieved independently)
- TaskManager is backend-agnostic (PostgreSQL, DynamoDB, in-memory, etc.)
- State machine enforced by TaskManager, not at model level
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Enums
# ============================================================================


class TaskState(str, Enum):
    """Task execution states (explicit state machine).

    Valid transitions:
    - QUEUED → RUNNING
    - RUNNING → COMPLETED | FAILED | CANCELED
    - RUNNING → WAITING_FOR_APPROVAL → RUNNING | FAILED
    """

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkflowType(str, Enum):
    """What kind of workflow this task is executing."""

    ANSWER_ONLY = "answer_only"  # S1: explanation, read-only
    PR_DRAFT = "pr_draft"  # S2: generate code, create PR
    REVIEW = "review"  # S3: analyze PR, post review
    TOOL_LOOKUP = "tool_lookup"  # S4: read-only tool access
    TOOL_MUTATION = "tool_mutation"  # S5: approval-gated tool mutation


class TaskArtifactType(str, Enum):
    """Kind of artifact this task produced."""

    GITHUB_COMMENT = "github_comment"
    GITHUB_PR = "github_pr"
    GITHUB_REVIEW = "github_review"
    VALIDATION_REPORT = "validation_report"
    TOOL_ACCESS_LOG = "tool_access_log"
    ERROR_SUMMARY = "error_summary"


# ============================================================================
# Artifact Model
# ============================================================================


class TaskArtifact(BaseModel):
    """A result or output produced during task execution."""

    # Identity
    id: str = Field(default_factory=lambda: f"artifact_{uuid4().hex[:12]}")
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
        description="Extra context (e.g., pr_number, check_count)"
    )

    # Lineage
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "artifact_abc123",
                "task_id": "task_xyz789",
                "artifact_type": "github_comment",
                "content_url": "https://github.com/org/repo/issues/42#issuecomment-999",
                "metadata": {"issue_number": 42},
                "created_at": "2026-04-08T10:30:00Z"
            }
        }
    )


# ============================================================================
# Task Model
# ============================================================================


class Task(BaseModel):
    """A unit of work triggered by a GitHub event.

    State Machine (validated by TaskManager implementation, not model):
    ─────────────────────────────────────────────────────────────
    QUEUED → RUNNING
        Task execution has started.

    RUNNING → COMPLETED | FAILED | CANCELED
        Task execution has finished (normal termination).

    RUNNING → WAITING_FOR_APPROVAL
        Task requires human approval (mutation workflows only).

    WAITING_FOR_APPROVAL → RUNNING
        Approval was granted, proceed with execution.

    WAITING_FOR_APPROVAL → FAILED
        Approval was denied or timed out.

    Terminal States (no further transitions possible):
    ──────────────────────────────────────────────
    - COMPLETED: Task succeeded
    - FAILED: Task encountered error or approval denied
    - CANCELED: Task was cancelled by user/admin

    Implementation Note:
    ───────────────────
    This model defines the data structure only. State transitions are
    validated by TaskManager implementations (e.g., PostgreSQL, DynamoDB).
    The model does not enforce transition rules; that's the responsibility
    of the TaskManager.update_task() method.
    """

    # === Identity ===
    id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:12]}")

    # === User & Repo Context ===
    user_id: str = Field(..., description="GitHub user ID who triggered the task")
    user_email: str = Field(..., description="GitHub user email (for attribution)")
    repo_id: str = Field(..., description="GitHub repo (owner/repo)")
    repo_owner: str = Field(..., description="GitHub org/user owner")
    repo_name: str = Field(..., description="Repository name")

    # === Workflow & Intent ===
    workflow_type: WorkflowType = Field(..., description="What kind of task")
    command_type: str = Field(..., description="Parsed command (explain, fix, review, etc.)")

    # === GitHub Trigger Context ===
    trigger_type: str = Field(
        ..., description="Event type (issue_comment, pr_comment, etc.)"
    )
    trigger_id: str = Field(..., description="Comment ID, issue #, or PR #")
    issue_number: Optional[int] = Field(None)
    pr_number: Optional[int] = Field(None)

    # === Execution State ===
    state: TaskState = Field(default=TaskState.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)

    # === Approval (for mutations) ===
    approval_required: bool = Field(default=False)
    approved_by: Optional[str] = Field(None)
    approved_at: Optional[datetime] = Field(None)

    # === Execution Details ===
    agentcore_session_id: Optional[str] = Field(None)

    # === Artifacts ===
    artifacts: List[TaskArtifact] = Field(default_factory=list)

    # === Error Handling ===
    error_message: Optional[str] = Field(None)

    # === Request Preservation (for audit/replay) ===
    request_body: dict = Field(...)

    # === Metadata ===
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
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
                "artifacts": [],
                "error_message": None,
                "metadata": {"duration_seconds": 90.0}
            }
        }
    )


# ============================================================================
# Request/Update Models
# ============================================================================


class TaskRequest(BaseModel):
    """Input to create a new task (normalized from GitHub event)."""

    user_id: str
    user_email: str
    repo_id: str
    repo_owner: str
    repo_name: str

    trigger_type: str
    trigger_id: str
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None

    workflow_type: WorkflowType
    command_type: str
    command_text: Optional[str] = None

    github_event: dict = Field(..., description="Raw GitHub webhook payload")


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

    model_config = ConfigDict(extra="forbid")


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


class TaskResult(BaseModel):
    """Final result of a task (for callbacks and reporting)."""

    task_id: str
    state: TaskState
    output_summary: str = Field(...)
    artifacts: List[TaskArtifact] = Field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = Field(...)


# ============================================================================
# TaskManager Interface
# ============================================================================


class TaskManager(ABC):
    """Abstract interface for task lifecycle management.

    Implementations can use PostgreSQL, DynamoDB, Redis, in-memory, etc.
    The interface is backend-agnostic.
    """

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
            updates: Partial update

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task doesn't exist
            InvalidStateTransition: If transition is invalid
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


# ============================================================================
# Exception Classes
# ============================================================================


class TaskError(Exception):
    """Base exception for task operations."""
    pass


class TaskNotFoundError(TaskError):
    """Task with given ID does not exist."""
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class TaskCreationError(TaskError):
    """Task could not be created."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Task creation failed: {reason}")


class InvalidStateTransition(TaskError):
    """Task state transition is invalid."""
    def __init__(self, task_id: str, current_state: TaskState, target_state: TaskState):
        self.task_id = task_id
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(
            f"Cannot transition task {task_id} from {current_state.value} to {target_state.value}"
        )


class CannotCancelError(TaskError):
    """Task cannot be canceled (already terminal)."""
    def __init__(self, task_id: str, current_state: TaskState):
        self.task_id = task_id
        self.current_state = current_state
        super().__init__(f"Cannot cancel task {task_id} (current state: {current_state.value})")


class CannotRetryError(TaskError):
    """Task cannot be retried (not in FAILED state)."""
    def __init__(self, task_id: str, current_state: TaskState):
        self.task_id = task_id
        self.current_state = current_state
        super().__init__(f"Cannot retry task {task_id} (current state: {current_state.value})")
