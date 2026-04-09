from __future__ import annotations

from .runtime import OrchestrationEngine
from .services.scheduler_service import (
    SchedulePolicyDecision,
    ScheduleRunner,
    SchedulerService,
    parse_schedule_expression,
    schedule_execution_objective,
)
from .store import GnosysStore


class ScheduleDaemon(ScheduleRunner):
    def __init__(
        self,
        store: GnosysStore,
        orchestration_engine: OrchestrationEngine,
        poll_interval_seconds: float = 5.0,
    ) -> None:
        super().__init__(
            scheduler_service=SchedulerService(store, orchestration_engine),
            poll_interval_seconds=poll_interval_seconds,
        )


__all__ = [
    "ScheduleDaemon",
    "SchedulePolicyDecision",
    "ScheduleRunner",
    "SchedulerService",
    "parse_schedule_expression",
    "schedule_execution_objective",
]
