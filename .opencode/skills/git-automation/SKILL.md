---
name: git-automation
description: >
  Git workflow automation for committing, pushing, and creating pull requests in a single flow.
  Creates branches, crafts commit messages from changes, pushes, and opens PRs with descriptions.
  Use when the user wants to commit changes, push to remote, create a PR, or automate git workflows.
  Triggers on: "commit this", "push and PR", "commit and push", "make a PR", "create pull request",
  "git workflow", "automate git", "commit my changes", "save and push", "publish changes".
license: MIT
metadata:
  author: OpenCode Skills (adapted from Anthropic claude-code commit-commands)
  version: "1.0.0"
  category: git-automation
  tags: "git, commit, push, pr, automation, workflow"
---

# Git Automation

Automated git workflow: commit → push → PR — all in a single response.

## Core Workflow

### Commit + Push + PR (full flow)

```
1. Check git status:          git status
2. Read current diff:         git diff HEAD
3. Identify current branch:   git branch --show-current
4. Create new branch if main
5. Stage and commit:          git add + git commit
6. Push to origin:            git push -u origin <branch>
7. Create PR:                 gh pr create
```

**Critical rule**: ALL steps must be done in a SINGLE message. Do not ask for confirmation between steps unless the changes are ambiguous.

### Commit message format

Analyze the diff and write a message following the repo's convention:

```
type(scope): concise description

- bullet point of key changes
- if breaking, add BREAKING CHANGE footer
```

Common types: `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `test`

### PR description format

```
## Summary
[Concise description of what this PR does]

## Changes
- [File/area]: [description of change]
- [File/area]: [description of change]

## Related
Closes #[issue] (if applicable)
```

## Common Scenarios

### 1. Quick commit (no PR)

```bash
git add -A
git commit -m "type(scope): message"
git push
```

Conditions: user says "commit" or "save" without mentioning PR.

### 2. Commit + Push + PR

```bash
# Check if on main → create branch
git checkout -b feat/my-feature

# Stage, commit, push, PR
git add -A
git commit -m "feat(scope): description"
git push -u origin feat/my-feature
gh pr create --fill
```

Conditions: user says "PR", "pull request", or changes are significant.

### 3. Quick fix (no branch, direct to main)

```bash
git add -A
git commit -m "fix(scope): description"
git push
```

Conditions: user says "quick fix", "minor change", or explicitly says "push to main".

## Guardrails

### Pre-flight checks (before any git operation):
1. `git status` — understand what's staged/unstaged
2. `git diff HEAD` — review all changes before committing
3. `git branch --show-current` — know where you are

### Never do:
- Force push (`git push --force`) without explicit confirmation
- Amend pushed commits
- Delete branches without asking
- Commit secrets, API keys, credentials — flag if seen in diff
- Write vague commit messages ("fix stuff", "update", "changes")

### Always verify:
- Commit only intended files (check `git status` carefully)
- No debug code, console.log, print statements in the diff
- No merge conflicts
- No large binary files accidentally staged

## Tips

- **One commit per logical change** — don't bundle unrelated changes
- **Reference issues** in commit messages and PR descriptions
- **Use `--fill` with `gh pr create`** to auto-populate from commits
- **Branch naming**: `type/description` (e.g., `feat/user-auth`, `fix/login-bug`)
- **Draft PRs**: Use `gh pr create --draft` for work-in-progress

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| git-automation | code-review-workflow | PR creation triggers PR review |
| git-automation | behavioral-rules | Commit hooks enforce rules before push |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `gh` not authenticated | Run `gh auth login` |
| Push rejected | Pull latest: `git pull --rebase origin <branch>` |
| Wrong branch | `git switch <correct-branch>` and re-stage |
| Uncommitted work | `git stash` before switching, `git stash pop` after |
