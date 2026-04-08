"""
Comprehensive tests for taskplane.models module.

Tests cover:
- Model creation and validation
- Enum values
- Serialization/deserialization
- State transitions (at model level)
- Artifact management
"""

import json
from datetime import datetime
import pytest

from source.taskplane.models import (
    Task,
    TaskArtifact,
    TaskArtifactType,
    TaskCreationError,
    TaskFilter,
    TaskRequest,
    TaskResult,
    TaskState,
    TaskUpdate,
    WorkflowType,
)


# ============================================================================
# TaskState Enum Tests
# ============================================================================


class TestTaskState:
    """Tests for TaskState enum."""

    def test_task_state_values(self):
        """TaskState has expected values."""
        assert TaskState.QUEUED.value == "queued"
        assert TaskState.RUNNING.value == "running"
        assert TaskState.WAITING_FOR_APPROVAL.value == "waiting_for_approval"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELED.value == "canceled"

    def test_task_state_count(self):
        """TaskState has exactly 6 states."""
        states = list(TaskState)
        assert len(states) == 6

    def test_task_state_string_conversion(self):
        """TaskState can be converted to/from string."""
        state_str = "completed"
        state = TaskState(state_str)
        assert state == TaskState.COMPLETED
        assert str(state.value) == state_str


class TestWorkflowType:
    """Tests for WorkflowType enum."""

    def test_workflow_types_exist(self):
        """All workflow types exist."""
        assert WorkflowType.ANSWER_ONLY
        assert WorkflowType.PR_DRAFT
        assert WorkflowType.REVIEW
        assert WorkflowType.TOOL_LOOKUP
        assert WorkflowType.TOOL_MUTATION

    def test_workflow_type_values(self):
        """WorkflowType values are correct."""
        assert WorkflowType.ANSWER_ONLY.value == "answer_only"
        assert WorkflowType.PR_DRAFT.value == "pr_draft"
        assert WorkflowType.REVIEW.value == "review"


# ============================================================================
# TaskArtifact Tests
# ============================================================================


class TestTaskArtifact:
    """Tests for TaskArtifact model."""

    def test_artifact_creation_minimal(self):
        """TaskArtifact can be created with minimal fields."""
        artifact = TaskArtifact(
            task_id="task_123",
            artifact_type=TaskArtifactType.GITHUB_COMMENT,
            content_url="https://github.com/org/repo/issues/42#issuecomment-999",
        )
        assert artifact.task_id == "task_123"
        assert artifact.artifact_type == TaskArtifactType.GITHUB_COMMENT
        assert artifact.content_url.startswith("https://")
        assert artifact.id.startswith("artifact_")
        assert artifact.created_at is not None

    def test_artifact_creation_with_metadata(self):
        """TaskArtifact can include metadata."""
        artifact = TaskArtifact(
            task_id="task_123",
            artifact_type=TaskArtifactType.VALIDATION_REPORT,
            content_url="s3://bucket/report.json",
            metadata={"check_count": 3, "passed": 2}
        )
        assert artifact.metadata["check_count"] == 3
        assert artifact.metadata["passed"] == 2

    def test_artifact_serialization(self):
        """TaskArtifact serializes to JSON."""
        artifact = TaskArtifact(
            task_id="task_123",
            artifact_type=TaskArtifactType.GITHUB_COMMENT,
            content_url="https://example.com/comment",
        )
        json_str = artifact.model_dump_json()
        assert "task_123" in json_str
        assert "github_comment" in json_str

    def test_artifact_deserialization(self):
        """TaskArtifact deserializes from JSON."""
        json_str = '''{
            "task_id": "task_123",
            "artifact_type": "github_comment",
            "content_url": "https://example.com/comment"
        }'''
        artifact = TaskArtifact.model_validate_json(json_str)
        assert artifact.task_id == "task_123"
        assert artifact.artifact_type == TaskArtifactType.GITHUB_COMMENT


# ============================================================================
# Task Tests
# ============================================================================


