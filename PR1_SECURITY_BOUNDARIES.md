# Security Boundaries — Claude Code on Bedrock v1

A clear articulation of what is protected, what is assumed safe, and what requires customer action.

## Threat Model

### Assets to Protect
1. **Source code repositories** — Don't expose sensitive repos to unauthorized tasks
2. **Model invocations** — Only approved teams/users can call Claude Code
3. **Tool access** — Internal systems (deploys, incidents, databases) must have policy gates
4. **User identity** — Attribution must be accurate and tamper-proof
5. **Audit trail** — All actions must be logged and non-repudiable

### Attack Vectors Addressed in v1

#### 1. **Unauthorized repo access**
- **Threat:** Attacker uses @claude mention in non-enabled repo
- **Control:** GitHub webhook validates repo is enabled before task creation
- **Boundary:** GitHub permissions are the source of truth; we don't override
- **Trust assumption:** GitHub org admins control who can push to enabled repos

#### 2. **User impersonation**
- **Threat:** Attacker forges GitHub identity
- **Control:** User identity comes from GitHub API (webhook signature verified)
- **Boundary:** Signature validation prevents webhook spoofing
- **Trust assumption:** GitHub's webhook signing is secure (it is)

#### 3. **Credential theft / exposure**
- **Threat:** AWS temporary credentials or OIDC tokens leak
- **Control:** Credentials are short-lived (1 hour max), issued per-session
- **Boundary:** Foundation layer (existing AWS guidance repo) handles credential lifecycle
- **Trust assumption:** AWS STS and Cognito credential handling is secure (it is)

#### 4. **Malicious code execution**
- **Threat:** Claude Code generates malicious code and/or it's applied to repo without review
- **Control:** v1 PR draft workflows produce GitHub PR drafts for review, not auto-merge
- **Boundary:** Humans must review before merge (GitHub branch protection)
- **Trust assumption:** GitHub RBAC and PR approval requirements work as expected

#### 5. **Tool access abuse**
- **Threat:** Attacker uses task context to invoke restricted internal tools
- **Control:** Tool gateway enforces authorization before invocation
- **Boundary:** Approval gates and role checks are enforced server-side
- **Trust assumption:** Tool owners implement the policy interface correctly

#### 6. **Audit trail tampering**
- **Threat:** Attacker deletes or modifies logs of what happened
- **Control:** CloudTrail logs are immutable and write-once
- **Boundary:** Task telemetry is sent to CloudWatch (immutable)
- **Trust assumption:** CloudTrail and CloudWatch cannot be deleted by task context

#### 7. **Denial of service**
- **Threat:** Attacker submits expensive or infinite-loop tasks to exhaust quota
- **Control:** AgentCore Runtime has hard timeout (8h async, 15m sync)
- **Boundary:** Task doesn't have permission to override timeouts
- **Trust assumption:** AgentCore Runtime enforces these limits (it does)

#### 8. **Policy bypass via tool connector**
- **Threat:** Attacker finds a tool connector that doesn't enforce policy
- **Control:** Tool gateway is the policy enforcement point
- **Boundary:** Connectors (MCP, REST, etc.) must delegate to gateway for auth
- **Trust assumption:** Tool connectors are reviewed before adding to registry

