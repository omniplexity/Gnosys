# Troubleshooting Guide

## Overview

This guide covers common issues you may encounter when running Gnosys v1.0 and how to resolve them.

## Common Issues

### Backend Connection Issues

#### Problem: Backend not responding

**Symptoms:**
- `gnosys_status` shows "unreachable"
- Health check fails

**Solutions:**
1. Check if Python backend is running:
   ```bash
   curl http://127.0.0.1:8766/health
   ```

2. If using spawn mode, check the spawn configuration in your OpenClaw config

3. Verify port 8766 is not in use:
   ```bash
   # Windows
   netstat -ano | findstr 8766
   
   # Linux/Mac
   lsof -i :8766
   ```

4. Check backend logs for errors

#### Problem: "Spawn failed" error

**Symptoms:**
- Backend process fails to start

**Solutions:**
1. Verify Python is installed:
   ```bash
   python --version
   ```

2. Install Python dependencies:
   ```bash
   pip install -e "./python[test]"
   pip install croniter
   ```

3. Check working directory path in config (default: `./python`)

### Memory Issues

#### Problem: Memory search returns no results

**Symptoms:**
- Search returns empty results even though data exists

**Solutions:**
1. Check if memories exist:
   ```bash
   curl http://127.0.0.1:8766/stats
   ```

2. Verify embeddings are enabled:
   ```json
   {
     "embeddings": {
       "provider": "local"
     }
   }
   ```

3. If using semantic search, check vector store is initialized

#### Problem: Context retrieval timeout

**Symptoms:**
- Context retrieval takes too long or times out

**Solutions:**
1. Reduce `maxTokens` in config:
   ```json
   {
     "context": {
       "maxTokens": 2000
     }
   }
   ```

2. Limit tiers included in retrieval:
   ```json
   {
     "context": {
       "includeTiers": ["working", "episodic"]
     }
   }
   ```

### Embeddings Issues

#### Problem: Semantic search falls back to keyword

**Symptoms:**
- Semantic search returns fewer results than expected

**Solutions:**
1. Check embeddings provider is enabled:
   ```json
   {
     "embeddings": {
       "provider": "local"
     }
   }
   ```

2. For local embeddings, ensure model is downloaded:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
   ```

3. Check vector database has data:
   ```bash
   curl http://127.0.0.1:8766/stats
   ```

#### Problem: OpenAI embeddings not working

**Symptoms:**
- Semantic search fails with OpenAI provider

**Solutions:**
1. Verify API key is set:
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

2. Check embedding model is available:
   ```json
   {
     "embeddings": {
       "provider": "openai",
       "openaiModel": "text-embedding-3-small"
     }
   }
   ```

### Database Issues

#### Problem: Database locked error

**Symptoms:**
- "database is locked" errors in logs

**Solutions:**
1. Ensure only one backend instance is running
2. Check for lingering processes:
   ```bash
   # Windows
   tasklist | findstr python
   
   # Linux/Mac
   ps aux | grep python
   ```
3. SQLite WAL mode is enabled by default; this should help with concurrent access

#### Problem: Database file not found

**Symptoms:**
- Cannot create or open database

**Solutions:**
1. Create data directory:
   ```bash
   mkdir -p python/data
   ```

2. Check path in config:
   ```json
   {
     "spawn": {
       "dbPath": "./python/data/gnosys.db",
       "vectorsPath": "./python/data/vectors.db"
     }
   }
   ```

### Performance Issues

#### Problem: Slow response times

**Symptoms:**
- API requests take longer than expected

**Solutions:**
1. Check monitoring metrics:
   ```bash
   curl http://127.0.0.1:8766/monitoring/metrics
   ```

2. Enable caching:
   ```json
   {
     "performance": {
       "cache": {
         "enabled": true
       }
     }
   }
   ```

3. Use batch operations for multiple inserts

### Scheduler Issues

#### Problem: Scheduled tasks not running

**Symptoms:**
- Tasks don't execute at scheduled time

**Solutions:**
1. Check scheduler is enabled:
   ```json
   {
     "scheduler": {
       "enabled": true
     }
   }
   ```

2. Verify cron syntax is valid
3. Check task is enabled:
   ```bash
   curl "http://127.0.0.1:8766/scheduled?enabled_only=true"
   ```

### Integration Issues

#### Problem: OpenClaw plugin not loading

**Symptoms:**
- Gnosys doesn't appear in available plugins

**Solutions:**
1. Verify plugin is registered in OpenClaw config:
   ```json
   {
     "plugins": {
       "slots": {
         "memory": "gnosys"
       },
       "entries": {
         "gnosys": {
           "enabled": true
         }
       }
     }
   }
   ```

2. Check TypeScript compiles:
   ```bash
   npm run check
   ```

3. Verify package.json has correct extension entry

## Diagnostic Commands

### Check Backend Health
```bash
curl http://127.0.0.1:8766/health
```

### Get Statistics
```bash
curl http://127.0.0.1:8766/stats
```

### Check Monitoring Metrics
```bash
curl http://127.0.0.1:8766/monitoring/metrics
```

### List Skills
```bash
curl http://127.0.0.1:8766/skills
```

### List Scheduled Tasks
```bash
curl http://127.0.0.1:8766/scheduled
```

### List Backups
```bash
curl http://127.0.0.1:8766/backup
```

## Getting Help

If you encounter issues not covered here:
1. Check the logs in `python/data/`
2. Review the implementation documentation
3. Run tests: `pytest python/tests`
4. Enable debug logging in config