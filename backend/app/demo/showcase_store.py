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


def _default_recipe() -> dict[str, Any]:
    return {
        "column_name": "Priority",
        "formula_kind": "threshold",
        "formula_text": '=IF(D2>=200,"Tier 1","Tier 2")',
        "fill_range": "G2:G7",
        "source_field": "employees",
        "source_column_letter": "D",
        "operator": ">=",
        "threshold": 200,
        "match_value": None,
        "true_value": "Tier 1",
        "false_value": "Tier 2",
        "output_filename": "fintech_shortlist_prepped.xlsx",
    }


def _default_workbook() -> dict[str, Any]:
    return {
        "base_headers": ["company", "model", "stage", "employees", "owner", "tag"],
        "column_added": False,
        "formula_seeded": False,
        "fill_down_done": False,
        "generated_by_tool": False,
        "current_input_name": None,
        "current_output_name": None,
    }


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
            "name": "CSV to Excel Formula Sidecar",
            "version": 1,
            "button_size": "medium",
            "primary_label": "Add code",
            "status": "observing",
            "personalization_notes": [],
            "analyst_rules": [],
            "change_log": [],
            "pending_update": None,
            "recipe": _default_recipe(),
        },
        "workbook": _default_workbook(),
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
            "tool_generated": False,
            "tool_personalized": False,
            "analyst_email_seen": False,
            "analyst_update_applied": False,
        },
    }
    return _refresh_graph(state)


def _upgrade_state(raw_state: dict[str, Any]) -> dict[str, Any]:
    state = _default_state()
    if not raw_state:
        return state

    state["current_day"] = int(raw_state.get("current_day") or state["current_day"])
    state["day_label"] = raw_state.get("day_label") or state["day_label"]
    state["history"] = list(raw_state.get("history") or [])
    state["timeline"] = list(raw_state.get("timeline") or [])

    for section in ("workflow", "tool", "inbox", "graph", "scenes", "workbook"):
        incoming = raw_state.get(section)
        if isinstance(incoming, dict):
            state[section].update(incoming)

    tool_recipe = raw_state.get("tool", {}).get("recipe") if isinstance(raw_state.get("tool"), dict) else None
    state["tool"]["recipe"] = _merge_recipe(_default_recipe(), tool_recipe)
    state["tool"]["pending_update"] = deepcopy(state["tool"].get("pending_update"))
    state["workbook"] = {
        **_default_workbook(),
        **(raw_state.get("workbook") or {}),
    }
    return _refresh_graph(state)


