# GitHub Workflows — Event to Task Mapping

How GitHub events are normalized to task requests and routed to execution workflows.

## GitHub Event Types Supported

| GitHub Event | Trigger | Task Workflow | Scenario |
|---|---|---|---|
| `issue_comment` with `@claude` | User comments `@claude ...` on issue | Varies (see command parsing) | S1, S2, S3, S4, S5 |
| `pull_request_review_comment` with `@claude` | User comments `@claude ...` on PR | Varies | S1, S2, S3, S4 |
| `pull_request` (opened) | PR opened (if automation enabled) | review | S3 |
| `issues` (assigned) | User assigned to issue (if automation enabled) | Varies | S2 (future) |

---

## Event Normalization

All GitHub events are normalized to a common `GitHubTaskRequest` model:

```python
class GitHubTaskRequest(BaseModel):
    # Event metadata
    event_type: Literal["issue_comment", "pr_comment", "pr_opened", "issue_assigned"]
    event_id: str  # Unique GitHub event ID
    
    # User information
    user_login: str  # GitHub username
    user_id: int  # GitHub user ID
    user_email: str  # (from GitHub API lookup or OIDC token)
    
    # Repository information
    repo_owner: str  # GitHub org/username
    repo_name: str  # Repository name
    repo_full_name: str  # owner/repo
    
    # Context (issue or PR)
    issue_number: Optional[int]  # Issue # if on an issue
    pr_number: Optional[int]  # PR # if on a PR
    comment_id: Optional[int]  # Comment ID if commenting
    comment_body: str  # The text of the comment or PR body
    
    # Branch information
    target_branch: str  # Base branch (usually 'main' or 'master')
    current_branch: Optional[str]  # Current branch (for PR context)
    
    # Parsed intent
    mentioned_claude: bool  # Did the comment mention @claude?
    command_text: Optional[str]  # The command after @claude (e.g., "explain why service X fails")
    command_type: Optional[str]  # Parsed command type (e.g., "explain", "fix", "review")
    
    # GitHub metadata
    created_at: datetime
    updated_at: datetime
```

### Validation Rules During Normalization

1. **Signature Verification**
   - GitHub webhook signature must match (HMAC-SHA256)
   - Reject if signature invalid

2. **Repo Enabled Check**
   - Is `repo_full_name` in the operator-configured enable list?
   - Reject if not enabled

3. **User Authorization**
   - Does user have permission to trigger tasks in this repo?
   - Check: GitHub collaborators, branch permissions
   - Use GitHub API to verify

4. **Command Parsing**
   - Extract text after `@claude`
   - Parse first word as command (explain, fix, review, status, etc.)
   - Extract parameters if present

---

## Command Parsing & Routing

### Command: `explain` (S1)

**Syntax:**
```
@claude explain <what>
@claude explain why <description>
@claude explain <file or service>
```

**Examples:**
```
@claude explain why this service fails with config X

@claude explain the null handling in utils/validation.ts

@claude explain the recent regression in deploy metrics
```

**Normalized Intent:**
- `command_type: "explain"`
- `workflow_type: "answer_only"`
- `parameters: { subject: "<what>" }`

**Routed to:** Answer-only execution (S1)

---

### Command: `fix` or `patch` (S2)

**Syntax:**
```
@claude fix <what>
@claude fix <what> and open a PR
@claude patch <file>
```

**Examples:**
```
@claude fix the null handling in services/payment.ts and open a PR

@claude fix the race condition in utils/cache.ts

@claude patch the bug in validators/schema.ts
```

**Normalized Intent:**
- `command_type: "fix"`
- `workflow_type: "pr_draft"`
- `parameters: { target: "<file or description>", open_pr: true }`

**Routed to:** PR draft execution (S2)

---

### Command: `review` (S3)

**Syntax:**
```
@claude review this [for <what>]
@claude review [this PR] [for <concerns>]
```

**Examples:**
```
@claude review this for regression risk

@claude review this PR for missing tests

@claude review for security issues
```

**Normalized Intent:**
- `command_type: "review"`
- `workflow_type: "review"`
- `parameters: { review_type: "<concerns>" }`

**Routed to:** PR review execution (S3)

---

### Command: `status` or `info` (S4, Tool Lookup)

**Syntax:**
```
@claude status <service> [in <environment>]
@claude info <resource>
@claude what is <thing>
```

**Examples:**
```
@claude status service-a in staging

@claude info the latest deploy for backend-api

@claude what is the current error rate for frontend-web
```

**Normalized Intent:**
- `command_type: "status"` or `"info"`
- `workflow_type: "tool_lookup"`
- `parameters: { target: "<service>", environment: "<env>" }`

**Routed to:** Tool gateway (S4)

---

### Command: `rerun`, `mark`, `update` (S5, Mutations)

**Syntax:**
```
@claude rerun <check or deploy>
@claude mark <thing> as <status>
@claude update <resource> with <change>
```

**Examples:**
```
@claude rerun the deploy check for service-a

@claude mark incident INC-123 as resolved

@claude update the deployment tags
```

**Normalized Intent:**
- `command_type: "rerun"` / `"mark"` / `"update"`
- `workflow_type: "tool_mutation"`
- `parameters: { operation: "<what>", target: "<resource>" }`

**Routed to:** Tool gateway with approval gate (S5)

---

### Unrecognized Command

If the command is not recognized or `@claude` is mentioned without a clear command:

- Default: "explain" (assume user wants explanation)
- Log: unrecognized pattern
- Post: "Didn't understand the command. Try: @claude explain <what>, @claude fix <what>, @claude review this, etc."

