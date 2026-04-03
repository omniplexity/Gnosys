# Skills Component

## Overview

The Skills system provides autonomous skill detection, extraction, storage, and refinement from trajectory data.

## File

`python/src/gnosys_backend/skills.py`

## Class: SkillSystem

```python
class SkillSystem:
    def __init__(self, db: Database, config: SkillsConfig) -> None: ...
    
    async def detect_patterns_from_trajectories(...) -> list[dict[str, Any]]: ...
    
    async def extract_skill(...) -> SkillRecord: ...
    
    async def list_skills() -> SkillListResponse: ...
    
    async def get_skill(skill_id: str) -> SkillRecord | None: ...
    
    async def match_skill(request: SkillMatchRequest) -> SkillMatchResponse: ...
    
    async def refine_skill(skill_id: str, 
                          request: SkillRefineRequest) -> SkillRefineResponse: ...
    
    async def delete_skill(skill_id: str) -> bool: ...
    
    async def get_skill_stats() -> dict[str, Any]: ...
```

## Skill Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Lifecycle                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌────────┐ │
│  │ Detect  │ →  │ Extract  │ →  │ Store   │ →  │ Refine │ │
│  └─────────┘    └──────────┘    └─────────┘    └────────┘ │
│       ↑                                                │    │
│       └────────────────── Loop ──────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Skill Detection

Triggers:
- **Repeated patterns**: Same tool sequence used 3+ times
- **Successful solutions**: Task completed successfully
- **User request**: Explicit skill creation

### Skill Extraction

Extracts from trajectories:
- Tool call sequences
- Parameter patterns
- Conditional logic
- Error handling patterns

### SKILL.md Format

Skills are stored in SKILL.md format:

```markdown
# Skill: Code Review

**Version**: 1.0.0
**ID**: uuid

## Triggers
- Code review requests
- PR review tasks

## Workflow
1. Read changed files
2. Run linter/static analysis
3. Identify potential issues
4. Suggest improvements

## Tools
- read, exec, glob

## Parameters
- {repo_path}: Repository location
- {branch}: Branch to review
```

### Skill Metadata

```json
{
  "name": "code_review",
  "version": "1.0.0",
  "created": "2024-01-15T10:30:00Z",
  "last_used": "2024-01-20T14:22:00Z",
  "use_count": 42,
  "success_rate": 0.95,
  "trigger_count": 3,
  "compounds_from": ["git_diff", "lint_check"]
}
```

### Skill Refinement

- **Versioning**: Semantic versioning (major.minor.patch)
- **Compounding**: Skills can build on other skills
- **Success Rate Tracking**: EMA-based success tracking
- **Rollback**: Version history for rollback

## Configuration

```json
{
  "skills": {
    "enabled": true,
    "auto_detect": true,
    "detection": {
      "min_pattern_count": 3,
      "success_threshold": 0.8,
      "min_task_complexity": "medium"
    },
    "storage": {
      "directory": "~/.openclaw/gnosys/skills",
      "max_skills": 100,
      "auto_cleanup": true,
      "delete_below_success_rate": 0.5
    }
  }
}
```

## Usage

```python
from gnosys_backend.skills import SkillSystem

skills = SkillSystem(db, config)

# List skills
result = await skills.list_skills()

# Create skill
skill = await skills.extract_skill(
    name="code_review",
    tools=["read", "exec", "glob"],
    workflow=["Read files", "Run linter", "Identify issues"],
    triggers=["code review", "PR review"],
    description="Automated code review workflow"
)

# Match skill to task
match = await skills.match_skill(SkillMatchRequest(
    task="Review PR #123",
    context={"repo": "myapp"}
))

# Refine skill
refined = await skills.refine_skill(skill.id, SkillRefineRequest(
    feedback="Found more issues",
    success=True,
    improvements=["Check security", "Check performance"]
))
```

## Database Schema

```sql
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    triggers_json TEXT NOT NULL,
    workflow_json TEXT NOT NULL,
    tools_json TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    description TEXT,
    compounds_from_json TEXT NOT NULL,
    use_count INTEGER NOT NULL DEFAULT 0,
    success_rate REAL NOT NULL DEFAULT 0.0,
    trigger_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_used_at TEXT
);
```

## File Storage

Skills are stored as files:

```
~/.openclaw/gnosys/skills/
├── code_review/
│   ├── SKILL.md
│   └── metadata.json
├── github_issues/
│   ├── SKILL.md
│   └── metadata.json
```