def _merge_recipe(base_recipe: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    recipe = deepcopy(base_recipe)
    if not isinstance(patch, dict):
        return recipe
    for key, value in patch.items():
        if value is not None:
            recipe[key] = value
    return recipe


def _suggested_change(recipe: dict[str, Any]) -> str:
    return (
        f"Add the {recipe.get('column_name', 'Priority')} column, write {recipe.get('formula_text')}, "
        "and fill it down automatically."
    )


def _append_change_log(state: dict[str, Any], *, source: str, summary: str, suggested_change: str, change_bullets: list[str]) -> None:
    state["tool"]["change_log"].insert(
        0,
        {
            "timestamp": utc_now(),
            "source": source,
            "summary": summary,
            "suggested_change": suggested_change,
            "change_bullets": change_bullets,
        },
    )


def _apply_recipe_patch(state: dict[str, Any], patch: dict[str, Any] | None) -> None:
    state["tool"]["recipe"] = _merge_recipe(state["tool"].get("recipe") or _default_recipe(), patch)


def _refresh_graph(state: dict[str, Any]) -> dict[str, Any]:
    workflow = state["workflow"]
    tool = state["tool"]
    workbook = state["workbook"]
    inbox = state["inbox"]
    scenes = state["scenes"]
    recipe = tool["recipe"]
    summary = summarize_showcase_state(state)
    tool_generated = bool(state["scenes"].get("tool_generated"))
    portal_seen = bool(scenes.get("portal_exported") or workflow["times_seen"] >= 1 or workbook.get("generated_by_tool"))
    excel_seen = bool(
        scenes.get("excel_opened")
        or scenes.get("excel_headers_done")
        or scenes.get("excel_formulas_done")
        or scenes.get("xlsx_saved")
        or workflow["times_seen"] >= 1
        or workbook.get("generated_by_tool")
    )
    memory_seen = bool(
        workflow["times_seen"] >= 1
        or workbook.get("generated_by_tool")
        or tool_generated
        or tool.get("personalization_notes")
        or inbox.get("pending_update")
    )

    nodes = [
        {"id": "bob", "label": "Bob", "kind": "person", "x": 100, "y": 180, "size": "lg"},
        {
            "id": "workflow",
            "label": workflow["name"],
            "kind": "workflow",
            "x": 305,
            "y": 168,
            "size": "xl",
            "count": workflow["times_seen"],
        },
    ]
    edges = [{"from": "bob", "to": "workflow", "label": f"{workflow['times_seen']} observed runs"}]

    if portal_seen:
        nodes.append({"id": "portal", "label": "CSV export", "kind": "step", "x": 515, "y": 88, "size": "md"})
        edges.append({"from": "workflow", "to": "portal", "label": "download CSV"})

    if excel_seen:
        nodes.append({"id": "excel", "label": "Excel cleanup", "kind": "step", "x": 520, "y": 258, "size": "md"})
        edges.append({"from": "workflow", "to": "excel", "label": "open + edit workbook"})

    if memory_seen:
        nodes.append(
            {
                "id": "memory",
                "label": "Workflow memory",
                "kind": "memory",
                "x": 770,
                "y": 168,
                "size": "lg",
                "count": workflow["times_seen"],
            }
        )
        edges.append({"from": "workflow", "to": "memory", "label": "pattern retained"})

    if workbook.get("column_added") or workbook.get("formula_seeded") or workflow["times_seen"] >= 1:
        nodes.append(
            {
                "id": "formula",
                "label": f"{recipe['column_name']} formula",
                "kind": "formula",
                "x": 740,
                "y": 70,
                "size": "md",
            }
        )
        edges.append({"from": "excel", "to": "formula", "label": "seed + drag down"})
        edges.append({"from": "formula", "to": "memory", "label": "rule remembered"})

    if tool_generated or tool["status"] in {"generated", "personalized", "updated"}:
        nodes.append(
            {
                "id": "tool",
                "label": f"{tool['name']} v{tool['version']}",
                "kind": "tool",
                "x": 995,
                "y": 168,
                "size": "lg",
            }
        )
        edges.append({"from": "memory", "to": "tool", "label": "code added"})
        if workbook.get("generated_by_tool"):
            edges.append({"from": "tool", "to": "excel", "label": "prefilled workbook"})

    if tool.get("personalization_notes"):
        nodes.append(
            {
                "id": "preference",
                "label": "Saved preference",
                "kind": "update",
                "x": 995,
                "y": 70,
                "size": "md",
            }
        )
        edges.append({"from": "tool", "to": "preference", "label": "remember for later"})
        edges.append({"from": "preference", "to": "memory", "label": "reusable preference"})

    pending_update = inbox.get("pending_update")
    if pending_update:
        nodes.append(
            {
                "id": "email",
                "label": "Analyst email",
                "kind": "email",
                "x": 770,
                "y": 325,
                "size": "md",
            }
        )
        nodes.append(
            {
                "id": "update",
                "label": "Formula update",
                "kind": "update",
                "x": 1000,
                "y": 325,
                "size": "md",
            }
        )
        edges.append({"from": "email", "to": "memory", "label": "new requirement"})
        edges.append({"from": "memory", "to": "update", "label": "pending revision"})

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
            state["timeline"].append({"timestamp": utc_now(), "action": action, "detail": detail})
            state["workflow"]["today_actions"].append(action)

            recipe_patch = detail.get("recipe_patch")
            if recipe_patch:
                _apply_recipe_patch(state, recipe_patch)

            if action == "portal_exported":
                state["scenes"]["portal_exported"] = True
                state["workbook"]["current_input_name"] = detail.get("filename")
            elif action == "excel_opened":
                state["scenes"]["excel_opened"] = True
            elif action == "excel_headers_done":
                state["scenes"]["excel_headers_done"] = True
            elif action == "excel_column_added":
                state["workbook"]["column_added"] = True
            elif action == "excel_formula_seeded":
                state["workbook"]["formula_seeded"] = True
            elif action == "excel_fill_down":
                state["workbook"]["fill_down_done"] = True
                state["scenes"]["excel_formulas_done"] = True
            elif action == "excel_formulas_done":
                state["scenes"]["excel_formulas_done"] = True
            elif action == "xlsx_saved":
                state["scenes"]["xlsx_saved"] = True
                state["workbook"]["current_output_name"] = detail.get("filename") or state["tool"]["recipe"].get("output_filename")
                if state["workflow"]["status"] != "ready":
                    state["workflow"]["status"] = "ready"
                if not state["scenes"]["tool_generated"]:
                    state["tool"]["status"] = "suggested"
                state["scenes"]["tool_suggested"] = True
                if not detail.get("skip_count"):
                    state["workflow"]["times_seen"] += 1
                    state["history"].append(
                        {
                            "day": state["day_label"],
                            "label": "Observed one full CSV-to-Excel cleanup pass, including the added formula column.",
                            "kind": "workflow-observation",
                        }
                    )
            elif action == "tool_used":
                state["workbook"]["generated_by_tool"] = True
                state["workbook"]["column_added"] = True
                state["workbook"]["formula_seeded"] = True
                state["workbook"]["fill_down_done"] = True
                state["scenes"]["tool_generated"] = True
                state["tool"]["status"] = "updated" if state["scenes"].get("analyst_update_applied") else "generated"
                state["workbook"]["current_input_name"] = detail.get("input_name") or state["workbook"].get("current_input_name")
                state["workbook"]["current_output_name"] = detail.get("output_name") or state["tool"]["recipe"].get("output_filename")

            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def advance_day(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            state["current_day"] += 1
            day_map = {2: "Thursday, Apr 17", 3: "Friday, Apr 18"}
            state["day_label"] = day_map.get(state["current_day"], f"Day {state['current_day']}")
            state["workflow"]["today_actions"] = []
            for key in ["portal_exported", "excel_opened", "excel_headers_done", "excel_formulas_done", "xlsx_saved"]:
                state["scenes"][key] = False
            state["workbook"] = {
                **state["workbook"],
                "column_added": False,
                "formula_seeded": False,
                "fill_down_done": False,
                "generated_by_tool": False,
                "current_input_name": None,
                "current_output_name": None,
            }
            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def fast_track_excel(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            recipe = state["tool"]["recipe"]
            state["timeline"].append(
                {
                    "timestamp": utc_now(),
                    "action": "excel_fast_track",
                    "detail": {
                        "column_name": recipe["column_name"],
                        "formula_text": recipe["formula_text"],
                    },
                }
            )
            state["workflow"]["today_actions"].append("excel_fast_track")
            state["scenes"]["excel_opened"] = True
            state["scenes"]["excel_headers_done"] = True
            state["scenes"]["excel_formulas_done"] = True
            state["workbook"]["column_added"] = True
            state["workbook"]["formula_seeded"] = True
            state["workbook"]["fill_down_done"] = True
            state = _refresh_graph(state)
            self._save_unlocked(state)
            return deepcopy(state)

    def generate_tool(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_unlocked()
            state["scenes"]["tool_generated"] = True
            state["tool"]["status"] = "generated"
            state["tool"]["primary_label"] = "Convert CSV to workbook"
            if not state["tool"]["change_log"]:
                recipe = state["tool"]["recipe"]
                _append_change_log(
                    state,
                    source="Vim",
                    summary="Observed the manual workbook cleanup and generated a reusable CSV-to-Excel helper.",
                    suggested_change=_suggested_change(recipe),
                    change_bullets=[
                        "Watch for a raw CSV drop",
                        f"Write the {recipe['column_name']} column automatically",
                        f"Seed {recipe['formula_text']} and fill it down",
                    ],
                )
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
                    "tool_generated": state["scenes"].get("tool_generated"),
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
                    "tool_generated": state["scenes"].get("tool_generated"),
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
                "recipe_patch": update.get("recipe_patch") or {},
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
                        "recipe_patch": pending.get("recipe_patch") or {},
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
        state["scenes"]["tool_generated"] = True
        _apply_recipe_patch(state, update.get("recipe_patch"))
        _append_change_log(
            state,
            source=request_source,
            summary=update["summary"],
            suggested_change=update["suggested_change"],
            change_bullets=update["change_bullets"],
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
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        upgraded = _upgrade_state(raw)
        if upgraded != raw:
            self._save_unlocked(upgraded)
        return deepcopy(upgraded)

    def _save_unlocked(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")