class TestTask:
    """Tests for Task model."""

    @pytest.fixture
    def minimal_task_data(self):
        """Minimal task creation data."""
        return {
            "user_id": "github_user_123",
            "user_email": "user@example.com",
            "repo_id": "org/repo",
            "repo_owner": "org",
            "repo_name": "repo",
            "workflow_type": WorkflowType.ANSWER_ONLY,
            "command_type": "explain",
            "trigger_type": "issue_comment",
            "trigger_id": "comment_999",
            "request_body": {"action": "created"},
        }

    def test_task_creation_minimal(self, minimal_task_data):
        """Task can be created with minimal fields."""
        task = Task(**minimal_task_data)
        assert task.user_id == "github_user_123"
        assert task.state == TaskState.QUEUED
        assert task.id.startswith("task_")
        assert task.created_at is not None
        assert len(task.artifacts) == 0

    def test_task_creation_full(self, minimal_task_data):
        """Task can be created with all fields."""
        minimal_task_data.update({
            "issue_number": 42,
            "pr_number": None,
            "approval_required": True,
            "metadata": {"custom": "value"}
        })
        task = Task(**minimal_task_data)
        assert task.issue_number == 42
        assert task.approval_required is True
        assert task.metadata["custom"] == "value"

    def test_task_with_artifacts(self, minimal_task_data):
        """Task can have artifacts."""
        artifact = TaskArtifact(
            task_id="task_123",
            artifact_type=TaskArtifactType.GITHUB_COMMENT,
            content_url="https://github.com/org/repo/issues/42#issuecomment-999",
        )
        minimal_task_data["artifacts"] = [artifact]
        task = Task(**minimal_task_data)
        assert len(task.artifacts) == 1
        assert task.artifacts[0].artifact_type == TaskArtifactType.GITHUB_COMMENT

    def test_task_serialization_round_trip(self, minimal_task_data):
        """Task serializes and deserializes losslessly."""
        task1 = Task(**minimal_task_data)
        json_str = task1.model_dump_json()
        task2 = Task.model_validate_json(json_str)

        assert task2.id == task1.id
        assert task2.user_id == task1.user_id
        assert task2.workflow_type == task1.workflow_type
        assert task2.state == task1.state

    def test_task_state_defaults(self, minimal_task_data):
        """Task state defaults to QUEUED."""
        task = Task(**minimal_task_data)
        assert task.state == TaskState.QUEUED
        assert task.started_at is None
        assert task.completed_at is None

    def test_task_json_deterministic(self, minimal_task_data):
        """Task JSON is deterministic (for audit trail)."""
        task1 = Task(**minimal_task_data)
        task2 = Task(**minimal_task_data)

        # Same data produces same JSON structure
        json1 = task1.model_dump_json()
        json2 = task2.model_dump_json()

        # Parse and compare structure (not exact string match, since IDs differ)
        data1 = json.loads(json1)
        data2 = json.loads(json2)

        # Core data should be identical (IDs will differ)
        assert data1["user_id"] == data2["user_id"]
        assert data1["repo_id"] == data2["repo_id"]
        assert data1["state"] == data2["state"]

    def test_task_preserves_github_event(self, minimal_task_data):
        """Task preserves original GitHub event for audit/replay."""
        github_event = {
            "action": "created",
            "comment": {"id": 999, "body": "@claude explain this"},
            "issue": {"number": 42},
            "repository": {"full_name": "org/repo"},
            "sender": {"login": "user"}
        }
        minimal_task_data["request_body"] = github_event
        task = Task(**minimal_task_data)

        assert task.request_body["action"] == "created"
        assert task.request_body["comment"]["id"] == 999


# ============================================================================
# TaskRequest Tests
# ============================================================================


class TestTaskRequest:
    """Tests for TaskRequest model."""

    def test_task_request_creation(self):
        """TaskRequest can be created."""
        request = TaskRequest(
            user_id="user_123",
            user_email="user@example.com",
            repo_id="org/repo",
            repo_owner="org",
            repo_name="repo",
            trigger_type="issue_comment",
            trigger_id="comment_999",
            workflow_type=WorkflowType.ANSWER_ONLY,
            command_type="explain",
            github_event={"action": "created"}
        )
        assert request.user_id == "user_123"
        assert request.workflow_type == WorkflowType.ANSWER_ONLY

    def test_task_request_from_task(self):
        """TaskRequest can be extracted from Task."""
        task = Task(
            user_id="user_123",
            user_email="user@example.com",
            repo_id="org/repo",
            repo_owner="org",
            repo_name="repo",
            workflow_type=WorkflowType.ANSWER_ONLY,
            command_type="explain",
            trigger_type="issue_comment",
            trigger_id="comment_999",
            request_body={"action": "created"}
        )
        # Can reconstruct request-like data from task
        assert task.user_id == "user_123"
        assert task.request_body["action"] == "created"


# ============================================================================
# TaskUpdate Tests
# ============================================================================


