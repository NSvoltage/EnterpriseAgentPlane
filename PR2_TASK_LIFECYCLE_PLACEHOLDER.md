# Task Lifecycle — State Machine and Artifact Model

**Status:** Placeholder for PR 2 (detailed implementation in PR 3)

This document outlines the task lifecycle contract that will be implemented in PR 3.

## Task States

```
Created
  ↓
Queued
  ↓
Running → Waiting for Approval → (Approved → Running | Denied → Failed)
  ↓
Completed  |  Failed  |  Canceled
```

### State Definitions

- **Queued**: Task is created but not yet started (awaiting worker pickup)
- **Running**: Task is actively executing
- **Waiting for Approval**: Task is paused, waiting for human approval (mutations only)
- **Completed**: Task finished successfully
- **Failed**: Task encountered an error
- **Canceled**: Task was canceled by user or admin

## Task Model (Pydantic)

See `PR3` for detailed implementation.

Basic shape:
```python
class Task(BaseModel):
    id: str  # UUID
    user_id: str
    repo_id: str
    workflow_type: str
    state: TaskState
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    artifacts: List[TaskArtifact]
```

## Artifacts

Tasks produce artifacts:
- GitHub comments
- PR URLs
- Validation reports
- Tool invocation logs
- Approval records

All artifacts are stored and linked to task_id for auditability.

---

**Note:** Full implementation spec is in PR 3.
