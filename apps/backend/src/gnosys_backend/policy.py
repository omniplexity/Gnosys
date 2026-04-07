from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AUTONOMY_MODES = ("Manual", "Supervised", "Autonomous", "Full Access")

MODE_ALIASES = {
    "yolo": "Full Access",
    "full access / yolo": "Full Access",
    "full access/yolo": "Full Access",
}

READ_ONLY_ACTIONS = {
    "read",
    "retrieve",
    "list",
    "search",
    "inspect",
    "view",
    "get",
}

WRITE_ACTIONS = {
    "create",
    "update",
    "patch",
    "save",
    "ingest",
    "launch",
    "schedule",
    "run",
    "write",
}

DESTRUCTIVE_ACTIONS = {
    "delete",
    "remove",
    "destroy",
    "purge",
}

EXTERNAL_SIDE_EFFECTS = {
    "push",
    "publish",
    "deploy",
    "send",
    "commit",
}


def normalize_mode(mode: str | None) -> str:
    raw = (mode or "Supervised").strip()
    if raw.lower() in MODE_ALIASES:
        return MODE_ALIASES[raw.lower()]
    candidate = raw.title()
    if candidate not in AUTONOMY_MODES:
        return "Supervised"
    return candidate


def classify_action(action: str, payload: dict[str, Any] | None = None) -> tuple[str, str]:
    pieces = [action]
    if payload:
        for key in ("objective", "title", "summary", "name", "action"):
            value = payload.get(key)
            if isinstance(value, str):
                pieces.append(value)
    lowered = " ".join(pieces).lower().strip()
    if any(token in lowered for token in DESTRUCTIVE_ACTIONS):
        return "critical", "The action deletes or destroys data."
    if any(token in lowered for token in EXTERNAL_SIDE_EFFECTS):
        return "high", "The action has an external side effect."
    if any(token in lowered for token in WRITE_ACTIONS):
        if payload and payload.get("enabled") is False:
            return "high", "The action disables an active control surface."
        return "medium", "The action mutates workspace state."
    if any(token in lowered for token in READ_ONLY_ACTIONS):
        return "low", "The action is read-only."
    return "medium", "The action is a state-changing request."


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    sensitivity: str
    reason: str
    mode: str
    action: str
    policy_scope: str
    policy_entity_type: str | None
    policy_entity_id: str | None


class PolicyEngine:
    def __init__(self, store: Any) -> None:
        self.store = store

    def snapshot(self) -> dict[str, Any]:
        workspace = self.store.get_workspace_state()
        mode = normalize_mode(workspace.get("autonomy_mode"))
        return {
            "autonomy_mode": mode,
            "kill_switch": workspace.get("kill_switch", "false").lower() == "true",
            "approval_bias": workspace.get("approval_bias", "supervised"),
            "mode_label": workspace.get("mode_label", "Global autonomy and approval policy"),
        }

    def resolve_effective_policy(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        workspace = self.snapshot()
        if entity_type and entity_id:
            entity_policy = self.store.get_entity_policy(entity_type, entity_id)
            if entity_policy is not None:
                return {**workspace, **entity_policy, "policy_scope": "entity", "policy_entity_type": entity_type, "policy_entity_id": entity_id}
        if project_id:
            project_policy = self.store.get_entity_policy("project", project_id)
            if project_policy is not None:
                return {**workspace, **project_policy, "policy_scope": "project", "policy_entity_type": "project", "policy_entity_id": project_id}
        return {**workspace, "policy_scope": "workspace", "policy_entity_type": None, "policy_entity_id": None}

    def update(self, *, autonomy_mode: str | None = None, kill_switch: bool | None = None, approval_bias: str | None = None) -> dict[str, Any]:
        updates: dict[str, str] = {}
        if autonomy_mode is not None:
            normalized_mode = normalize_mode(autonomy_mode)
            updates["autonomy_mode"] = normalized_mode
            updates["mode"] = normalized_mode
        if kill_switch is not None:
            updates["kill_switch"] = "true" if kill_switch else "false"
        if approval_bias is not None:
            updates["approval_bias"] = approval_bias.strip() or "supervised"
        if updates:
            self.store.update_workspace_state(updates)
        return self.snapshot()

    def evaluate(
        self,
        *,
        action: str,
        payload: dict[str, Any] | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        project_id: str | None = None,
        mutating: bool = True,
    ) -> PolicyDecision:
        snapshot = self.resolve_effective_policy(entity_type=entity_type, entity_id=entity_id, project_id=project_id)
        mode = snapshot["autonomy_mode"]
        kill_switch = bool(snapshot["kill_switch"])
        sensitivity, reason = classify_action(action, payload)

        if not mutating:
            return PolicyDecision(
                allowed=True,
                requires_approval=False,
                sensitivity=sensitivity,
                reason=reason,
                mode=mode,
                action=action,
                policy_scope=snapshot["policy_scope"],
                policy_entity_type=snapshot["policy_entity_type"],
                policy_entity_id=snapshot["policy_entity_id"],
            )

        if kill_switch:
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                sensitivity=sensitivity,
                reason="The kill switch is enabled.",
                mode=mode,
                action=action,
                policy_scope=snapshot["policy_scope"],
                policy_entity_type=snapshot["policy_entity_type"],
                policy_entity_id=snapshot["policy_entity_id"],
            )

        if mode == "Full Access":
            return PolicyDecision(
                allowed=True,
                requires_approval=False,
                sensitivity=sensitivity,
                reason="Full Access allows automated execution.",
                mode=mode,
                action=action,
                policy_scope=snapshot["policy_scope"],
                policy_entity_type=snapshot["policy_entity_type"],
                policy_entity_id=snapshot["policy_entity_id"],
            )

        if mode == "Manual":
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                sensitivity=sensitivity,
                reason="Manual mode requires approval for all mutations.",
                mode=mode,
                action=action,
                policy_scope=snapshot["policy_scope"],
                policy_entity_type=snapshot["policy_entity_type"],
                policy_entity_id=snapshot["policy_entity_id"],
            )

        if mode == "Supervised" and sensitivity in {"high", "critical"}:
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                sensitivity=sensitivity,
                reason=reason,
                mode=mode,
                action=action,
                policy_scope=snapshot["policy_scope"],
                policy_entity_type=snapshot["policy_entity_type"],
                policy_entity_id=snapshot["policy_entity_id"],
            )

        if mode == "Autonomous" and sensitivity == "critical":
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                sensitivity=sensitivity,
                reason="Critical actions remain gated in autonomous mode.",
                mode=mode,
                action=action,
                policy_scope=snapshot["policy_scope"],
                policy_entity_type=snapshot["policy_entity_type"],
                policy_entity_id=snapshot["policy_entity_id"],
            )

        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            sensitivity=sensitivity,
            reason=reason,
            mode=mode,
            action=action,
            policy_scope=snapshot["policy_scope"],
            policy_entity_type=snapshot["policy_entity_type"],
            policy_entity_id=snapshot["policy_entity_id"],
        )
