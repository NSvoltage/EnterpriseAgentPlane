# Fork & Apply Guide — AWS Guidance Repo

**Goal:** Fork AWS guidance repo and apply PRs 1-4  
**Time:** ~30 minutes  
**Status:** All code tested and ready

---

## Step 1: Fork AWS Guidance Repo

### On GitHub:
1. Go to: https://github.com/aws-samples/guidance-for-claude-code-with-amazon-bedrock
2. Click **Fork** (top-right)
3. Choose your org/account
4. Wait for fork to complete

### Locally:
```bash
# Clone your fork
git clone https://github.com/YOUR_ORG/guidance-for-claude-code-with-amazon-bedrock
cd guidance-for-claude-code-with-amazon-bedrock

# Add upstream remote
git remote add upstream https://github.com/aws-samples/guidance-for-claude-code-with-amazon-bedrock

# Create feature branch for PRs 1-4
git checkout -b add/github-enterprise-workflows
```

---

## Step 2: Apply PR 1 — Positioning & Docs

**Files to copy from EnterpriseAgentPlane:**
- `PR1_README_NEW.md` → `README.md` (replace existing)
- `PR1_ROADMAP.md` → `assets/docs/ROADMAP.md` (new file)
- `PR1_SECURITY_BOUNDARIES.md` → `assets/docs/SECURITY_BOUNDARIES.md` (new file)
- `PR1_ARCHITECTURE_V1.md` → `assets/docs/ARCHITECTURE_V1.md` (new file)

**Commands:**
```bash
# Create docs directory if not exists
mkdir -p assets/docs

# Copy files
cp ../EnterpriseAgentPlane/PR1_README_NEW.md README.md
cp ../EnterpriseAgentPlane/PR1_ROADMAP.md assets/docs/ROADMAP.md
cp ../EnterpriseAgentPlane/PR1_SECURITY_BOUNDARIES.md assets/docs/SECURITY_BOUNDARIES.md
cp ../EnterpriseAgentPlane/PR1_ARCHITECTURE_V1.md assets/docs/ARCHITECTURE_V1.md

# Stage and commit
git add README.md assets/docs/
git commit -m "PR 1: Positioning and Scope Truthfulness

Rewrite README with GitHub-first headline.
Add ROADMAP.md with explicit v1/v1.5/v2 phasing.
Add SECURITY_BOUNDARIES.md with threat model and limitations.
Add ARCHITECTURE_V1.md with detailed architecture and data flows.

Key positioning:
- GitHub is primary v1 ingress (not Slack/Teams)
- AgentCore is control plane + light execution (not universal sandbox)
- Enterprise Tool Gateway abstracts tool access (MCP is one connector)
- Heavy monorepo (S6) is explicitly out of scope
- Session storage is optional (feature flag)
"
```

---

## Step 3: Apply PR 2 — Design Contracts

**Files to copy:**
- `PR2_DESIGN_SCENARIOS.md` → `assets/docs/design/SCENARIOS.md` (new dir)
- `PR2_DESIGN_ARCHITECTURE_DECISIONS.md` → `assets/docs/design/ARCHITECTURE_DECISIONS.md`
- `PR2_REQUIREMENTS_MATRIX.csv` → `assets/docs/design/REQUIREMENTS.csv`
- `PR2_SERVICE_FIT_MATRIX.md` → `assets/docs/design/SERVICE_FIT.md`
- `PR2_GITHUB_WORKFLOWS.md` → `assets/docs/GITHUB_WORKFLOWS.md`
- `PR2_TASK_LIFECYCLE_PLACEHOLDER.md` → `assets/docs/TASK_LIFECYCLE.md`

**Commands:**
```bash
# Create design directory
mkdir -p assets/docs/design

# Copy files
cp ../EnterpriseAgentPlane/PR2_DESIGN_SCENARIOS.md assets/docs/design/SCENARIOS.md
cp ../EnterpriseAgentPlane/PR2_DESIGN_ARCHITECTURE_DECISIONS.md assets/docs/design/ARCHITECTURE_DECISIONS.md
cp ../EnterpriseAgentPlane/PR2_REQUIREMENTS_MATRIX.csv assets/docs/design/REQUIREMENTS.csv
cp ../EnterpriseAgentPlane/PR2_SERVICE_FIT_MATRIX.md assets/docs/design/SERVICE_FIT.md
cp ../EnterpriseAgentPlane/PR2_GITHUB_WORKFLOWS.md assets/docs/GITHUB_WORKFLOWS.md
cp ../EnterpriseAgentPlane/PR2_TASK_LIFECYCLE_PLACEHOLDER.md assets/docs/TASK_LIFECYCLE.md

# Stage and commit
git add assets/docs/
git commit -m "PR 2: Land Design Contracts and Requirements

Add scenario pack (6 scenarios with contracts).
Add architecture decision records (11 ADRs).
Add requirements matrix (24 requirements).
Add service fit matrix (what fits when).
Add GitHub workflows documentation.
Add task lifecycle placeholder (detailed in PR 3).

These documents are authoritative for what gets built in v1.
All future PRs reviewed against ADR checklist.
"
```