---

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer's Enterprise                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  GitHub (source of truth for code + permissions)     │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AWS Account (identity, networking, audit logs)      │   │
│  │  ├─ IAM OIDC Provider / Cognito Identity Pool       │   │
│  │  ├─ Bedrock (Claude Code invocation)                │   │
│  │  ├─ AgentCore Runtime (task execution)              │   │
│  │  ├─ CloudTrail (immutable audit)                    │   │
│  │  ├─ CloudWatch (observability)                      │   │
│  │  └─ Internal Tool Gateway (policy enforcement)      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  AWS Bedrock (Claude Code & AgentCore — AWS-managed)       │
│  (We do not control or audit AgentCore internals)          │
└─────────────────────────────────────────────────────────────┘
```

### Inside Our Boundary (We Enforce)

- **Task creation** — Only from authorized GitHub events
- **User attribution** — Mapped from GitHub → AWS identity
- **Repo scoping** — Tasks can only access enabled repos
- **Tool authorization** — Policy gates before tool invocation
- **Audit logging** — All task state changes, tool accesses

### Outside Our Boundary (We Assume Secure)

- **AgentCore Runtime internals** — AWS-managed, in preview
- **Bedrock model behavior** — Claude's safety properties
- **GitHub webhook security** — GitHub's signing and delivery
- **AWS IAM/STS/Cognito** — AWS's authentication and credential systems
- **AWS CloudTrail/CloudWatch** — AWS's logging infrastructure

### Customer's Responsibility

- **GitHub org configuration** — Branch protection, CODEOWNERS, approvals
- **Identity provider security** — Keep OIDC credentials and IdP secure
- **Tool connector implementations** — If building custom connectors, follow the security model
- **Approval policy tuning** — Set appropriate approval gates per tool/repo
- **Network security** — If using private deployment, VPC configuration
- **Monitoring & alerting** — Set up alerts for unusual task patterns

---

## Known Limitations & Mitigations

### 1. AgentCore Session Storage is Preview

**Limitation:**  
AgentCore persistent filesystem can reset (versioning, inactivity) and is not guaranteed stable.

**Mitigation:**  
- v1 does NOT require session storage
- Treat it as optional feature flag
- Each workflow should be able to start from scratch
- Document v1 as session-less

**Future:** v2 may standardize on session storage with SLAs.

---

### 2. AgentCore Has Hard Timeout Limits

**Limitation:**  
- Async jobs: maximum 8 hours
- Synchronous calls: maximum 15 minutes
- Per-session compute and memory quotas

**Mitigation:**  
- Scenario S6 (heavy monorepo/mobile builds) is explicitly out of v1
- Document these limits in README and scenario descriptions
- Recommend CodeBuild for longer-running validation
- Design workflows to work within these constraints

**Future:** v2 will support pluggable heavier backends.

---

### 3. Fine-Grained Policy Has Limitations

**Limitation:**  
AgentCore policy does not support principal-level fine-grained policies. We can enforce "is user in approved role" but not "can user X call tool Y with parameter Z only on Mondays."

**Mitigation:**  
- Tool gateway implements approval gates for high-risk operations
- v1 supports curated tool sets with role-based authorization
- Document that dynamic principal-level policies are v2 work
- Use GitHub team membership + AWS role mapping for coarse-grained control

**Future:** v2 will support fine-grained policy composition (Cedar-like).

---

### 4. MCP Connector Depends on Target Tool

**Limitation:**  
MCP connector security depends on the tool's MCP implementation. We can't guarantee all MCP servers are secure.

**Mitigation:**  
- Tool registry requires review + approval before adding
- MCP tools must be from curated, trusted sources
- Connector validates schema before execution
- Tool access is logged (not hidden in MCP protocol)
- Policy gates are server-side, not delegated to MCP

**Future:** Tool marketplace may have vetting process.

---

### 5. No End-to-End Encryption in Logs

**Limitation:**  
Task logs are stored in CloudWatch. Model inputs/outputs may be visible to AWS support (if requested).

**Mitigation:**  
- Don't include secrets or PII in @claude prompts
- Use tool gateway for accessing sensitive data (tools can sanitize before returning)
- Customer can implement VPC endpoint + PrivateLink for private deployment
- CloudWatch logs are immutable once written (tamper-proof)

**Future:** Customer can configure encrypted log retention per org policy.

---

### 6. GitHub Permissions Are Source of Truth

**Limitation:**  
If GitHub is compromised, this system is compromised (same as any GitHub-based workflow).

**Mitigation:**  
- Standard GitHub security best practices apply (2FA, branch protection, CODEOWNERS)
- Encourage org admins to audit GitHub collaborators
- CloudTrail logs all Bedrock invocations (GitHub is not the final audit)
- Recommend MFA for GitHub accounts

**Future:** Support GitHub Enterprise with additional controls if needed.

---

## Threat Scenarios (Out of Scope for v1)

### Scenario: Cross-Repo Access Escalation
**Threat:** Attacker enables task on repo A, then tries to access repo B through tool gateway  
**Why out of v1 scope:** Requires fine-grained policy (depends on Cedar-like support in v2)  
**v1 mitigation:** Approve tools per repo; don't create global tool that accesses all repos

### Scenario: Model Injection / Prompt Poisoning
**Threat:** Attacker crafts PR comment to trick Claude into revealing system prompts  
**Why out of v1 scope:** Depends on Claude's guardrails, not our system  
**v1 mitigation:** Document in user guides; Claude's safety training should cover this  
**Future:** Apply safety filters to task inputs in v2 if needed

### Scenario: Resource Exhaustion via Forking
**Threat:** Attacker creates many tasks to exhaust AgentCore quota  
**Why out of v1 scope:** Quota management is AWS-level, not our layer  
**v1 mitigation:** Document quota limits; recommend monitoring dashboards  
**Future:** Implement task rate limiting in task gateway if needed

---

## Deployment-Specific Boundaries

### Standard AWS Deployment (Default)

**Assumptions:**
- Bedrock, AgentCore, CloudTrail are in same AWS account
- GitHub webhook delivers to Lambda/API Gateway in public internet
- Tools are accessed via public internet or AWS VPC

**Not protected:**
- Webhook delivery network (HTTPS TLS assumed)
- Tool APIs on public internet (depends on tool's TLS)

**Mitigations:**
- Verify webhook signature
- Use API Gateway WAF for rate limiting
- Recommend tool endpoints be HTTPS-only

### Private VPC Deployment (Advanced)

**Assumptions:**
- Task execution happens in private subnets
- Tools are accessed via PrivateLink or VPC endpoints
- GitHub webhook delivered via PrivateLink to API Gateway

**Additional protections:**
- Tools not accessible from public internet
- Network-level isolation of task runtime
- Internal-only audit log delivery

**Customer responsibility:**
- VPC configuration and subnet isolation
- PrivateLink endpoint management
- Private NAT or VPN for GitHub webhook

**Not supported in v1:** Full private deployment with all components isolated.  
**Supported in v1:** Reference documentation for AWS-recommended private patterns.

---

## Audit & Compliance

### What Is Logged

**CloudTrail (AWS API audit):**
- All Bedrock invocations (user, model, region, time, tokens)
- IAM role assumption (temporary credential issuance)
- AgentCore Runtime session creation

**CloudWatch (Task telemetry):**
- Task state transitions (queued → running → completed)
- Tool invocation attempts and outcomes
- Validation check results
- User and repo attribution

**GitHub (Workflow audit):**
- Comments and mentions (@claude)
- PR creation / commits
- Review comments

### What Is NOT Logged

- Model output content (not stored by default)
- Full tool responses (summarized in metrics)
- Source code file contents (analyzed at runtime, not stored)

**Customers can:**
- Export CloudWatch Logs to S3 for long-term retention
- Stream logs to Splunk / Datadog / other SIEM
- Implement custom logging via task callbacks

### Compliance Frameworks

**Supported:**
- SOC 2 Type II (CloudTrail provides audit trail)
- FedRAMP (if using GovCloud deployment, future)
- HIPAA (if using HIPAA-eligible Bedrock models, future)

**Recommended practices:**
- Enable MFA on GitHub and AWS
- Regular access reviews
- CloudWatch alert on unusual patterns
- Quarterly audit log reviews

---

## Security Checklist for Operators

Before deploying v1, ensure:

- [ ] **Identity:** OIDC provider is configured and credentials are short-lived
- [ ] **GitHub:** Org has branch protection, CODEOWNERS, and 2FA enabled
- [ ] **Repos:** Only enable task access for repos that have approved maintainers
- [ ] **Tools:** Review every tool in tool registry before adding
- [ ] **Approvals:** Set approval gates for high-risk tools (mutations, data access)
- [ ] **Monitoring:** CloudWatch dashboard is configured; set up alerts
- [ ] **Audit:** CloudTrail is enabled and logs are exported to S3
- [ ] **Network:** If private deployment, VPC configuration is reviewed
- [ ] **Secrets:** No secrets in GitHub comments, configs, or logs
- [ ] **Limits:** DocumentAgentCore timeouts and quota limits to users

---

## Incident Response

### If a Task Is Compromised

1. **Immediate:** Cancel the task (it will timeout in 8h max anyway)
2. **Audit:** Review CloudTrail for what APIs were called
3. **Scope:** Check if any PRs were created (review before merging)
4. **Revoke:** If tool was abused, revoke the tool from registry
5. **Notify:** Inform repo maintainers and tool owners
6. **Review:** Update approval policies if needed

### If GitHub Account Is Compromised

1. **GitHub:** Follow GitHub's incident response (reset 2FA, audit PATs)
2. **Audit:** Review CloudTrail for any Bedrock invocations by that user
3. **Revoke:** Disable the user's AWS role if needed
4. **Scope:** Check if any PRs were created in their name
5. **Notify:** Inform security team and affected repo owners

### If AWS Credentials Leak

1. **IAM:** Revoke the leaked role immediately
2. **CloudTrail:** Review all Bedrock API calls from that role
3. **Audit:** Check if any tasks were created or tools invoked
4. **Scope:** If only temporary credentials (they expire in 1h), monitor for the hour
5. **Notify:** Inform security team; CloudTrail may have recorded the exposure

---

## Security Feedback

Found a security issue?

1. **Do not** open a public GitHub issue
2. **Do** email security@example.com with details
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 24h and provide updates.

---

**Document version:** 1.0  
**Last updated:** 2026-04-08  
**Status:** Final (for v1 release)
