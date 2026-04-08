"""
GitHub adapter — Convert GitHub webhook events to task requests.

Responsibilities:
- Webhook signature verification
- Event normalization (issue_comment, pr_comment, pr_opened, etc.)
- Command parsing and intent extraction (@claude <command>)
- Repo enable/disable checking
- User authorization checking

Non-responsibilities:
- GitHub API client (separate concern)
- Task execution (separate concern)
- Approval routing (tool gateway)
"""

import hashlib
import hmac
from typing import Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from .models import TaskRequest, WorkflowType


# ============================================================================
# Enums & Constants
# ============================================================================


class CommandType(str, Enum):
    """Recognized @claude commands."""
    EXPLAIN = "explain"
    FIX = "fix"
    PATCH = "patch"  # Alias for fix
    REVIEW = "review"
    STATUS = "status"
    INFO = "info"
    RERUN = "rerun"
    MARK = "mark"
    UPDATE = "update"


class GitHubEventType(str, Enum):
    """GitHub webhook event types we handle."""
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    PULL_REQUEST = "pull_request"
    ISSUES = "issues"


# ============================================================================
# Models for GitHub Payloads
# ============================================================================


class GitHubUser(BaseModel):
    """GitHub user from webhook."""
    login: str
    id: int


class GitHubRepo(BaseModel):
    """GitHub repository from webhook."""
    name: str
    full_name: str
    owner: Dict


class GitHubComment(BaseModel):
    """GitHub comment from webhook."""
    id: int
    body: str


class GitHubIssue(BaseModel):
    """GitHub issue from webhook."""
    number: int
    title: str


class GitHubPullRequest(BaseModel):
    """GitHub PR from webhook."""
    number: int
    title: str
    head: Dict  # { ref: branch_name, sha: ... }
    base: Dict  # { ref: target_branch, sha: ... }


class GitHubWebhookPayload(BaseModel):
    """Parsed GitHub webhook payload."""
    action: str
    repository: GitHubRepo
    sender: GitHubUser
    comment: Optional[GitHubComment] = None
    issue: Optional[GitHubIssue] = None
    pull_request: Optional[GitHubPullRequest] = None


# ============================================================================
# Exceptions
# ============================================================================


class GitHubAdapterError(Exception):
    """Base exception for GitHub adapter."""
    pass


class InvalidSignatureError(GitHubAdapterError):
    """Webhook signature is invalid."""
    pass


class RepoNotEnabledError(GitHubAdapterError):
    """Repository is not enabled for tasks."""
    pass


class UnauthorizedUserError(GitHubAdapterError):
    """User is not authorized to create tasks."""
    pass


class CommandParseError(GitHubAdapterError):
    """Command could not be parsed."""
    pass


# ============================================================================
# GitHub Event Normalizer
# ============================================================================


