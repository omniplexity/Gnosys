# Gnosys v2 Roadmap - Incremental Version Specification

## Document Version: 2.0.2
## Created: 2026-04-03
## Author: Austin

## Overview

This document specifies the incremental roadmap to advance Gnosys from v1.0.0 to v2.0.0. Each version increment (1.0.x) represents a focused, testable release with 3-5 concrete deliverables.

---

## Version 1.0.1 - Local Embeddings

**Priority:** HIGH | **Target:** This weekend

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.1.1 | Install `sentence-transformers` package | `pip list \| grep sentence-transformers` |
| 1.0.1.2 | Update config: embeddings.provider = "local" | Check config JSON |
| 1.0.1.3 | Update config: embeddings.model = "all-MiniLM-L6-v2" | Check config JSON |
| 1.0.1.4 | Implement LocalEmbeddings class | Import works, no errors |
| 1.0.1.5 | Test embedding generation with sample text | Returns 384-dim vector |
| 1.0.1.6 | Verify vector storage in database | `SELECT COUNT(*) FROM vectors` > 0 |

### Dependencies
- `sentence-transformers>=2.2.0`
- `numpy>=1.24.0`

### Success Criteria
- [ ] Embeddings generate without errors
- [ ] Semantic search returns different results than keyword-only
- [ ] Vector count increments in stats

---

## Version 1.0.2 - CLI Foundation

**Priority:** HIGH | **Target:** This weekend

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.2.1 | Implement `/gnosys status` command | Returns backend URL, DB path, memory count, uptime |
| 1.0.2.2 | Implement `/gnosys help` command | Shows all commands with usage examples |
| 1.0.2.3 | Implement `/gnosys store --content <text>` | Memory appears in database |
| 1.0.2.4 | Implement `/gnosys get <id>` | Returns memory by ID |
| 1.0.2.5 | Add structured error output | Errors return code + message + suggestions |

### Dependencies
- Built on 1.0.1

### Success Criteria
- [x] All 5 commands work without errors
- [x] Help shows comprehensive usage
- [x] Errors are actionable

---

## Version 1.0.3 - Auto-Backup System

**Priority:** HIGH | **Target:** Early next week

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.3.1 | Create backup directory structure | `backups/daily`, `backups/weekly`, `backups/monthly` exist |
| 1.0.3.2 | Implement full backup to SQLite | `.gz` file created in daily folder |
| 1.0.3.3 | Implement backup checksum generation | SHA256 checksum stored |
| 1.0.3.4 | Implement restore from backup | Database restored correctly |
| 1.0.3.5 | Add backup config to `config.json` | Schedule, retention configurable |

### Dependencies
- Built on 1.0.2

### Success Criteria
- [ ] Backup creates valid compressed file
- [ ] Restore recovers all memories
- [ ] Checksum verification works

---

## Version 1.0.4 - Search & Retrieval

**Priority:** HIGH | **Target:** Early next week

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.4.1 | Implement `/gnosys search <query>` | Returns relevant memories |
| 1.0.4.2 | Implement hybrid search (keyword + semantic) | Combined results |
| 1.0.4.3 | Add `--limit` option to search | Respects limit parameter |
| 1.0.4.4 | Add `--type` and `--tier` filters | Filters work correctly |
| 1.0.4.5 | Implement `/gnosys stats` command | Shows counts by type/tier |

### Dependencies
- Built on 1.0.1, 1.0.2

### Success Criteria
- [ ] Search returns semantically similar results
- [ ] Filters correctly narrow results
- [ ] Stats match database counts

---

## Version 1.0.5 - Context Engine

**Priority:** MEDIUM | **Target:** Week 2

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.5.1 | Enable context engine in config | `config.json` has context.enabled = true |
| 1.0.5.2 | Implement ContextBuilder class | Imports without errors |
| 1.0.5.3 | Implement token trimming | Context fits within max_tokens |
| 1.0.5.4 | Add OpenClaw before_prompt hook | Context injected into prompts |
| 1.0.5.5 | Configure tier weighting | Semantic tier weighted appropriately |

### Dependencies
- Built on 1.0.4

### Success Criteria
- [ ] Relevant memories injected into prompts
- [ ] Token limit respected
- [ ] Response quality improved with context

---

## Version 1.0.6 - Memory Slot Replacement

**Priority:** MEDIUM | **Target:** Week 2

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.6.1 | Plugin loads before session creation | No race conditions |
| 1.0.6.2 | Test session persistence (restart) | Memories survive gateway restart |
| 1.0.6.3 | Configure memory slot to gnosys | `slots.memory = "gnosys"` |
| 1.0.6.4 | Implement fallback to default memory | If Gnosys fails, uses backup |
| 1.0.6.5 | Migrate existing MEMORY.md files | Import to Gnosys format |

### Dependencies
- Built on 1.0.5

### Success Criteria
- [ ] Gnosys is primary memory backend
- [ ] Sessions persist across restarts
- [ ] Fallback works if Gnosys down

---

## Version 1.0.7 - Tool Mapping

