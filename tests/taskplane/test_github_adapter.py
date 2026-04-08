"""
Tests for GitHub adapter — event normalization and command parsing.

Tests cover:
- Signature verification
- Event normalization
- Command parsing
- Workflow type inference
- Authorization checks
"""

import hashlib
import hmac
import json
import pytest

from source.taskplane.github_adapter import (
    CommandType,
    GitHubEventNormalizer,
    GitHubEventType,
    InvalidSignatureError,
    RepoNotEnabledError,
    UnauthorizedUserError,
    CommandParseError,
)
from source.taskplane.models import WorkflowType


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def webhook_secret():
    """Shared webhook secret."""
    return "test_secret_123"


@pytest.fixture
def normalizer(webhook_secret):
    """Create a normalizer with test config."""
    return GitHubEventNormalizer(
        enabled_repos=["org/repo", "org/enabled-repo"],
        webhook_secret=webhook_secret
    )


@pytest.fixture
def basic_issue_comment_payload():
    """Basic issue comment webhook payload."""
    return {
        "action": "created",
        "repository": {
            "name": "repo",
            "full_name": "org/repo",
            "owner": {"login": "org"}
        },
        "sender": {
            "login": "engineer",
            "id": 123
        },
        "comment": {
            "id": 999,
            "body": "@claude explain this"
        },
        "issue": {
            "number": 42,
            "title": "Something is broken"
        }
    }