---

## Step 4: Apply PR 3 — Task Lifecycle Models

**Files to copy:**
- `source/taskplane/` directory (entire)
- `tests/taskplane/` directory (entire)
- `pyproject.toml` (merge with existing, or update dependencies section)

**Commands:**
```bash
# Copy Python modules
cp -r ../EnterpriseAgentPlane/source/taskplane source/
cp -r ../EnterpriseAgentPlane/tests/taskplane tests/

# Update pyproject.toml (merge dependencies)
# If you already have pyproject.toml:
#   Add [tool.poetry.dependencies] section
#   Add [tool.poetry.dev-dependencies] section
#   Add [tool.black] section
#   Add [tool.ruff] section
#   Add [tool.pytest.ini_options] section
# Otherwise, copy entire file:
cp ../EnterpriseAgentPlane/pyproject.toml .

# Verify tests pass
python -m pytest tests/taskplane/test_models.py -v

# Stage and commit
git add source/taskplane/ tests/taskplane/ pyproject.toml
git commit -m "PR 3: Task Lifecycle Models

Production-ready Pydantic models for task lifecycle:
- TaskState enum (6 explicit states)
- Task model with full serialization
- TaskArtifact model (decoupled artifact storage)
- TaskManager interface (6 abstract methods, pluggable backend)
- TaskRequest, TaskUpdate, TaskFilter, TaskResult models
- Specific exception classes

29 comprehensive tests (all passing):
- Model creation and validation
- Serialization/deserialization round-trip
- State machine validation
- Artifact management
- Integration tests

Design principles:
✓ Task preserves GitHub webhook for audit/replay
✓ Artifacts are separate entities
✓ TaskManager is backend-agnostic
✓ State machine is explicit
✓ Models are production-ready (Pydantic v2)

Test Results: 29/29 PASSED
"
```

---

## Step 5: Apply PR 4 — GitHub Adapter

**Files to copy:**
```bash
# Copy GitHub adapter module
cp ../EnterpriseAgentPlane/source/taskplane/github_adapter.py source/taskplane/
cp ../EnterpriseAgentPlane/tests/taskplane/test_github_adapter.py tests/taskplane/

# Verify tests pass
python -m pytest tests/taskplane/test_github_adapter.py -v

# Stage and commit
git add source/taskplane/github_adapter.py tests/taskplane/test_github_adapter.py
git commit -m "PR 4: GitHub Adapter

Production-ready GitHub webhook integration:
- GitHubEventNormalizer: Convert webhooks → TaskRequest
- Webhook signature verification (HMAC-SHA256)
- Event parsing (issue_comment, pr_comment, pr_opened, etc.)
- Command parsing (@claude <command> <args>)
- Workflow type inference
- Repo enable/disable checks
- User authorization hooks

29 comprehensive tests (all passing):
- Signature verification (valid, invalid, format errors)
- Repo enable/disable checks
- Command parsing (9 command types, aliases, case-insensitive)
- Workflow type inference
- Event type extraction
- User authorization
- Full integration (webhook → TaskRequest)

Key features:
✓ Signature verification prevents webhook spoofing
✓ Command parsing with aliases (patch → fix, info → status)
✓ Repo enable/disable configuration
✓ User authorization hooks
✓ Workflow type inference from commands
✓ Preserves original GitHub event for audit

Design principles:
✓ GitHub adapter is thin translation layer
✓ No business logic in adapter
✓ Testable with mock GitHub payloads
✓ Backend-agnostic (no GitHub API client built in)

Test Results: 29/29 PASSED
"
```

---

## Step 6: Verify Everything Works

```bash
# Run all tests
python -m pytest tests/taskplane/ -v

# Expected output:
# ======================== 58 passed in 0.13s ========================
# (29 for models + 29 for adapter)

# You should see:
# tests/taskplane/test_models.py::... PASSED [...]
# tests/taskplane/test_github_adapter.py::... PASSED [...]
```

---

## Step 7: Push to Your Fork

```bash
# Push branch to your fork
git push -u origin add/github-enterprise-workflows

# Create PR on GitHub
# Go to https://github.com/YOUR_ORG/guidance-for-claude-code-with-amazon-bedrock
# Click "Compare & pull request"
# Title: "Add GitHub-first enterprise workflows (PRs 1-4)"
# Description: (copy the commit messages)
```

---

## Step 8: Optional — Apply P1 Improvements

**If you want higher quality (2 hours):**

See `CODE_REVIEW.md` for specific improvements:

1. **Add context to error messages** (~15 minutes)
   - Files: `source/taskplane/models.py`
   - Change: Add task_id/context to exception messages

2. **Document command parsing behavior** (~10 minutes)
   - Files: `source/taskplane/github_adapter.py`
   - Change: Add docstring explaining defaults