**Priority:** MEDIUM | **Target:** Week 2

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.7.1 | Register 'memory_search' → Gnosys mapping | Native tool uses Gnosys |
| 1.0.7.2 | Register 'memory_get' → Gnosys mapping | Works with ID |
| 1.0.7.3 | Register 'memory_store' → Gnosys mapping | Stores through Gnosys |
| 1.0.7.4 | Add tool aliases (gnosys.search, etc.) | Both syntaxes work |
| 1.0.7.5 | Test native `/memory search` command | Uses Gnosys backend |

### Dependencies
- Built on 1.0.6

### Success Criteria
- [ ] Native memory tools route to Gnosys
- [ ] Aliases work correctly
- [ ] No duplication of data

---

## Version 1.0.8 - Scheduled Tasks

**Priority:** MEDIUM | **Target:** Week 2-3

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.8.1 | Implement health check task (every 15 min) | Logs component status |
| 1.0.8.2 | Implement memory extraction task (on conversation end) | Extracts facts from chat |
| 1.0.8.3 | Implement memory maintenance task (daily 3 AM) | Prunes expired, vacuums DB |
| 1.0.8.4 | Implement `/gnosys schedule` command | List, add, remove tasks |
| 1.0.8.5 | Add scheduled task config to `config.json` | Cron expressions configurable |

### Dependencies
- Built on 1.0.7

### Success Criteria
- [ ] Health checks run on schedule
- [ ] Memories extracted from conversations
- [ ] Database stays optimized

---

## Version 1.0.9 - Skill Foundation

**Priority:** MEDIUM | **Target:** Week 3

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.9.1 | Configure skill auto-detection in config | auto_detect = true |
| 1.0.9.2 | Implement trajectory fetch | Get recent 100 trajectories |
| 1.0.9.3 | Implement pattern frequency analysis | Count repeated sequences |
| 1.0.9.4 | Implement skill extraction (manual trigger) | `/gnosys detect-skills` works |
| 1.0.9.5 | Implement `/gnosys skills` command | List, view skills |

### Dependencies
- Built on 1.0.8

### Success Criteria
- [ ] Can detect repeated patterns
- [ ] Skills extracted to database
- [ ] CLI shows skill list

---

## Version 1.0.10 - Learning Loop

**Priority:** MEDIUM | **Target:** Week 3

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.10.1 | Configure learning mode = "hybrid" | Config accepts mode |
| 1.0.10.2 | Implement scheduled learning (hourly) | Cron job triggers analysis |
| 1.0.10.3 | Implement triggered learning on "remember this" | Extracts user-directed memories |
| 1.0.10.4 | Implement strategy weight adaptation | Updates based on outcomes |
| 1.0.10.5 | Implement learning log | Tracks what was learned |

### Dependencies
- Built on 1.0.9

### Success Criteria
- [ ] Learning fires on schedule
- [ ] Learning fires on trigger
- [ ] Strategy weights update

---

## Version 1.0.11 - Error System Foundation

**Priority:** LOW | **Target:** Week 3-4

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.11.1 | Define error code hierarchy | Codes 1000-9999 per category |
| 1.0.11.2 | Create error registry (JSON) | Code → message, causes, fix |
| 1.0.11.3 | Implement error logging | Structured log format |
| 1.0.11.4 | Add embeddings fallback | Keyword-only if vector fails |
| 1.0.11.5 | Implement graceful degradation | System stays up on failures |

### Dependencies
- Built on 1.0.10

### Success Criteria
- [ ] Error codes are descriptive
- [ ] Fallback modes work
- [ ] Errors logged with context

---

## Version 1.0.12 - Embeddings Enhancement

**Priority:** LOW | **Target:** Week 4

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.12.1 | Implement batch embedding support | Process multiple texts at once |
| 1.0.12.2 | Add batch size config | Configurable batch_size |
| 1.0.12.3 | Optimize embedding caching | Cache frequently accessed vectors |
| 1.0.12.4 | Add model auto-download | Downloads on first use |
| 1.0.12.5 | Performance test | <500ms per embedding |

### Dependencies
- Built on 1.0.1

### Success Criteria
- [ ] Batch processing works
- [ ] Performance improved
- [ ] Cache hit rate >80%

---

## Version 1.0.13 - Database Optimization

**Priority:** LOW | **Target:** Week 4

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.13.1 | Create migrations table | Tracks schema version |
| 1.0.13.2 | Implement migration runner | Applies pending migrations |
| 1.0.13.3 | Add composite indexes | Optimizes common queries |
| 1.0.13.4 | Implement query logging | Identify slow queries |
| 1.0.13.5 | Analyze and rebuild fragmented indexes | Weekly maintenance |

### Dependencies
- Built on 1.0.12

### Success Criteria
- [ ] Migrations run on startup
- [ ] Indexes improve search speed
- [ ] Query logs actionable

---

## Version 1.0.14 - Dashboard Foundation

**Priority:** LOW | **Target:** Week 4-5

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.14.1 | Add dashboard route | `GET /gnosys/dashboard` loads |
| 1.0.14.2 | Implement overview panel | Total memories, by tier/type |
| 1.0.14.3 | Implement memory browser | Search and view memories |
| 1.0.14.4 | Implement health panel | Component status indicators |
| 1.0.14.5 | Add dark mode | Theme toggle |

