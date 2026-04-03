from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from gnosys_backend.backup import BackupManager, RestoreManager, MigrationManager
from gnosys_backend.context_retrieval import ContextRetrievalStore
from gnosys_backend.embeddings import EmbeddingsProvider
from gnosys_backend.entity_extraction import EntityExtractor
from gnosys_backend.error_handling import ErrorHandler
from gnosys_backend.interop import InteropService, ImportFormat, ExportFormat
from gnosys_backend.learning import LearningStore
from gnosys_backend.models import (
    AgentSpawnRequest,
    AgentSpawnResponse,
    ContextRetrieveRequest,
    ContextRetrieveResponse,
    DatasetGenerateRequest,
    DatasetGenerateResponse,
    HealthResponse,
    LearningStatsResponse,
    MemoryCreateRequest,
    MemoryCreateResponse,
    MetricsResponse,
    PatternDetectRequest,
    PatternDetectResponse,
    PipelineExecuteRequest,
    PipelineExecuteResponse,
    ScheduledTaskCreateRequest,
    ScheduledTaskHistoryResponse,
    ScheduledTaskListResponse,
    ScheduledTaskRecord,
    ScheduledTaskRunResponse,
    SearchResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResult,
    SkillCreateRequest,
    SkillListResponse,
    SkillMatchRequest,
    SkillMatchResponse,
    SkillRecord,
    SkillRefineRequest,
    SkillRefineResponse,
    StatsResponse,
    TaskDelegateRequest,
    TaskDelegateResponse,
    TrajectoryCreateRequest,
    TrajectoryCreateResponse,
    TrajectoryListResponse,
    TrajectoryRecord,
    TrajectoryUpdateRequest,
    TrajectoryUpdateResponse,
)
from gnosys_backend.memory_store import MemoryStore
from gnosys_backend.monitoring import MonitoringSystem
from gnosys_backend.pipeline import PipelineStore
from gnosys_backend.scheduler import Scheduler
from gnosys_backend.skills import SkillSystem
from gnosys_backend.trajectory_store import TrajectoryStore
from gnosys_backend.vector_store import VectorStore