@pytest.fixture
def basic_pr_comment_payload():
    """Basic PR comment webhook payload."""
    return {
        "action": "created",
        "repository": {
            "name": "repo",
            "full_name": "org/repo",
            "owner": {"login": "org"}
        },
        "sender": {
            "login": "engineer",
            "id": 123
        },
        "comment": {
            "id": 999,
            "body": "@claude fix the null handling"
        },
        "pull_request": {
            "number": 156,
            "title": "Fix null handling",
            "head": {"ref": "feature/fix", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"}
        }
    }


def create_signature(payload_bytes: bytes, secret: str) -> str:
    """Create a valid GitHub webhook signature."""
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ============================================================================
# Signature Verification Tests
# ============================================================================


class TestSignatureVerification:
    """Tests for webhook signature verification."""

    def test_valid_signature(self, normalizer, basic_issue_comment_payload, webhook_secret):
        """Valid signature is accepted."""
        payload_bytes = json.dumps(basic_issue_comment_payload).encode()
        signature = create_signature(payload_bytes, webhook_secret)

        # Should not raise
        normalizer.verify_signature(payload_bytes, signature)

    def test_invalid_signature(self, normalizer, basic_issue_comment_payload, webhook_secret):
        """Invalid signature is rejected."""
        payload_bytes = json.dumps(basic_issue_comment_payload).encode()
        signature = "sha256=invalid_signature"

        with pytest.raises(InvalidSignatureError):
            normalizer.verify_signature(payload_bytes, signature)

    def test_signature_format_error(self, normalizer):
        """Invalid signature format is rejected."""
        with pytest.raises(InvalidSignatureError, match="Invalid signature format"):
            normalizer.verify_signature(b"test", "invalid_format")

    def test_modified_payload_invalid_signature(self, normalizer, basic_issue_comment_payload, webhook_secret):
        """Signature fails if payload is modified."""
        payload_bytes = json.dumps(basic_issue_comment_payload).encode()
        signature = create_signature(payload_bytes, webhook_secret)

        # Modify payload
        modified_payload = payload_bytes + b"extra"

        with pytest.raises(InvalidSignatureError):
            normalizer.verify_signature(modified_payload, signature)


# ============================================================================
# Repo Enabled Checks
# ============================================================================


class TestRepoEnabledChecks:
    """Tests for repo enable/disable checks."""

    def test_enabled_repo_accepted(self, normalizer, basic_issue_comment_payload):
        """Enabled repos are accepted."""
        # Should not raise
        result = normalizer.normalize(basic_issue_comment_payload)
        assert result.repo_id == "org/repo"

    def test_disabled_repo_rejected(self, normalizer, basic_issue_comment_payload):
        """Disabled repos are rejected."""
        basic_issue_comment_payload["repository"]["full_name"] = "org/disabled-repo"

        with pytest.raises(RepoNotEnabledError):
            normalizer.normalize(basic_issue_comment_payload)

    def test_multiple_enabled_repos(self, webhook_secret):
        """Normalizer supports multiple enabled repos."""
        normalizer = GitHubEventNormalizer(
            enabled_repos=["org/repo1", "org/repo2", "org/repo3"],
            webhook_secret=webhook_secret
        )

        payload = {
            "action": "created",
            "repository": {
                "name": "repo2",
                "full_name": "org/repo2",
                "owner": {"login": "org"}
            },
            "sender": {"login": "user", "id": 1},
            "comment": {"id": 1, "body": "@claude explain"},
            "issue": {"number": 1, "title": "Issue"}
        }

        result = normalizer.normalize(payload)
        assert result.repo_id == "org/repo2"


# ============================================================================
# Command Parsing Tests
# ============================================================================


class TestCommandParsing:
    """Tests for @claude command parsing."""

    def test_explain_command(self, normalizer, basic_issue_comment_payload):
        """@claude explain is parsed correctly."""
        basic_issue_comment_payload["comment"]["body"] = "@claude explain why this fails"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.EXPLAIN.value
        assert result.command_text == "why this fails"

    def test_fix_command(self, normalizer, basic_issue_comment_payload):
        """@claude fix is parsed correctly."""
        basic_issue_comment_payload["comment"]["body"] = "@claude fix the null handling"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.FIX.value
        assert result.command_text == "the null handling"

    def test_patch_alias(self, normalizer, basic_issue_comment_payload):
        """@claude patch is aliased to fix."""
        basic_issue_comment_payload["comment"]["body"] = "@claude patch utils/cache.ts"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.FIX.value
        assert result.command_text == "utils/cache.ts"

    def test_review_command(self, normalizer, basic_issue_comment_payload):
        """@claude review is parsed correctly."""
        basic_issue_comment_payload["comment"]["body"] = "@claude review this for regression risk"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.REVIEW.value
        assert result.command_text == "this for regression risk"

    def test_status_command(self, normalizer, basic_issue_comment_payload):
        """@claude status is parsed correctly."""
        basic_issue_comment_payload["comment"]["body"] = "@claude status service-a in staging"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.STATUS.value
        assert result.command_text == "service-a in staging"

    def test_no_command_defaults_to_explain(self, normalizer, basic_issue_comment_payload):
        """No @claude mention defaults to explain."""
        basic_issue_comment_payload["comment"]["body"] = "This is broken"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.EXPLAIN.value
        assert result.command_text is None

    def test_command_case_insensitive(self, normalizer, basic_issue_comment_payload):
        """@Claude and @CLAUDE are both recognized."""
        basic_issue_comment_payload["comment"]["body"] = "@CLAUDE EXPLAIN this issue"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.EXPLAIN.value
        assert result.command_text == "this issue"

    def test_multiline_comment_with_command(self, normalizer, basic_issue_comment_payload):
        """Command in multiline comment is extracted."""
        basic_issue_comment_payload["comment"]["body"] = (
            "Some context\n"
            "@claude fix the bug\n"
            "More context"
        )

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.FIX.value
        assert result.command_text == "the bug"

    def test_command_without_args(self, normalizer, basic_issue_comment_payload):
        """Command without additional args is handled."""
        basic_issue_comment_payload["comment"]["body"] = "@claude review"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.command_type == CommandType.REVIEW.value
        assert result.command_text is None


# ============================================================================
# Workflow Type Inference Tests
# ============================================================================


class TestWorkflowTypeInference:
    """Tests for inferring workflow type from command."""

    def test_explain_to_answer_only(self, normalizer, basic_issue_comment_payload):
        """explain command → answer_only workflow."""
        basic_issue_comment_payload["comment"]["body"] = "@claude explain this"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.workflow_type == WorkflowType.ANSWER_ONLY

    def test_fix_to_pr_draft(self, normalizer, basic_issue_comment_payload):
        """fix command → pr_draft workflow."""
        basic_issue_comment_payload["comment"]["body"] = "@claude fix the issue"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.workflow_type == WorkflowType.PR_DRAFT

    def test_review_to_review_workflow(self, normalizer, basic_issue_comment_payload):
        """review command → review workflow."""
        basic_issue_comment_payload["comment"]["body"] = "@claude review this"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.workflow_type == WorkflowType.REVIEW

    def test_status_to_answer_only(self, normalizer, basic_issue_comment_payload):
        """status command → answer_only workflow (default)."""
        basic_issue_comment_payload["comment"]["body"] = "@claude status service-a"

        result = normalizer.normalize(basic_issue_comment_payload)

        # Default to answer_only; tool_lookup would be determined by intent
        assert result.workflow_type in [WorkflowType.ANSWER_ONLY, WorkflowType.TOOL_LOOKUP]

    def test_mutation_to_tool_mutation(self, normalizer, basic_issue_comment_payload):
        """rerun/mark/update commands → tool_mutation workflow."""
        basic_issue_comment_payload["comment"]["body"] = "@claude rerun the deploy check"

        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.workflow_type == WorkflowType.TOOL_MUTATION


# ============================================================================
# Event Type Extraction Tests
# ============================================================================


class TestEventTypeExtraction:
    """Tests for extracting trigger context."""

    def test_issue_comment_event(self, normalizer, basic_issue_comment_payload):
        """Issue comment event is identified."""
        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.trigger_type == GitHubEventType.ISSUE_COMMENT.value
        assert result.issue_number == 42
        assert result.pr_number is None

    def test_pr_comment_event(self, normalizer, basic_pr_comment_payload):
        """PR comment event is identified."""
        result = normalizer.normalize(basic_pr_comment_payload)

        assert result.trigger_type == GitHubEventType.PULL_REQUEST_REVIEW_COMMENT.value
        assert result.pr_number == 156
        assert result.issue_number is None

    def test_trigger_id_is_comment_id(self, normalizer, basic_issue_comment_payload):
        """Trigger ID is the comment ID for comment events."""
        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.trigger_id == "999"


# ============================================================================
# User Authorization Tests
# ============================================================================


class TestUserAuthorization:
    """Tests for user authorization checks."""

    def test_unauthorized_user_rejected(self, webhook_secret):
        """Unauthorized users are rejected."""
        def authorizer(user_id, repo_id):
            # Only user 123 is authorized
            return user_id == 123

        normalizer = GitHubEventNormalizer(
            enabled_repos=["org/repo"],
            webhook_secret=webhook_secret,
            user_authorizer=authorizer
        )

        payload = {
            "action": "created",
            "repository": {"name": "repo", "full_name": "org/repo", "owner": {"login": "org"}},
            "sender": {"login": "unauthorized", "id": 456},
            "comment": {"id": 1, "body": "@claude explain"},
            "issue": {"number": 1, "title": "Issue"}
        }

        with pytest.raises(UnauthorizedUserError):
            normalizer.normalize(payload)

    def test_authorized_user_accepted(self, webhook_secret):
        """Authorized users are accepted."""
        def authorizer(user_id, repo_id):
            return user_id == 123

        normalizer = GitHubEventNormalizer(
            enabled_repos=["org/repo"],
            webhook_secret=webhook_secret,
            user_authorizer=authorizer
        )

        payload = {
            "action": "created",
            "repository": {"name": "repo", "full_name": "org/repo", "owner": {"login": "org"}},
            "sender": {"login": "engineer", "id": 123},
            "comment": {"id": 1, "body": "@claude explain"},
            "issue": {"number": 1, "title": "Issue"}
        }

        result = normalizer.normalize(payload)
        assert result.user_id == "123"


# ============================================================================
# Full Integration Tests
# ============================================================================


class TestFullNormalization:
    """Integration tests for complete event normalization."""

    def test_issue_comment_to_task_request(self, normalizer, basic_issue_comment_payload):
        """Issue comment webhook → TaskRequest."""
        result = normalizer.normalize(basic_issue_comment_payload)

        assert result.user_id == "123"
        assert result.repo_id == "org/repo"
        assert result.repo_owner == "org"
        assert result.repo_name == "repo"
        assert result.workflow_type == WorkflowType.ANSWER_ONLY
        assert result.command_type == CommandType.EXPLAIN.value
        assert result.trigger_type == GitHubEventType.ISSUE_COMMENT.value
        assert result.issue_number == 42
        assert result.github_event == basic_issue_comment_payload

    def test_pr_comment_to_task_request(self, normalizer, basic_pr_comment_payload):
        """PR comment webhook → TaskRequest."""
        result = normalizer.normalize(basic_pr_comment_payload)

        assert result.user_id == "123"
        assert result.repo_id == "org/repo"
        assert result.workflow_type == WorkflowType.PR_DRAFT
        assert result.command_type == CommandType.FIX.value
        assert result.trigger_type == GitHubEventType.PULL_REQUEST_REVIEW_COMMENT.value
        assert result.pr_number == 156
        assert result.github_event == basic_pr_comment_payload

    def test_user_email_extracted(self, normalizer, basic_issue_comment_payload):
        """User email is included in TaskRequest."""
        result = normalizer.normalize(basic_issue_comment_payload)

        # Should generate email from login
        assert "engineer" in result.user_email
        assert "@" in result.user_email


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