### Dependencies
- Built on 1.0.13

### Success Criteria
- [ ] Dashboard loads in browser
- [ ] All panels render
- [ ] Responsive on mobile

---

## Version 1.0.15 - Visualization

**Priority:** LOW | **Target:** Week 5

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.15.1 | Implement memory timeline | Memories over time chart |
| 1.0.15.2 | Implement tier distribution | Pie chart |
| 1.0.15.3 | Implement activity graph | Recent activity |
| 1.0.15.4 | Implement skill tree view | Hierarchical skill display |
| 1.0.15.5 | Add export functionality | CSV/JSON export |

### Dependencies
- Built on 1.0.14

### Success Criteria
- [ ] Charts render correctly
- [ ] Data updates in real-time
- [ ] Exports work

---

## Version 1.0.16 - CLI Complete

**Priority:** LOW | **Target:** Week 5

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.16.1 | Implement `/gnosys delete <id>` | Removes memory |
| 1.0.16.2 | Implement `/gnosys edit <id> --content <text>` | Updates memory |
| 1.0.16.3 | Implement `/gnosys import <file>` | Bulk import |
| 1.0.16.4 | Implement `/gnosys export` | Bulk export |
| 1.0.16.5 | Add tab completion | CLI UX improvement |

### Dependencies
- Built on 1.0.15

### Success Criteria
- [ ] All CRUD operations work
- [ ] Bulk import/export work
- [ ] Tab completion fires

---

## Version 1.0.17 - /doctor Command

**Priority:** LOW | **Target:** Week 5-6

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.17.1 | Implement `/gnosys doctor` run | Executes diagnostics |
| 1.0.17.2 | Implement auto-fix attempts | Fixes common issues |
| 1.0.17.3 | Add remediation steps | Detailed instructions |
| 1.0.17.4 | Add system health scoring | /doctor gives grade |
| 1.0.17.5 | Add report export | Saves diagnostics |

### Dependencies
- Built on 1.0.11

### Success Criteria
- [ ] /doctor runs without errors
- [ ] Auto-fixes work when safe
- [ ] Remediation is actionable

---

## Version 1.0.18 - Testing & Polish

**Priority:** LOW | **Target:** Week 6

### Deliverables

| # | Task | Verification |
|---|------|---------------|
| 1.0.18.1 | Increase test coverage | Target 80%+ coverage |
| 1.0.18.2 | Add integration tests | Full flows work |
| 1.0.18.3 | Performance benchmarking | All targets met |
| 1.0.18.4 | Documentation complete | All API endpoints documented |
| 1.0.18.5 | Release v1.1.0 | Tagged release |

### Dependencies
- Built on 1.0.17

### Success Criteria
- [ ] Tests pass
- [ ] Documentation complete
- [ ] Release ready

---

## Version 1.0.19 through 1.0.x - Future Features

Reserved for features identified during development that aren't critical paths.

Potential candidates (to be prioritized):
- Recursive skill building (skills that build on skills)
- Multi-agent pipeline integration
- Voice/modal interaction support
- Cross-instance synchronization
- Encryption at rest
- Advanced analytics

---

## Version 2.0.0 - Standalone Desktop App

**Priority:** FUTURE | **Target:** Post v1.0.x

### Vision
Refactor Gnosys framework into standalone desktop application:
- Native multi-agent pipeline
- Complete OpenClaw feature set + more
- Desktop-optimized UI/UX
- Full system integration

### Prerequisites
- All v1.0.x features complete
- v1.x stable and tested
- User feedback incorporated

---

## Version Numbering Convention

```
v{Major}.{Minor}.{Patch}

Major: 2 (when standalone app releases)
Minor: Feature additions (1.0 → 1.1 → 1.2)
Patch: Bug fixes and refinements (1.0.1 → 1.0.2)
```

---

## Dependencies Graph

```
1.0.1 → 1.0.2 → 1.0.3 → 1.0.4 → 1.0.5 → 1.0.6 → 1.0.7 → 1.0.8 → 1.0.9 → 1.0.10
                          ↘_______________________________________________↗
```

---

## Quick Start Checklist

Run these in order:

- [ ] 1.0.1: Get local embeddings working
- [ ] 1.0.2: Build CLI foundation
- [ ] 1.0.3: Implement auto-backup
- [ ] 1.0.4: Complete search and retrieval
- [ ] 1.0.5: Context engine
- [ ] 1.0.6: Full memory slot replacement
- [ ] 1.0.7: Tool mapping
- [ ] 1.0.8: Scheduled tasks
- [ ] 1.0.9: Skill foundation
- [ ] 1.0.10: Learning loop
- [ ] 1.0.11: Error system foundation
- [ ] 1.0.12+: Polish and refine

---

## Notes

- Each version should take 3-7 days of development
- Test thoroughly before moving to next version
- Use version tags in git: `v1.0.1`, `v1.0.2`, etc.
- Update changelog with each release
- Prioritize based on user feedback

---

*Document maintained by Austin - Last updated 2026-04-03*