class TestTaskUpdate:
    """Tests for TaskUpdate model."""

    def test_partial_update(self):
        """TaskUpdate allows partial updates."""
        update = TaskUpdate(
            state=TaskState.RUNNING,
            started_at=datetime.utcnow()
        )
        assert update.state == TaskState.RUNNING
        assert update.started_at is not None
        assert update.completed_at is None

    def test_update_with_completion(self):
        """TaskUpdate can mark completion."""
        update = TaskUpdate(
            state=TaskState.COMPLETED,
            completed_at=datetime.utcnow()
        )
        assert update.state == TaskState.COMPLETED
        assert update.completed_at is not None

    def test_update_with_error(self):
        """TaskUpdate can record errors."""
        update = TaskUpdate(
            state=TaskState.FAILED,
            error_message="Task timed out after 30 seconds"
        )
        assert update.state == TaskState.FAILED
        assert "timed out" in update.error_message


# ============================================================================
# TaskFilter Tests
# ============================================================================


class TestTaskFilter:
    """Tests for TaskFilter model."""

    def test_filter_minimal(self):
        """TaskFilter can be minimal (no filters)."""
        filter_obj = TaskFilter()
        assert filter_obj.limit == 50
        assert filter_obj.offset == 0

    def test_filter_by_repo(self):
        """TaskFilter can filter by repo."""
        filter_obj = TaskFilter(repo_id="org/repo", limit=10)
        assert filter_obj.repo_id == "org/repo"
        assert filter_obj.limit == 10

    def test_filter_by_state(self):
        """TaskFilter can filter by state."""
        filter_obj = TaskFilter(state=TaskState.COMPLETED)
        assert filter_obj.state == TaskState.COMPLETED

    def test_filter_limit_constraints(self):
        """TaskFilter enforces limit constraints."""
        with pytest.raises(ValueError):
            # limit must be >= 1
            TaskFilter(limit=0)

        with pytest.raises(ValueError):
            # limit must be <= 1000
            TaskFilter(limit=2000)


# ============================================================================
# TaskResult Tests
# ============================================================================


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_result_creation(self):
        """TaskResult can be created."""
        result = TaskResult(
            task_id="task_123",
            state=TaskState.COMPLETED,
            output_summary="Task completed successfully",
            duration_seconds=90.0
        )
        assert result.task_id == "task_123"
        assert result.state == TaskState.COMPLETED
        assert result.duration_seconds == 90.0

    def test_result_with_artifacts(self):
        """TaskResult can include artifacts."""
        artifact = TaskArtifact(
            task_id="task_123",
            artifact_type=TaskArtifactType.GITHUB_COMMENT,
            content_url="https://github.com/org/repo/issues/42#issuecomment-999"
        )
        result = TaskResult(
            task_id="task_123",
            state=TaskState.COMPLETED,
            output_summary="Explained the issue",
            artifacts=[artifact],
            duration_seconds=45.0
        )
        assert len(result.artifacts) == 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests across models."""

    def test_task_lifecycle_happy_path(self):
        """Test a complete task lifecycle."""
        # 1. Create task (in QUEUED state)
        task = Task(
            user_id="user_123",
            user_email="user@example.com",
            repo_id="org/repo",
            repo_owner="org",
            repo_name="repo",
            workflow_type=WorkflowType.ANSWER_ONLY,
            command_type="explain",
            trigger_type="issue_comment",
            trigger_id="comment_999",
            request_body={"action": "created"}
        )
        task_id = task.id
        assert task.state == TaskState.QUEUED

        # 2. Add artifact (would be done by execution layer)
        artifact = TaskArtifact(
            task_id=task_id,
            artifact_type=TaskArtifactType.GITHUB_COMMENT,
            content_url="https://github.com/org/repo/issues/42#issuecomment-999"
        )
        task.artifacts.append(artifact)

        # 3. Serialize for storage
        json_str = task.model_dump_json()

        # 4. Deserialize from storage
        task_restored = Task.model_validate_json(json_str)
        assert task_restored.id == task_id
        assert len(task_restored.artifacts) == 1
        assert task_restored.artifacts[0].artifact_type == TaskArtifactType.GITHUB_COMMENT

    def test_task_request_to_task_conversion(self):
        """Test converting TaskRequest to Task."""
        request = TaskRequest(
            user_id="user_123",
            user_email="user@example.com",
            repo_id="org/repo",
            repo_owner="org",
            repo_name="repo",
            trigger_type="issue_comment",
            trigger_id="comment_999",
            workflow_type=WorkflowType.PR_DRAFT,
            command_type="fix",
            command_text="fix the null handling",
            github_event={"action": "created", "comment": {"id": 999}}
        )

        # TaskManager would convert request to task
        task = Task(
            user_id=request.user_id,
            user_email=request.user_email,
            repo_id=request.repo_id,
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
            workflow_type=request.workflow_type,
            command_type=request.command_type,
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            request_body=request.github_event
        )

        assert task.user_id == request.user_id
        assert task.workflow_type == request.workflow_type
        assert task.request_body == request.github_event


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
