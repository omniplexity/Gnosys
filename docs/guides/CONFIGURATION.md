# Configuration Guide

## Overview

This guide covers all configuration options for the Gnosys plugin and backend.

## OpenClaw Configuration

### Plugin Slot

```json
{
  "plugins": {
    "slots": {
      "memory": "gnosys",
      "contextEngine": "gnosys"
    }
  }
}
```

### Plugin Entry

```json
{
  "plugins": {
    "entries": {
      "gnosys": {
        "enabled": true,
        "config": {
          "mode": "spawn-local-python-backend",
          "requestTimeoutMs": 10000,
          "healthcheckTimeoutMs": 3000,
          "backendUrl": "http://127.0.0.1:8766",
          "spawn": {
            "command": "python",
            "args": ["-m", "gnosys_backend.app"],
            "cwd": "./python",
            "host": "127.0.0.1",
            "port": 8766,
            "dbPath": "./python/data/gnosys.db",
            "vectorsPath": "./python/data/vectors.db",
            "startupTimeoutMs": 10000
          },
          "retention": {
            "episodicDays": 30,
            "archiveDays": 365,
            "defaultSearchLimit": 10
          },
          "embeddings": {
            "provider": "local",
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "dimension": 384,
            "openaiModel": "text-embedding-3-small",
            "batchSize": 32
          },
          "context": {
            "enabled": true,
            "maxTokens": 4000,
            "budgetFraction": 0.5,
            "includeTiers": ["working", "episodic", "semantic", "archive"]
          },
          "pipeline": {
            "enabled": true,
            "maxAgents": 10,
            "defaultTimeoutSeconds": 300
          },
          "learning": {
            "enabled": true,
            "patternDetection": {
              "trajectoryLimit": 100,
              "minSequenceLength": 2,
              "minFrequency": 2
            },
            "datasetGeneration": {
              "successThreshold": 0.8,
              "minTrajectories": 100
            }
          },
          "skills": {
            "enabled": true,
            "autoDetect": true,
            "detection": {
              "minPatternCount": 3,
              "successThreshold": 0.8
            },
            "storage": {
              "directory": "~/.openclaw/gnosys/skills",
              "maxSkills": 100
            }
          },
          "scheduler": {
            "enabled": true,
            "maxConcurrent": 5,
            "timeoutSeconds": 300
          },
          "api": {
            "enabled": true,
            "host": "127.0.0.1",
            "port": 8766,
            "auth": {
              "type": "bearer",
              "token": "gnosys_api_token"
            }
          },
          "monitoring": {
            "enabled": true,
            "metricsPort": 8767
          }
        }
      }
    }
  }
}
```

## Configuration Options

### Connection Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | string | `spawn-local-python-backend` | Connection mode: `spawn-local-python-backend` or `backend-url` |
| `requestTimeoutMs` | number | 10000 | HTTP request timeout in milliseconds |
| `healthcheckTimeoutMs` | number | 3000 | Health check timeout in milliseconds |
| `backendUrl` | string | `http://127.0.0.1:8766` | Backend URL (when not using spawn mode) |

### Spawn Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `command` | string | `python` | Command to spawn |
| `args` | array | `["-m", "gnosys_backend.app"]` | Command arguments |
| `cwd` | string | `./python` | Working directory |
| `host` | string | `127.0.0.1` | Backend host |
| `port` | number | 8766 | Backend port |
| `dbPath` | string | `./python/data/gnosys.db` | SQLite database path |
| `vectorsPath` | string | `./python/data/vectors.db` | Vector database path |
| `startupTimeoutMs` | number | 10000 | Startup timeout |

### Retention Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `episodicDays` | number | 30 | Days to retain episodic memories |
| `archiveDays` | number | 365 | Days to retain archive memories |
| `defaultSearchLimit` | number | 10 | Default search results limit |

### Embeddings Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `provider` | string | `local` | Embeddings provider: `local` or `openai` |
| `model` | string | `sentence-transformers/all-MiniLM-L6-v2` | Local model name |
| `dimension` | number | 384 | Embedding dimension |
| `openaiModel` | string | `text-embedding-3-small` | OpenAI model name |
| `batchSize` | number | 32 | Batch size for embedding |

### Context Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable context retrieval |
| `maxTokens` | number | 4000 | Maximum tokens for context |
| `budgetFraction` | number | 0.5 | Budget fraction per tier |
| `includeTiers` | array | all tiers | Tiers to include |

### Pipeline Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable pipeline |
| `maxAgents` | number | 10 | Maximum concurrent agents |
| `defaultTimeoutSeconds` | number | 300 | Default timeout |

### Learning Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable learning |
| `patternDetection.trajectoryLimit` | number | 100 | Trajectories to analyze |
| `patternDetection.minSequenceLength` | number | 2 | Min tool sequence length |
| `patternDetection.minFrequency` | number | 2 | Min pattern frequency |
| `datasetGeneration.successThreshold` | number | 0.8 | Min success rate |
| `datasetGeneration.minTrajectories` | number | 100 | Min trajectories for dataset |

### Skills Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable skills |
| `autoDetect` | boolean | true | Auto-detect skill patterns |
| `detection.minPatternCount` | number | 3 | Min pattern occurrences |
| `detection.successThreshold` | number | 0.8 | Min success rate |
| `storage.directory` | string | `~/.openclaw/gnosys/skills` | Skills directory |
| `storage.maxSkills` | number | 100 | Max skills to store |

### Scheduler Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable scheduler |
| `maxConcurrent` | number | 5 | Max concurrent tasks |
| `timeoutSeconds` | number | 300 | Task timeout |

### API Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable API |
| `host` | string | `127.0.0.1` | API host |
| `port` | number | 8766 | API port |
| `auth.type` | string | `bearer` | Auth type |
| `auth.token` | string | `gnosys_api_token` | Auth token |

### Monitoring Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | true | Enable monitoring |
| `metricsPort` | number | 8767 | Metrics port |

## Environment Variables

All options can be set via environment variables:

| Variable | Description |
|----------|-------------|
| `GNOSYS_DB_PATH` | Database path |
| `GNOSYS_VECTORS_PATH` | Vector database path |
| `GNOSYS_HOST` | Backend host |
| `GNOSYS_PORT` | Backend port |
| `GNOSYS_RETENTION_EPISODIC_DAYS` | Episodic retention days |
| `GNOSYS_RETENTION_ARCHIVE_DAYS` | Archive retention days |
| `GNOSYS_EMBEDDINGS_PROVIDER` | Embeddings provider |
| `GNOSYS_EMBEDDINGS_MODEL` | Embeddings model |
| `GNOSYS_PIPELINE_ENABLED` | Enable pipeline |
| `GNOSYS_LEARNING_ENABLED` | Enable learning |
| `GNOSYS_SKILLS_ENABLED` | Enable skills |
| `GNOSYS_SCHEDULER_ENABLED` | Enable scheduler |
| `GNOSYS_API_ENABLED` | Enable API |
| `GNOSYS_MONITORING_ENABLED` | Enable monitoring |
