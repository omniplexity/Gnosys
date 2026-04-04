# Gnosys CLI Reference

**Version**: 1.0.5 | **Updated**: 2026-04-03

---

## Overview

The Gnosys CLI provides command-line access to the Gnosys memory backend. It allows you to:
- Check backend status and statistics
- Store, retrieve, and search memories
- Create and restore backups
- Retrieve context for queries
- View help and documentation

---

## Installation

The CLI is installed automatically with the gnosys-backend package:

```bash
pip install -e .
```

This installs two commands:
- `gnosys-backend` - Start the backend server
- `gnosys` - CLI for interacting with the backend

---

## Commands

### status

Show backend status and statistics.

```bash
gnosys status [OPTIONS]
```

**Options:**
- `-v, --verbose` - Show verbose status information

**Examples:**
```bash
gnosys status
gnosys status --verbose
```

**Output:**
```json
{
  "status": "healthy",
  "version": "0.8.0",
  "backend_url": "http://127.0.0.1:8766",
  "database": "gnosys.db",
  "total_memories": 12
}
```

---

### help

Display help information for Gnosys commands.

```bash
gnosys help [COMMAND]
```

**Arguments:**
- `COMMAND` - Optional. Show help for specific command

**Examples:**
```bash
gnosys help
gnosys help store
gnosys help get
```

---

### store

Store a new memory in the backend.

```bash
gnosys store [OPTIONS]
```

**Options:**
- `-c, --content <text>` **(required)** - The memory content to store
- `-t, --type <type>` - Memory type: `conversational`, `procedural`, `factual` (default: conversational)
- `-i, --tier <tier>` - Memory tier: `working`, `episodic`, `semantic`, `archive` (default: semantic)
- `--tags <tags>` - Comma-separated tags

**Examples:**
```bash
gnosys store --content "Remember to buy milk"
gnosys store -c "Task completed" -t factual -i semantic
gnosys store -c "Important note" --tags "work,urgent"
```

---

### get

Retrieve a memory by ID.

```bash
gnosys get <ID>
```

**Arguments:**
- `ID` **(required)** - The memory ID to retrieve

**Examples:**
```bash
gnosys get 8013f52b-86f5-4cff-961a-7686a401f756
```

---

### search

Search memories by keyword.

```bash
gnosys search <QUERY> [OPTIONS]
```

**Arguments:**
- `QUERY` **(required)** - Search query

**Options:**
- `-l, --limit <1-100>` - Maximum number of results (default: 10)
- `-t, --type <type>` - Filter by memory type
- `-i, --tier <tier>` - Filter by tier

**Examples:**
```bash
gnosys search project
gnosys search deadline -l 5
gnosys search task --tier episodic
```

---

### stats

Show memory statistics by type and tier.

```bash
gnosys stats
```

**Examples:**
```bash
gnosys stats
```

---

### backup

Create a backup of Gnosys data.

```bash
gnosys backup [OPTIONS]
```

**Options:**
- `-t, --type <type>` - Backup type: `full`, `incremental` (default: full)
- `-c, --components <list>` - Comma-separated components: `database`, `vectors`, `skills` (default: database,vectors)

**Examples:**
```bash
gnosys backup
gnosys backup --type full
gnosys backup -t incremental -c database,vectors
```

**Output:**
```json
{
  "id": "gnosys_full_20260403_223000",
  "backup_type": "full",
  "components": ["database", "vectors"],
  "file_path": "~/.openclaw/gnosys/backups/gnosys_full_20260403_223000.tar.gz",
  "checksum": "sha256:...",
  "size_bytes": 123456,
  "created_at": "2026-04-03T22:30:00+00:00"
}
```

---

### list-backups

List all available backups.

```bash
gnosys list-backups
```

**Examples:**
```bash
gnosys list-backups
```

**Output:**
```json
{
  "backups": [
    {
      "id": "gnosys_full_20260403_223000",
      "backup_type": "full",
      "file_path": "~/.openclaw/gnosys/backups/gnosys_full_20260403_223000.tar.gz",
      "size_bytes": 123456,
      "created_at": "2026-04-03T22:30:00+00:00"
    }
  ]
}
```

---

### restore

Restore Gnosys from a backup.

```bash
gnosys restore [OPTIONS]
```

**Options:**
- `-b, --backup-path <path>` **(required)** - Path to backup file
- `-t, --target <dir>` **(required)** - Target directory for restore
- `--overwrite` - Overwrite existing files

**Examples:**
```bash
gnosys restore -b ./backups/gnosys_full_20260403_223000.tar.gz -t ./data
gnosys restore --backup-path ./backup.tar.gz --target ./data --overwrite
```

**Output:**
```json
{
  "restored": {
    "database": "./data/gnosys.db",
    "vectors": "./data/vectors.db"
  }
}
```

---

### context

Retrieve context from memory for a query.

```bash
gnosys context <QUERY> [OPTIONS]
```

**Arguments:**
- `QUERY` **(required)** - Query to retrieve context for

**Options:**
- `-m, --max-tokens <tokens>` - Maximum tokens to retrieve (default: 4096)
- `-t, --tiers <list>` - Comma-separated tiers: `working`, `episodic`, `semantic`, `archive` (default: working,episodic,semantic)

**Examples:**
```bash
gnosys context "my project details"
gnosys context "project" -m 2048 -t working,episodic
```

**Output:**
```
Query: my project details
Used Tokens: 1500 / 4096
Tiers: working, episodic, semantic

Context:
[WORKING] User prefers dark mode theme

[EPISODIC] Project meeting on 2026-04-01 discussed feature requirements

[SEMANTIC] The project uses FastAPI with SQLite backend
```

---

## Error Output

All commands return structured error output when they fail:

```json
{
  "error": {
    "code": 1001,
    "message": "Cannot connect to Gnosys backend at http://127.0.0.1:8766",
    "suggestions": [
      "Ensure the backend is running: gnosys-backend",
      "Check the port configuration in config.json",
      "Verify no firewall is blocking the connection"
    ]
  }
}
```

---

## Configuration

The CLI uses the same configuration as the backend. See [CONFIGURATION.md](./CONFIGURATION.md) for details.

Default backend URL: `http://127.0.0.1:8766`

---

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 1001 | Connection error |
| 1002 | Timeout |
| 1003 | Invalid response |

---

*Documentation maintained by Austin - Last updated 2026-04-04*