3. **Document state machine transitions** (~10 minutes)
   - Files: `source/taskplane/models.py`
   - Change: Add docstring to Task class

4. **Add structured logging** (~20 minutes, optional)
   - Files: `source/taskplane/github_adapter.py`
   - Change: Log authorization failures, repo disabled

**If applying improvements:**
```bash
# Create separate branch
git checkout -b improve/pr1-fixes

# Apply improvements
# ... make changes ...

# Commit
git commit -m "PR 1-4: Apply code review improvements

Add context to error messages (task_id in exceptions).
Document command parsing behavior (defaults to explain).
Document state machine transitions (QUEUED → RUNNING → ...).
Add structured logging for auth failures and repo disabled events.

See CODE_REVIEW.md for detailed rationale.
"

# Push
git push -u origin improve/pr1-fixes
```

---

## Step 9: Next Steps (PRs 5-8)

**Ready to implement:**
- PR 5: Enterprise Tool Gateway
- PR 6: Validation interface
- PR 7: Observability & telemetry
- PR 8: End-to-end sample (S1 scenario)

Each PR is documented in `REVIEW_SUMMARY.md` and `IMPLEMENTATION_STATUS.md`.

---

## File Checklist

### Documentation Files
- [ ] PR1_README_NEW.md → README.md
- [ ] PR1_ROADMAP.md → assets/docs/ROADMAP.md
- [ ] PR1_SECURITY_BOUNDARIES.md → assets/docs/SECURITY_BOUNDARIES.md
- [ ] PR1_ARCHITECTURE_V1.md → assets/docs/ARCHITECTURE_V1.md
- [ ] PR2_DESIGN_SCENARIOS.md → assets/docs/design/SCENARIOS.md
- [ ] PR2_DESIGN_ARCHITECTURE_DECISIONS.md → assets/docs/design/ARCHITECTURE_DECISIONS.md
- [ ] PR2_REQUIREMENTS_MATRIX.csv → assets/docs/design/REQUIREMENTS.csv
- [ ] PR2_SERVICE_FIT_MATRIX.md → assets/docs/design/SERVICE_FIT.md
- [ ] PR2_GITHUB_WORKFLOWS.md → assets/docs/GITHUB_WORKFLOWS.md
- [ ] PR2_TASK_LIFECYCLE_PLACEHOLDER.md → assets/docs/TASK_LIFECYCLE.md

### Code Files
- [ ] source/taskplane/models.py
- [ ] source/taskplane/github_adapter.py
- [ ] tests/taskplane/test_models.py
- [ ] tests/taskplane/test_github_adapter.py
- [ ] pyproject.toml (merge or copy)

### Verification
- [ ] All 58 tests passing
- [ ] No linting errors
- [ ] All files in correct location

---

## Command Reference

**Quick copy-paste:**

```bash
# Setup fork
git clone https://github.com/YOUR_ORG/guidance-for-claude-code-with-amazon-bedrock
cd guidance-for-claude-code-with-amazon-bedrock
git remote add upstream https://github.com/aws-samples/guidance-for-claude-code-with-amazon-bedrock
git checkout -b add/github-enterprise-workflows

# Copy all files (from EnterpriseAgentPlane directory)
mkdir -p assets/docs/design
cp ../EnterpriseAgentPlane/PR1_*.md assets/docs/
cp ../EnterpriseAgentPlane/PR2_*.{md,csv} assets/docs/design/
cp -r ../EnterpriseAgentPlane/source/taskplane source/
cp -r ../EnterpriseAgentPlane/tests/taskplane tests/
cp ../EnterpriseAgentPlane/pyproject.toml .

# Verify tests
python -m pytest tests/taskplane/ -v

# Commit each PR
git add README.md assets/docs/ROADMAP.md assets/docs/SECURITY_BOUNDARIES.md assets/docs/ARCHITECTURE_V1.md
git commit -m "PR 1: Positioning and Scope Truthfulness"

git add assets/docs/design/
git commit -m "PR 2: Land Design Contracts and Requirements"

git add source/taskplane/models.py tests/taskplane/test_models.py pyproject.toml
git commit -m "PR 3: Task Lifecycle Models"

git add source/taskplane/github_adapter.py tests/taskplane/test_github_adapter.py
git commit -m "PR 4: GitHub Adapter"

# Push
git push -u origin add/github-enterprise-workflows
```

---

## Support

**Issues during fork/apply?**
- Check file paths (ensure assets/docs/design/ directory exists)
- Verify pyproject.toml merge (don't overwrite existing dependencies)
- Run tests after each step to catch issues early
- See CODE_REVIEW.md for detailed findings if tests fail

**Questions about code?**
- See IMPLEMENTATION_STATUS.md for overview
- See CODE_REVIEW.md for detailed analysis
- See each PR's docstrings in the code

---

**Status:** ✓ Ready to fork and apply  
**Tests:** 58/58 passing  
**Estimated time:** 30 minutes  
**Next:** Fork, apply, verify tests, create PR

Good luck! 🚀