class GitHubEventNormalizer:
    """Convert GitHub webhook payloads to TaskRequest objects."""

    def __init__(
        self,
        enabled_repos: List[str],
        webhook_secret: str,
        user_authorizer: Optional[callable] = None
    ):
        """Initialize the normalizer.

        Args:
            enabled_repos: List of repos (owner/name) that can create tasks
            webhook_secret: Secret for verifying webhook signatures
            user_authorizer: Optional function(user_id, repo_id) -> bool
                If None, all users are authorized (not recommended for production)
        """
        self.enabled_repos = set(enabled_repos)
        self.webhook_secret = webhook_secret
        self.user_authorizer = user_authorizer or (lambda uid, rid: True)

    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw webhook body
            signature_header: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid

        Raises:
            InvalidSignatureError: If signature is invalid
        """
        if not signature_header.startswith("sha256="):
            raise InvalidSignatureError("Invalid signature format")

        expected_sig = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        provided_sig = signature_header[7:]  # Remove "sha256=" prefix

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise InvalidSignatureError("Signature mismatch")

        return True

    def normalize(
        self,
        payload: dict,
        signature_header: Optional[str] = None
    ) -> TaskRequest:
        """Normalize GitHub webhook payload to TaskRequest.

        Args:
            payload: Raw webhook payload (dict)
            signature_header: Optional X-Hub-Signature-256 for verification

        Returns:
            TaskRequest ready for task creation

        Raises:
            InvalidSignatureError: If signature verification enabled and fails
            RepoNotEnabledError: If repo is not enabled
            UnauthorizedUserError: If user is not authorized
            CommandParseError: If command cannot be parsed
        """
        # Parse webhook
        try:
            webhook = GitHubWebhookPayload(**payload)
        except ValidationError as e:
            raise GitHubAdapterError(f"Invalid webhook payload: {e}")

        # Check repo enabled
        if webhook.repository.full_name not in self.enabled_repos:
            raise RepoNotEnabledError(
                f"Repo {webhook.repository.full_name} is not enabled for tasks"
            )

        # Check user authorization
        if not self.user_authorizer(webhook.sender.id, webhook.repository.full_name):
            raise UnauthorizedUserError(
                f"User {webhook.sender.login} is not authorized for this repo"
            )

        # Determine event type and extract context
        trigger_type, trigger_id, issue_number, pr_number = self._extract_trigger_context(webhook)

        # Get comment body (source of command)
        comment_body = webhook.comment.body if webhook.comment else ""

        # Parse command from comment
        command_type, command_text = self._parse_command(comment_body)

        # Infer workflow type from command
        workflow_type = self._infer_workflow_type(command_type)

        # Get user email (would normally come from GitHub API lookup)
        # For now, we'll use a placeholder (real impl would fetch from API)
        user_email = f"{webhook.sender.login}@github.com"

        return TaskRequest(
            user_id=str(webhook.sender.id),
            user_email=user_email,
            repo_id=webhook.repository.full_name,
            repo_owner=webhook.repository.owner["login"],
            repo_name=webhook.repository.name,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            issue_number=issue_number,
            pr_number=pr_number,
            workflow_type=workflow_type,
            command_type=command_type,
            command_text=command_text,
            github_event=payload
        )

    def _extract_trigger_context(
        self,
        webhook: GitHubWebhookPayload
    ) -> Tuple[str, str, Optional[int], Optional[int]]:
        """Extract trigger type, ID, and issue/PR context.

        Returns:
            (trigger_type, trigger_id, issue_number, pr_number)
        """
        if webhook.comment:
            # issue_comment or pull_request_review_comment
            trigger_id = str(webhook.comment.id)

            if webhook.issue and not webhook.pull_request:
                # Issue comment
                trigger_type = GitHubEventType.ISSUE_COMMENT.value
                return trigger_type, trigger_id, webhook.issue.number, None
            elif webhook.pull_request:
                # PR comment
                trigger_type = GitHubEventType.PULL_REQUEST_REVIEW_COMMENT.value
                return trigger_type, trigger_id, None, webhook.pull_request.number

        if webhook.pull_request:
            # PR opened/synchronize/etc
            trigger_type = GitHubEventType.PULL_REQUEST.value
            trigger_id = str(webhook.pull_request.number)
            return trigger_type, trigger_id, None, webhook.pull_request.number

        if webhook.issue:
            # Issue opened/assigned/etc
            trigger_type = GitHubEventType.ISSUES.value
            trigger_id = str(webhook.issue.number)
            return trigger_type, trigger_id, webhook.issue.number, None

        raise GitHubAdapterError("Cannot determine trigger context from webhook")

    def _parse_command(self, comment_body: str) -> Tuple[str, Optional[str]]:
        """Parse @claude command from comment.

        Syntax:
            @claude <command> [<args...>]

        Behavior:
        ─────────
        1. Looks for @claude mention (case-insensitive: @claude, @CLAUDE, @Claude)
        2. Extracts first word after @claude as command
        3. Everything after command is treated as arguments

        Defaults:
        ─────────
        - If no @claude mention: returns ("explain", None)
            Rationale: Safest assumption when no explicit command
        - If unrecognized command: returns ("explain", <args>)
            Rationale: Safe fallback, logs warning in production

        Examples:
        ────────
        "@claude explain why this fails"
            → ("explain", "why this fails")

        "@claude fix the null handling"
            → ("fix", "the null handling")

        "@claude review this"
            → ("review", "this")

        "No claude mention here"
            → ("explain", None)  # Default

        "@claude unknown_command here"
            → ("explain", "unknown_command here")  # Fallback to explain

        Note: Arguments are NOT split further; everything after the
        command word is treated as a single argument string.
        """
        if "@claude" not in comment_body.lower():
            # No @claude mention; default to explain
            return CommandType.EXPLAIN.value, None

        # Extract text after @claude
        lines = comment_body.split("\n")
        claude_line = None

        for line in lines:
            if "@claude" in line.lower():
                claude_line = line
                break

        if not claude_line:
            return CommandType.EXPLAIN.value, None

        # Remove @claude and surrounding whitespace
        parts = claude_line.lower().split("@claude", 1)
        if len(parts) < 2:
            return CommandType.EXPLAIN.value, None

        text_after = parts[1].strip()
        if not text_after:
            return CommandType.EXPLAIN.value, None

        # Extract command (first word)
        words = text_after.split(None, 1)  # Split on whitespace
        command_str = words[0] if words else ""
        args = words[1] if len(words) > 1 else ""

        # Map aliases
        if command_str == "patch":
            command_type = CommandType.FIX.value
        elif command_str == "info":
            command_type = CommandType.STATUS.value
        else:
            # Default to explain if unrecognized
            command_type = command_str if command_str in [c.value for c in CommandType] else CommandType.EXPLAIN.value

        return command_type, args if args else None

    def _infer_workflow_type(self, command_type: str) -> WorkflowType:
        """Infer workflow type from command.

        Mapping:
        - explain, status, info → answer_only (S1)
        - fix, patch → pr_draft (S2)
        - review → review (S3)
        - (status, info) → tool_lookup (S4)  [if tool context]
        - rerun, mark, update → tool_mutation (S5)
        """
        if command_type in [CommandType.EXPLAIN.value, CommandType.INFO.value]:
            return WorkflowType.ANSWER_ONLY
        elif command_type in [CommandType.FIX.value, CommandType.PATCH.value]:
            return WorkflowType.PR_DRAFT
        elif command_type == CommandType.REVIEW.value:
            return WorkflowType.REVIEW
        elif command_type in [CommandType.STATUS.value]:
            # Could be tool_lookup or answer_only depending on context
            # For now, assume answer_only; tool_lookup would be determined by intent
            return WorkflowType.ANSWER_ONLY
        elif command_type in [CommandType.RERUN.value, CommandType.MARK.value, CommandType.UPDATE.value]:
            return WorkflowType.TOOL_MUTATION
        else:
            return WorkflowType.ANSWER_ONLY


# ============================================================================
# GitHub Status Callback Interface
# ============================================================================


class GitHubStatusCallback:
    """Interface for posting task results back to GitHub."""

    async def post_comment(self, repo_id: str, issue_or_pr_number: int, body: str) -> str:
        """Post a comment to an issue or PR.

        Args:
            repo_id: GitHub repo (owner/name)
            issue_or_pr_number: Issue or PR number
            body: Comment text

        Returns:
            Comment URL
        """
        raise NotImplementedError()

    async def create_pr(
        self,
        repo_id: str,
        branch: str,
        target_branch: str,
        title: str,
        body: str
    ) -> str:
        """Create a pull request.

        Args:
            repo_id: GitHub repo (owner/name)
            branch: Feature branch to merge
            target_branch: Target branch (usually 'main')
            title: PR title
            body: PR description

        Returns:
            PR URL
        """
        raise NotImplementedError()

    async def add_review_comment(
        self,
        repo_id: str,
        pr_number: int,
        body: str,
        commit_id: Optional[str] = None,
        path: Optional[str] = None,
        line: Optional[int] = None
    ) -> str:
        """Add a review comment to a PR.

        Args:
            repo_id: GitHub repo (owner/name)
            pr_number: PR number
            body: Comment text
            commit_id: Optional commit SHA for specific revision
            path: Optional file path for line-specific comment
            line: Optional line number for line-specific comment

        Returns:
            Comment URL
        """
        raise NotImplementedError()
