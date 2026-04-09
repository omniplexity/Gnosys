from __future__ import annotations

from fastapi import HTTPException

from ..store import GnosysStore


class ReplayService:
    def __init__(self, store: GnosysStore) -> None:
        self.store = store

    def build_replay_timeline(self, task_run_id: str) -> list[dict[str, object]]:
        task_run = self.store.get_task_run(task_run_id)
        if task_run is None:
            raise HTTPException(status_code=404, detail="Task run not found")
        timeline: list[dict[str, object]] = [
            {
                "kind": "task_run",
                "label": task_run["status"],
                "detail": task_run["summary"],
                "created_at": task_run["created_at"],
                "source_id": task_run["id"],
            }
        ]
        for agent_run in self.store.list_agent_runs(task_run_id=task_run_id, limit=100):
            timeline.append(
                {
                    "kind": f"agent:{agent_run['run_kind']}",
                    "label": agent_run["agent_name"],
                    "detail": agent_run["summary"],
                    "created_at": agent_run["created_at"],
                    "source_id": agent_run["id"],
                }
            )
        for schedule_run in self.store.list_schedule_runs(limit=100, task_run_id=task_run_id):
            timeline.append(
                {
                    "kind": "schedule_run",
                    "label": schedule_run["schedule_name"],
                    "detail": schedule_run["result_summary"],
                    "created_at": schedule_run["created_at"],
                    "source_id": schedule_run["id"],
                }
            )
        for event in self.store.list_replay_events(task_run_id=task_run_id):
            timeline.append(
                {
                    "kind": "event",
                    "label": event["type"],
                    "detail": event["source"],
                    "created_at": event["created_at"],
                    "source_id": str(event["id"]),
                }
            )
        timeline.sort(key=lambda item: str(item["created_at"]))
        return timeline

    def compare_runs(self, task_run_id: str) -> dict[str, object] | None:
        task_run = self.store.get_task_run(task_run_id)
        if task_run is None:
            return None
        history = [run for run in self.store.list_task_runs(limit=50) if run["task_id"] == task_run["task_id"]]
        previous = next((run for run in history if run["id"] != task_run_id), None)
        current_agent_runs = self.store.list_agent_runs(task_run_id=task_run_id, limit=100)
        current_schedule_runs = self.store.list_schedule_runs(limit=100, task_run_id=task_run_id)
        current_timeline = self.build_replay_timeline(task_run_id)
        if previous is None:
            return {
                "previous_task_run_id": None,
                "status_changed": False,
                "summary_changed": False,
                "step_count_delta": 0,
                "approval_required_changed": False,
                "task_summary_changed": False,
                "agent_run_count_delta": len(current_agent_runs),
                "schedule_run_count_delta": len(current_schedule_runs),
                "timeline_entry_count_delta": len(current_timeline),
            }
        previous_task = self.store.get_task(previous["task_id"])
        previous_agent_runs = self.store.list_agent_runs(task_run_id=previous["id"], limit=100)
        previous_schedule_runs = self.store.list_schedule_runs(limit=100, task_run_id=previous["id"])
        previous_timeline = self.build_replay_timeline(previous["id"])
        return {
            "previous_task_run_id": previous["id"],
            "status_changed": previous["status"] != task_run["status"],
            "summary_changed": previous["summary"] != task_run["summary"],
            "step_count_delta": int(task_run["step_count"]) - int(previous["step_count"]),
            "approval_required_changed": bool(previous["approval_required"]) != bool(task_run["approval_required"]),
            "task_summary_changed": (previous_task["summary"] if previous_task else "") != (self.store.get_task(task_run["task_id"]) or {}).get("summary", ""),
            "agent_run_count_delta": len(current_agent_runs) - len(previous_agent_runs),
            "schedule_run_count_delta": len(current_schedule_runs) - len(previous_schedule_runs),
            "timeline_entry_count_delta": len(current_timeline) - len(previous_timeline),
        }

    def run_matches_query(self, task_run: dict[str, object], query: str) -> bool:
        normalized = query.strip().lower()
        if not normalized:
            return True
        task = self.store.get_task(str(task_run["task_id"]))
        project = self.store.get_project(str(task_run.get("project_id"))) if task_run.get("project_id") else None
        project_thread = self.store.get_project_thread(str(task_run.get("project_thread_id"))) if task_run.get("project_thread_id") else None
        chat_session = self.store.get_chat_session(str(task_run.get("chat_session_id"))) if task_run.get("chat_session_id") else None
        agent_runs = self.store.list_agent_runs(task_run_id=str(task_run["id"]), limit=100)
        haystack = " ".join(
            [
                str(task_run.get("objective", "")),
                str(task_run.get("summary", "")),
                str(task_run.get("status", "")),
                str(task_run.get("mode", "")),
                str(task.get("title", "")) if task is not None else "",
                str(task.get("summary", "")) if task is not None else "",
                str(task.get("priority", "")) if task is not None else "",
                str(project.get("name", "")) if project is not None else "",
                str(project_thread.get("title", "")) if project_thread is not None else "",
                str(chat_session.get("title", "")) if chat_session is not None else "",
                " ".join(str(run.get("agent_name", "")) for run in agent_runs),
                " ".join(str(run.get("summary", "")) for run in agent_runs),
            ]
        ).lower()
        return normalized in haystack

    def diagnostics_metrics(self, task_runs: list[dict[str, object]], *, filtered_count: int) -> dict[str, object]:
        completed = sum(1 for run in task_runs if str(run.get("status")) == "Completed")
        failed = sum(1 for run in task_runs if str(run.get("status")) == "Failed")
        approval_required = sum(1 for run in task_runs if bool(run.get("approval_required")))
        return {
            "total_task_runs": self.store.count_task_runs(),
            "filtered_task_runs": filtered_count,
            "total_agent_runs": self.store.count_agent_runs(),
            "total_schedule_runs": self.store.count_schedule_runs(),
            "completed_task_runs": completed,
            "failed_task_runs": failed,
            "approval_required_task_runs": approval_required,
        }
