from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.demo_brain import plan_showcase_tool_update, summarize_showcase_state


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_state() -> dict[str, Any]:
    state = {
        "current_day": 1,
        "day_label": "Wednesday, Apr 16",
        "workflow": {
            "slug": "finance-export-cleanup",
            "name": "Fintech shortlist prep",
            "times_seen": 0,
            "status": "observing",
            "today_actions": [],
        },
        "history": [],
        "tool": {
            "id": "workflow-finance-cleanup",
            "name": "Workbook Prep Sidecar",
            "version": 1,
            "button_size": "medium",
            "primary_label": "Prepare workbook",
            "status": "learning",
            "personalization_notes": [],
            "analyst_rules": [],
            "change_log": [],
            "pending_update": None,
        },
        "inbox": {
            "messages": [],
            "pending_update": None,
            "last_sync_at": None,
            "sync_status": "idle",
        },
        "timeline": [],
        "graph": {
            "nodes": [],
            "edges": [],
            "headline": "",
            "graph_note": "",
            "ai_caption": "",
            "tool_summary": "",
            "pending_update_summary": "",
        },
        "scenes": {
            "portal_exported": False,
            "excel_opened": False,
            "excel_headers_done": False,
            "excel_formulas_done": False,
            "xlsx_saved": False,
            "tool_suggested": False,
            "tool_personalized": False,
            "analyst_email_seen": False,
            "analyst_update_applied": False,
        },
    }
    return _refresh_graph(state)


def _refresh_graph(state: dict[str, Any]) -> dict[str, Any]:
    workflow = state["workflow"]
    tool = state["tool"]
    inbox = state["inbox"]
    summary = summarize_showcase_state(state)

    nodes = [
        {"id": "bob", "label": "Bob", "kind": "person", "x": 90, "y": 170, "size": "lg"},
        {
            "id": "workflow",
            "label": workflow["name"],
            "kind": "workflow",
            "x": 290,
            "y": 160,
            "size": "xl",
            "count": workflow["times_seen"],
        },
        {
            "id": "portal",
            "label": "Deal portal",
            "kind": "step",
            "x": 510,
            "y": 90,
            "size": "md",
        },
        {
            "id": "excel",
            "label": "Excel prep",
            "kind": "step",
            "x": 520,
            "y": 235,
            "size": "md",
        },
        {
            "id": "memory",
            "label": "Workflow memory",
            "kind": "memory",
            "x": 750,
            "y": 160,
            "size": "lg",
            "count": workflow["times_seen"],
        },
    ]
    edges = [
        {"from": "bob", "to": "workflow", "label": f"{workflow['times_seen']} observed runs"},
        {"from": "workflow", "to": "portal", "label": "select + export CSV"},
        {"from": "workflow", "to": "excel", "label": "rename + formula + save"},
        {"from": "workflow", "to": "memory", "label": "context retained"},
    ]

    if tool["status"] in {"ready", "personalized", "updated"}:
        nodes.append(
            {
                "id": "tool",
                "label": f"{tool['name']} v{tool['version']}",
                "kind": "tool",
                "x": 960,
                "y": 160,
                "size": "lg",
            }
        )
        edges.append({"from": "memory", "to": "tool", "label": "helper generated"})

    pending_update = inbox.get("pending_update")
    if pending_update:
        nodes.append(
            {
                "id": "email",
                "label": "Analyst email",
                "kind": "email",
                "x": 740,
                "y": 310,
                "size": "md",
            }
        )
        nodes.append(
            {
                "id": "update",
                "label": "Suggested workflow update",
                "kind": "update",
                "x": 965,
                "y": 310,
                "size": "md",
            }
        )
        edges.append({"from": "email", "to": "memory", "label": "new requirement"})
        edges.append({"from": "memory", "to": "update", "label": "apply to helper"})

    state["graph"] = {
        "nodes": nodes,
        "edges": edges,
        "headline": summary["headline"],
        "graph_note": summary["graph_note"],
        "ai_caption": summary["ai_caption"],
        "tool_summary": summary["tool_summary"],
        "pending_update_summary": summary["pending_update_summary"],
    }
    return state


class ShowcaseDemoStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            return self._load_unlocked()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            state = _default_state()
            self._save_unlocked(state)
            return deepcopy(state)

    def record_action(self, action: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            detail = detail or {}
            state["timeline"].append(
                {
                    "timestamp": utc_now(),
                    "action": action,
                    "detail": detail,
                }
            )

            today_actions: list[str] = state["workflow"]["today_actions"]
            today_actions.append(action)

            if action == "portal_exported":
                state["scenes"]["portal_exported"] = True
            elif action == "excel_opened":
                state["scenes"]["excel_opened"] = True
            elif action == "excel_headers_done":
                state["scenes"]["excel_headers_done"] = True
            elif action == "excel_formulas_done":
                state["scenes"]["excel_formulas_done"] = True
            elif action == "xlsx_saved":
                state["scenes"]["xlsx_saved"] = True
                state["workflow"]["times_seen"] += 1
                state["history"].append(
                    {
                        "day": state["day_label"],
                        "label": "Observed one full finance export cleanup pass.",
                        "kind": "workflow-observation",
                    }
                )
                if state["workflow"]["times_seen"] >= 1:
                    state["workflow"]["status"] = "ready"
                    state["tool"]["status"] = "ready"
                    state["scenes"]["tool_suggested"] = True
            elif action == "tool_opened":
                state["tool"]["status"] = "ready"
            elif action == "tool_used":
                state["tool"]["status"] = "ready"

            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def advance_day(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            state["current_day"] += 1
            day_map = {
                2: "Thursday, Apr 17",
                3: "Friday, Apr 18",
            }
            state["day_label"] = day_map.get(state["current_day"], f"Day {state['current_day']}")
            state["workflow"]["today_actions"] = []
            for key in ["portal_exported", "excel_opened", "excel_headers_done", "excel_formulas_done", "xlsx_saved"]:
                state["scenes"][key] = False
            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def personalize_tool(self, request: str) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            update = plan_showcase_tool_update(
                {
                    "source": "user",
                    "request": request,
                    "tool": state["tool"],
                }
            )
            self._apply_tool_update(state, update, request_source="Bob")
            state["scenes"]["tool_personalized"] = True
            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def inject_email(self, message: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            inbox_message = {
                "id": message.get("id") or f"msg-{len(state['inbox']['messages']) + 1}",
                "from": message.get("from") or "financial.analyst@acme-capital.com",
                "subject": message.get("subject") or "Workflow change request",
                "body": message.get("body") or "",
                "received_at": message.get("received_at") or utc_now(),
                "status": "unread",
            }
            state["inbox"]["messages"].insert(0, inbox_message)
            state["inbox"]["last_sync_at"] = utc_now()
            state["scenes"]["analyst_email_seen"] = True

            update = plan_showcase_tool_update(
                {
                    "source": "email",
                    "request": f"{inbox_message['subject']}\n\n{inbox_message['body']}".strip(),
                    "tool": state["tool"],
                    "pending_email": inbox_message,
                }
            )
            pending = {
                "message_id": inbox_message["id"],
                "summary": update["summary"],
                "suggested_change": update["suggested_change"],
                "button_size": update["button_size"],
                "primary_label": update["primary_label"],
                "change_bullets": update["change_bullets"],
                "graph_note": update["graph_note"],
            }
            state["inbox"]["pending_update"] = pending
            state["tool"]["pending_update"] = pending
            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def apply_pending_update(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            pending = state["tool"].get("pending_update")
            if pending:
                self._apply_tool_update(
                    state,
                    {
                        "summary": pending["summary"],
                        "suggested_change": pending["suggested_change"],
                        "button_size": pending["button_size"],
                        "primary_label": pending["primary_label"],
                        "change_bullets": pending["change_bullets"],
                        "graph_note": pending["graph_note"],
                    },
                    request_source="Financial analyst",
                )
                state["inbox"]["pending_update"] = None
                state["tool"]["pending_update"] = None
                state["scenes"]["analyst_update_applied"] = True
            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def _apply_tool_update(self, state: dict[str, Any], update: dict[str, Any], *, request_source: str) -> None:
        state["tool"]["version"] += 1
        state["tool"]["button_size"] = update["button_size"]
        state["tool"]["primary_label"] = update["primary_label"]
        state["tool"]["status"] = "updated" if request_source == "Financial analyst" else "personalized"
        state["tool"]["change_log"].insert(
            0,
            {
                "timestamp": utc_now(),
                "source": request_source,
                "summary": update["summary"],
                "suggested_change": update["suggested_change"],
                "change_bullets": update["change_bullets"],
            },
        )
        if request_source == "Bob":
            state["tool"]["personalization_notes"].insert(0, update["suggested_change"])
        else:
            state["tool"]["analyst_rules"].insert(0, update["suggested_change"])

    def _load_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            state = _default_state()
            self._save_unlocked(state)
            return deepcopy(state)
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_unlocked(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")