def create_router(
    store: MemoryStore,
    embeddings: EmbeddingsProvider,
    vectors: VectorStore,
    entities: EntityExtractor,
    context_store: ContextRetrievalStore,
    pipeline_store: PipelineStore,
    learning_store: LearningStore,
    trajectory_store: TrajectoryStore,
    skills_system: SkillSystem,
    scheduler: Scheduler,
    monitoring: MonitoringSystem,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="healthy" if store.health() else "unhealthy",
            service="gnosys-backend",
            version="0.8.0",
            database=str(store.get_stats().database_path),
        )

    @router.post("/memories", response_model=MemoryCreateResponse)
    def create_memory(request: MemoryCreateRequest) -> MemoryCreateResponse:
        memory = store.store_memory(request)

        # Store vector embedding if embeddings available
        if embeddings.is_available():
            try:
                vector = embeddings.embed(memory.content)
                vectors.store_vector(
                    memory_id=memory.id,
                    content=memory.content,
                    vector=vector,
                    metadata={
                        "memory_type": memory.memory_type,
                        "tier": memory.tier,
                        "tags": memory.tags,
                    },
                )
            except Exception:
                # Log but don't fail if embedding fails
                pass

        # Extract and store entities
        try:
            entities.extract_from_memory(memory.id, memory.content)
        except Exception:
            # Log but don't fail if entity extraction fails
            pass

        return MemoryCreateResponse(memory=memory)

    @router.get("/memories/search", response_model=SearchResponse)
    def search_memories(
        q: str = Query(min_length=1),
        limit: int | None = Query(default=None, ge=1, le=100),
        memory_type: str | None = None,
        tier: str | None = None,
    ) -> SearchResponse:
        return store.search_memories(q, limit=limit, memory_type=memory_type, tier=tier)

    @router.post("/memories/semantic-search", response_model=SemanticSearchResponse)
    def semantic_search(request: SemanticSearchRequest) -> SemanticSearchResponse:
        """Hybrid semantic + keyword search."""

        # Check if embeddings are available
        if not embeddings.is_available():
            # Fall back to keyword search
            keyword_results = store.search_memories(
                request.query,
                limit=request.limit,
                memory_type=request.memory_type,
                tier=request.tier,
            )
            results = [
                SemanticSearchResult(
                    memory=r.memory,
                    score=float(r.score),
                    keyword_score=float(r.score),
                    matched_keywords=r.matched_keywords,
                )
                for r in keyword_results.results
            ]
            return SemanticSearchResponse(
                query=request.query,
                count=len(results),
                results=results,
                used_semantic_search=False,
            )

        try:
            # Generate query embedding
            query_vector = embeddings.embed(request.query)

            # Get keyword results
            keyword_results = store.search_memories(
                request.query,
                limit=request.limit * 2,  # Get more for re-ranking
                memory_type=request.memory_type,
                tier=request.tier,
            )
            keyword_memory_ids = [r.memory.id for r in keyword_results.results]

            # Get semantic similarity results
            semantic_results = vectors.search_similar(
                query_vector,
                limit=request.limit * 2,
                memory_ids=keyword_memory_ids if keyword_memory_ids else None,
            )

            # Create lookup for keyword scores
            keyword_scores = {r.memory.id: r.score for r in keyword_results.results}

            # Combine and re-rank results
            combined: dict[str, SemanticSearchResult] = {}

            # Add keyword results
            for kr in keyword_results.results:
                kw_score = keyword_scores.get(kr.memory.id, 0)
                combined[kr.memory.id] = SemanticSearchResult(
                    memory=kr.memory,
                    score=0.0,  # Will be calculated below
                    keyword_score=float(kw_score),
                    semantic_score=None,
                    matched_keywords=kr.matched_keywords,
                )

            # Add and score semantic results
            for sr in semantic_results:
                memory_id = sr["memory_id"]
                if memory_id in combined:
                    combined[memory_id].semantic_score = sr["similarity"]
                    # Calculate combined score
                    kw = combined[memory_id].keyword_score or 0.0
                    sem = sr["similarity"]
                    kw_norm = kw / 100.0  # Normalize keyword score to 0-1
                    combined[memory_id].score = (
                        request.semantic_weight * sem
                        + (1 - request.semantic_weight) * kw_norm
                    )

            # Sort by combined score
            sorted_results = sorted(
                combined.values(),
                key=lambda x: (-x.score, x.memory.created_at, x.memory.id),
            )

            final_results = sorted_results[: request.limit]
            truncated = len(sorted_results) > request.limit

            return SemanticSearchResponse(
                query=request.query,
                count=len(final_results),
                results=final_results,
                used_semantic_search=True,
                truncated=truncated,
            )

        except Exception as e:
            # Fall back to keyword search on error
            keyword_results = store.search_memories(
                request.query,
                limit=request.limit,
                memory_type=request.memory_type,
                tier=request.tier,
            )
            results = [
                SemanticSearchResult(
                    memory=r.memory,
                    score=float(r.score),
                    keyword_score=float(r.score),
                    matched_keywords=r.matched_keywords,
                )
                for r in keyword_results.results
            ]
            return SemanticSearchResponse(
                query=request.query,
                count=len(results),
                results=results,
                used_semantic_search=False,
            )

    @router.get("/stats", response_model=StatsResponse)
    def stats() -> StatsResponse:
        return store.get_stats()

    @router.post("/context/retrieve", response_model=ContextRetrieveResponse)
    def retrieve_context(request: ContextRetrieveRequest) -> ContextRetrieveResponse:
        return context_store.retrieve(request)

    @router.get("/memories/{memory_id}", response_model=MemoryCreateResponse)
    def get_memory(memory_id: str) -> MemoryCreateResponse:
        memory = store.get_memory(memory_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        return MemoryCreateResponse(memory=memory)

    @router.delete("/memories/{memory_id}")
    def delete_memory(memory_id: str) -> dict:
        deleted = store.delete_memory(memory_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found")
        # Also delete vector if exists
        vectors.delete_vector(memory_id)
        # Also delete associated entities
        entities.delete_by_memory(memory_id)
        return {"deleted": memory_id, "success": True}

    # Entity extraction endpoints
    @router.get("/entities/memory/{memory_id}")
    def get_memory_entities(memory_id: str) -> dict:
        """Get all entities extracted from a memory."""
        memory = store.get_memory(memory_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        entity_list = entities.get_memory_entities(memory_id)
        return {"memory_id": memory_id, "entities": entity_list}

    @router.get("/entities/search")
    def search_entities(
        q: str = Query(min_length=1),
        entity_type: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
    ) -> dict:
        """Search entities by value."""
        results = entities.search(query=q, entity_type=entity_type, limit=limit)
        return {
            "query": q,
            "entity_type": entity_type,
            "count": len(results),
            "results": results,
        }

    @router.get("/entities/stats")
    def entity_stats() -> dict:
        """Get entity extraction statistics."""
        return entities.get_stats()

    # Pipeline endpoints
    @router.post("/agents/spawn", response_model=AgentSpawnResponse)
    def spawn_agent(request: AgentSpawnRequest) -> AgentSpawnResponse:
        """Spawn a sub-agent with isolated context."""
        return pipeline_store.spawn_agent(request)

    @router.post("/agents/delegate", response_model=TaskDelegateResponse)
    def delegate_task(request: TaskDelegateRequest) -> TaskDelegateResponse:
        """Delegate a task to a sub-agent."""
        return pipeline_store.delegate_task(request)

    @router.get("/agents/{agent_id}", response_model=AgentSpawnResponse)
    def get_agent(agent_id: str) -> AgentSpawnResponse:
        """Get agent by ID."""
        agent = pipeline_store.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    @router.get("/agents", response_model=list[AgentSpawnResponse])
    def list_agents(parent_id: str | None = None) -> list[AgentSpawnResponse]:
        """List active agents."""
        return pipeline_store.list_active_agents(parent_id)

    @router.get("/pipeline/agents", response_model=list[AgentSpawnResponse])
    def list_pipeline_agents(parent_id: str | None = None) -> list[AgentSpawnResponse]:
        """List active pipeline agents."""
        return pipeline_store.list_active_agents(parent_id)

    @router.post("/pipeline/execute", response_model=PipelineExecuteResponse)
    def execute_pipeline(request: PipelineExecuteRequest) -> PipelineExecuteResponse:
        """Execute a multi-agent pipeline."""
        return pipeline_store.execute_pipeline(request)

    # Learning endpoints
    @router.post("/learning/detect-patterns", response_model=PatternDetectResponse)
    def detect_patterns(request: PatternDetectRequest) -> PatternDetectResponse:
        """Detect patterns from recent trajectories."""
        return learning_store.detect_patterns(request)

    @router.post("/learning/generate-dataset", response_model=DatasetGenerateResponse)
    def generate_dataset(request: DatasetGenerateRequest) -> DatasetGenerateResponse:
        """Generate training dataset from successful trajectories."""
        return learning_store.generate_dataset(request)

    @router.get("/learning/metrics", response_model=LearningStatsResponse)
    def learning_metrics() -> LearningStatsResponse:
        """Get learning system metrics."""
        return trajectory_store.get_stats()

    @router.get("/learning/stats", response_model=LearningStatsResponse)
    def learning_stats() -> LearningStatsResponse:
        """Get learning system statistics."""
        return trajectory_store.get_stats()

    # Trajectory endpoints
    @router.post("/trajectories", response_model=TrajectoryCreateResponse)
    def create_trajectory(request: TrajectoryCreateRequest) -> TrajectoryCreateResponse:
        """Create a new trajectory record."""
        trajectory = trajectory_store.create(request)
        return TrajectoryCreateResponse(trajectory=trajectory)

    @router.put(
        "/trajectories/{trajectory_id}", response_model=TrajectoryUpdateResponse
    )
    def update_trajectory(
        trajectory_id: str, request: TrajectoryUpdateRequest
    ) -> TrajectoryUpdateResponse:
        """Update a trajectory record."""
        trajectory = trajectory_store.update(trajectory_id, request)
        if trajectory is None:
            raise HTTPException(status_code=404, detail="Trajectory not found")
        return TrajectoryUpdateResponse(trajectory=trajectory)

    @router.get("/trajectories/{trajectory_id}", response_model=TrajectoryRecord)
    def get_trajectory(trajectory_id: str) -> TrajectoryRecord:
        """Get a trajectory by ID."""
        trajectory = trajectory_store.get(trajectory_id)
        if trajectory is None:
            raise HTTPException(status_code=404, detail="Trajectory not found")
        return trajectory

    @router.get("/trajectories", response_model=TrajectoryListResponse)
    def list_trajectories(
        limit: int = Query(default=50, ge=1, le=100),
        agent_type: str | None = None,
    ) -> TrajectoryListResponse:
        """List recent trajectories."""
        return trajectory_store.list_recent(limit, agent_type)

    # ==================== Skills Endpoints ====================

    @router.get("/skills", response_model=SkillListResponse)
    async def list_skills() -> SkillListResponse:
        """List all skills."""
        return await skills_system.list_skills()

    @router.post("/skills", response_model=SkillRecord)
    async def create_skill(request: SkillCreateRequest) -> SkillRecord:
        """Create a new skill."""
        return await skills_system.extract_skill(
            name=request.name,
            tools=request.tools,
            workflow=request.workflow,
            triggers=request.triggers,
            parameters=request.parameters,
            compounds_from=request.compounds_from,
            description=request.description,
        )

    @router.get("/skills/{skill_id}", response_model=SkillRecord)
    async def get_skill(skill_id: str) -> SkillRecord:
        """Get a skill by ID."""
        skill = await skills_system.get_skill(skill_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        return skill

    @router.post("/skills/match", response_model=SkillMatchResponse)
    async def match_skill(request: SkillMatchRequest) -> SkillMatchResponse:
        """Match a task to the best skill."""
        return await skills_system.match_skill(request)

    @router.post("/skills/{skill_id}/refine", response_model=SkillRefineResponse)
    async def refine_skill(
        skill_id: str, request: SkillRefineRequest
    ) -> SkillRefineResponse:
        """Refine a skill based on feedback."""
        try:
            return await skills_system.refine_skill(skill_id, request)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.delete("/skills/{skill_id}")
    async def delete_skill(skill_id: str) -> dict:
        """Delete a skill."""
        success = await skills_system.delete_skill(skill_id)
        if not success:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"deleted": skill_id, "success": True}

    @router.get("/skills/stats")
    async def skills_stats() -> dict:
        """Get skills system statistics."""
        return await skills_system.get_skill_stats()

    # ==================== Scheduler Endpoints ====================

    @router.get("/scheduled", response_model=ScheduledTaskListResponse)
    async def list_scheduled_tasks(
        enabled_only: bool = False,
    ) -> ScheduledTaskListResponse:
        """List all scheduled tasks."""
        return await scheduler.list_tasks(enabled_only)

    @router.post("/scheduled", response_model=ScheduledTaskRecord)
    async def create_scheduled_task(
        request: ScheduledTaskCreateRequest,
    ) -> ScheduledTaskRecord:
        """Create a new scheduled task."""
        try:
            return await scheduler.create_task(request)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/scheduled/{task_id}", response_model=ScheduledTaskRecord)
    async def get_scheduled_task(task_id: str) -> ScheduledTaskRecord:
        """Get a scheduled task by ID."""
        task = await scheduler.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @router.post("/scheduled/{task_id}/run", response_model=ScheduledTaskRunResponse)
    async def run_scheduled_task(task_id: str) -> ScheduledTaskRunResponse:
        """Run a scheduled task immediately."""
        try:
            return await scheduler.run_task(task_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.delete("/scheduled/{task_id}")
    async def delete_scheduled_task(task_id: str) -> dict:
        """Delete a scheduled task."""
        success = await scheduler.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"deleted": task_id, "success": True}

    @router.get(
        "/scheduled/{task_id}/history", response_model=ScheduledTaskHistoryResponse
    )
    async def get_task_history(
        task_id: str, limit: int = 50
    ) -> ScheduledTaskHistoryResponse:
        """Get execution history for a task."""
        return await scheduler.get_task_history(task_id, limit)

    @router.get("/scheduler/stats")
    async def scheduler_stats() -> dict:
        """Get scheduler statistics."""
        return await scheduler.get_scheduler_stats()

    # ==================== Monitoring Endpoints ====================

    @router.get("/monitoring/health")
    async def monitoring_health() -> dict:
        """Get health status."""
        return await monitoring.check_health()

    @router.get("/monitoring/metrics", response_model=MetricsResponse)
    async def monitoring_metrics() -> MetricsResponse:
        """Get system metrics."""
        return await monitoring.get_metrics()

    # ==================== Backup & Recovery Endpoints ====================

    class BackupCreateRequest(BaseModel):
        backup_type: str = "full"
        components: list[str] | None = None

    class BackupListResponse(BaseModel):
        backups: list[dict]

    class RestoreRequest(BaseModel):
        backup_path: str
        target_dir: str
        components: list[str] | None = None
        overwrite: bool = False

    @router.post("/backup")
    def create_backup(request: BackupCreateRequest) -> dict:
        """Create a backup."""
        backup_mgr = BackupManager(
            db_path=store.db_path,
            vectors_path=vectors.db_path,
            skills_dir=Path("./data/skills")
            if Path("./data/skills").exists()
            else None,
        )

        if request.backup_type == "full":
            record = backup_mgr.create_full_backup()
        else:
            record = backup_mgr.create_selective_backup(
                components=request.components or ["database", "vectors"],
            )

        return {
            "id": record.id,
            "backup_type": record.backup_type,
            "components": record.components,
            "file_path": record.file_path,
            "checksum": record.checksum,
            "size_bytes": record.size_bytes,
            "created_at": record.created_at.isoformat(),
        }

    @router.get("/backup", response_model=BackupListResponse)
    def list_backups() -> BackupListResponse:
        """List all backups."""
        backup_mgr = BackupManager(
            db_path=store.db_path,
            vectors_path=vectors.db_path,
        )
        backups = backup_mgr.list_backups()
        return BackupListResponse(
            backups=[
                {
                    "id": b.id,
                    "backup_type": b.backup_type,
                    "file_path": b.file_path,
                    "size_bytes": b.size_bytes,
                    "created_at": b.created_at.isoformat(),
                }
                for b in backups
            ]
        )

    @router.get("/backup/verify/{backup_id}")
    def verify_backup(backup_id: str) -> dict:
        """Verify backup integrity."""
        backup_mgr = BackupManager(
            db_path=store.db_path,
            vectors_path=vectors.db_path,
        )
        backups = backup_mgr.list_backups()
        backup = next((b for b in backups if b.id == backup_id), None)

        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")

        result = backup_mgr.verify_backup(Path(backup.file_path))
        return {"backup_id": backup_id, "valid": result}

    @router.post("/restore")
    def restore_backup(request: RestoreRequest) -> dict:
        """Restore from a backup."""
        restore_mgr = RestoreManager(
            db_path=store.db_path,
            vectors_path=vectors.db_path,
        )

        results = restore_mgr.restore(
            backup_path=Path(request.backup_path),
            target_dir=Path(request.target_dir),
            components=request.components,
            overwrite=request.overwrite,
        )

        return {"restored": results}

    @router.get("/migrate/export")
    def migrate_export(
        format: str = Query(default="json"),
        output: str = Query(default="./data/export"),
    ) -> dict:
        """Export data for migration."""
        interop = InteropService()

        # Get all memories
        memories = store.search_memories(query="", limit=1000)

        # Export
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            path = interop.export_memories(
                memories=[m.model_dump() for m in memories],
                output_path=output_path.with_suffix(".json"),
                format=ExportFormat.JSON,
            )
        elif format == "markdown":
            path = interop.export_memories(
                memories=[m.model_dump() for m in memories],
                output_path=output_path.with_suffix(".md"),
                format=ExportFormat.MARKDOWN,
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        return {"exported_to": path, "count": len(memories)}

    @router.post("/migrate/import")
    def migrate_import(
        input_path: str = Query(),
        format: str = Query(default="json"),
    ) -> dict:
        """Import data from external source."""
        interop = InteropService()

        input_p = Path(input_path)
        if not input_p.exists():
            raise HTTPException(status_code=404, detail="Input file not found")

        # Import based on format
        try:
            import_format = ImportFormat(format)
        except ValueError:
            raise HTTPException(status_code=400, detail="Unsupported format")

        memories = interop.import_memories(input_p, import_format)

        # Store imported memories
        imported = 0
        for mem in memories:
            try:
                store.store_memory(
                    MemoryCreateRequest(
                        content=mem.get("content", ""),
                        memory_type=mem.get("type", "conversational"),
                        tier=mem.get("tier", "semantic"),
                        metadata=mem.get("metadata", {}),
                    )
                )
                imported += 1
            except Exception:
                continue

        return {"imported": imported, "total": len(memories)}

    # ==================== Error Handling Status ====================

    @router.get("/error-handler/status")
    def error_handler_status() -> dict:
        """Get error handler status."""
        error_handler = ErrorHandler()
        return error_handler.get_status()

    return router