---

## Workflow-to-Execution Mapping

### Workflow: `answer_only` (S1)

**Trigger:**
- `command_type: explain`

**Execution:**
1. Fetch repo context (files, recent commits)
2. Optionally query tools (read-only only)
3. Invoke Claude Code with prompt
4. Summarize response
5. Post comment with answer

**Artifacts:**
- GitHub comment URL

**Approval Required:** No

**Tool Access:** Read-only only

**Time Estimate:** 30-120 seconds

---

### Workflow: `pr_draft` (S2)

**Trigger:**
- `command_type: fix`

**Execution:**
1. Create task branch (from target_branch)
2. Fetch repo context
3. Invoke Claude Code with fix prompt
4. Apply changes to branch
5. Commit changes
6. Create PR (in draft state)
7. Run validation (lint, test, security)
8. Post comment with PR link and validation results

**Artifacts:**
- GitHub PR URL
- Validation reports (S3 links)

**Approval Required:** No (but PR requires review before merge)

**Tool Access:** Repo write only

**Time Estimate:** 2-10 minutes

---

### Workflow: `review` (S3)

**Trigger:**
- `command_type: review`
- Triggered on PR comment or PR open event (if configured)

**Execution:**
1. Fetch PR diff and context
2. Analyze for regression risk, missing tests, issues
3. Summarize findings
4. Post review comment (or report comment)

**Artifacts:**
- GitHub review comment or PR comment URL

**Approval Required:** No

**Tool Access:** Repo read only

**Time Estimate:** 1-5 minutes

---

### Workflow: `tool_lookup` (S4)

**Trigger:**
- `command_type: status` or `info`

**Execution:**
1. Parse intent (what tool, what parameters)
2. Tool gateway: authorize user for tool
3. Invoke tool (read-only)
4. Summarize response
5. Post comment with result

**Artifacts:**
- GitHub comment URL

**Approval Required:** No

**Tool Access:** Enterprise Tool Gateway (curated read-only)

**Time Estimate:** 10-60 seconds

---

### Workflow: `tool_mutation` (S5)

**Trigger:**
- `command_type: rerun`, `mark`, `update`, etc.

**Execution:**
1. Parse intent (what tool, what operation, parameters)
2. Tool gateway: check authorization
3. Check: does tool require approval? Yes → goto Approval Phase
4. Approval Phase:
   - Generate approval request
   - Route to approval target (GitHub, admin portal, etc.)
   - Wait for approval
5. Invoke tool (with mutation capability)
6. Summarize result
7. Post comment with result and approval/execution details

**Artifacts:**
- GitHub comment URL
- Approval record (in observability system)

**Approval Required:** Yes (by tool configuration)

**Tool Access:** Enterprise Tool Gateway (curated, approval-gated)

**Time Estimate:** Seconds to hours (depends on approval wait time)

---

## Approval Routing (S5)

When a task requires approval (mutation tool):

**Approval Request Contains:**
- Task ID
- User requesting (GitHub user)
- Operation (what they want to do)
- Tool involved
- Estimated impact

**Approval Routes (v1):**
- **GitHub comment reply** — Approval reviewer responds in thread
- (v1.5+: Admin portal, Slack, email)

**Approval Decision:**
- `approved` — Proceed with execution
- `denied` — Cancel task, inform user in GitHub
- `timeout` — If not approved in 24h, cancel task

**Approval Audit:**
- Who approved
- When
- Via what mechanism
- Logged to CloudWatch + CloudTrail

---

## Error Handling

### Common Errors During Normalization

1. **Signature Invalid**
   - Reject: log warning
   - Return: 403 Forbidden

2. **Repo Not Enabled**
   - Reject: don't create task
   - Return: 202 Accepted (webhook is processed)
   - Action: post comment "This repo is not enabled for tasks. Contact admin."

3. **User Not Authorized**
   - Reject: don't create task
   - Return: 202 Accepted
   - Action: post comment "You don't have permission to create tasks in this repo."

4. **Command Not Recognized**
   - Create task with `workflow_type: answer_only` (default explain)
   - Post comment: "Command not recognized. Try: explain, fix, review, status, etc."

5. **Multiple @claude Mentions**
   - Take the first one
   - Ignore others

---

## Testing

### Mock GitHub Payloads for Testing

**S1: explain command**
```json
{
  "action": "created",
  "comment": {
    "id": 123456,
    "body": "@claude explain why this service fails with config X"
  },
  "issue": {
    "number": 42,
    "title": "Deployment failing in staging"
  },
  "repository": {
    "name": "backend-api",
    "full_name": "myorg/backend-api"
  },
  "sender": {
    "login": "engineer-alice",
    "id": 789
  }
}
```

**S2: fix command**
```json
{
  "action": "created",
  "comment": {
    "id": 123457,
    "body": "@claude fix the null handling in services/payment.ts and open a PR"
  },
  "pull_request": {
    "number": 156,
    "head": { "ref": "feature/new-flow" },
    "base": { "ref": "main" }
  },
  "repository": {
    "name": "backend-api",
    "full_name": "myorg/backend-api"
  },
  "sender": {
    "login": "engineer-bob",
    "id": 790
  }
}
```

---

## Future Extensions (Not v1)

- Slash commands via GitHub app (`/claude explain ...`)
- Batch operations (multiple @claude mentions in one comment)
- Scheduled workflows (run review on every PR opened)
- Custom command definitions per repo

---

**Document version:** 1.0  
**Last updated:** 2026-04-08  
**Status:** Reference for task routing and normalization
