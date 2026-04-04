from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from gnosys_backend.api.routes import create_router
from gnosys_backend.config import AppConfig, load_config
from gnosys_backend.context_retrieval import ContextRetrievalStore
from gnosys_backend.db import Database
from gnosys_backend.embeddings import EmbeddingsProvider, create_embeddings_provider
from gnosys_backend.entity_extraction import EntityExtractor, EntityStore
from gnosys_backend.learning import LearningStore
from gnosys_backend.memory_store import MemoryStore
from gnosys_backend.monitoring import MonitoringSystem
from gnosys_backend.plugin import GnosysPlugin, create_plugin
from gnosys_backend.pipeline import PipelineStore
from gnosys_backend.scheduler import Scheduler
from gnosys_backend.skills import SkillSystem
from gnosys_backend.trajectory_store import TrajectoryStore
from gnosys_backend.vector_store import VectorStore


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or load_config()
    db = Database(app_config.resolved_db_path())

    # Initialize Gnosys plugin for memory slot replacement
    gnosys_plugin = create_plugin(app_config, db)

    store = MemoryStore(db, app_config)

    # Initialize embeddings provider and vector store
    embeddings = create_embeddings_provider(app_config)
    vectors = VectorStore(Database(app_config.resolved_vectors_path()), app_config)

    # Initialize entity extraction
    entity_db = Database(app_config.resolved_db_path())
    entity_store = EntityStore(entity_db, app_config)
    entity_extractor = EntityExtractor(entity_store)

    # Initialize context retrieval store
    context_store = ContextRetrievalStore(
        memory_store=store,
        vector_store=vectors,
        embeddings_provider=embeddings,
        config=app_config,
    )

    # Initialize pipeline store
    pipeline_store = PipelineStore(db, app_config.pipeline)

    # Initialize learning store
    learning_store = LearningStore(db, app_config.learning)

    # Initialize trajectory store
    trajectory_store = TrajectoryStore(db, app_config)

    # Initialize skills system
    skills_system = SkillSystem(db, app_config.skills)

    # Initialize scheduler
    scheduler = Scheduler(db, app_config.scheduler)

    # Initialize monitoring
    monitoring = MonitoringSystem(db, app_config.monitoring)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.prune_expired()
        try:
            yield
        finally:
            store.close()
            vectors.close()
            entity_store.close()

    app = FastAPI(title="Gnosys Backend", version="1.0.5", lifespan=lifespan)
    app.state.config = app_config
    app.state.store = store
    app.state.embeddings = embeddings
    app.state.vectors = vectors
    app.state.entities = entity_extractor
    app.state.context_store = context_store
    app.state.pipeline_store = pipeline_store
    app.state.learning_store = learning_store
    app.state.trajectory_store = trajectory_store
    app.state.skills_system = skills_system
    app.state.scheduler = scheduler
    app.state.monitoring = monitoring
    app.include_router(
        create_router(
            store,
            embeddings,
            vectors,
            entity_extractor,
            context_store,
            pipeline_store,
            learning_store,
            trajectory_store,
            skills_system,
            scheduler,
            monitoring,
        )
    )

    return app


def main() -> None:
    config = load_config()
    uvicorn.run(
        "gnosys_backend.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        reload=False,
    )


app = create_app()


if __name__ == "__main__":
    main()
