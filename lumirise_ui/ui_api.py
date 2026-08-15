"""Read-only Phase 1B queue APIs.

These methods are intentionally whitelisted only for reads.  They apply the
existing DocType permission boundary through ``frappe.get_list`` and never
create, update, assign, share, submit, cancel, or post a business document.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

from lumirise_ui.feature_flags import require_enabled

TASK_FIELDS = (
	"name",
	"title",
	"status",
	"priority",
	"severity",
	"task_type",
	"department",
	"source_department",
	"next_department",
	"owner_user",
	"due_on",
	"due_date",
	"business_impact",
	"blocker_code",
	"blocker_reason",
	"review_on",
	"reference_doctype",
	"reference_name",
	"source_event",
	"escalated",
	"creation",
	"modified",
)

SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _task_contract():
	"""Load the Phase 0 contract only when a queue is actually enabled.

	This keeps the standalone UI app importable on an older custom-app checkout,
	while still refusing to serve data until the authoritative business contract
	is installed. It prevents a partial installation from silently guessing task
	status semantics.
	"""
	try:
		from lumirise_custom.task_contracts import TERMINAL_STATUSES, task_view
	except ModuleNotFoundError:
		frappe.throw(
			_("Lumirise UI requires the Phase 0 task contract from lumirise_custom."),
			frappe.PermissionError,
		)
	return TERMINAL_STATUSES, task_view


def _parse_limit(limit: int | str | None, default: int = 100, maximum: int = 250) -> int:
	try:
		return max(1, min(int(limit or default), maximum))
	except (TypeError, ValueError):
		return default


def _parse_horizon(horizon: int | str | None, default: int = 7, maximum: int = 90) -> int:
	try:
		return max(0, min(int(horizon or default), maximum))
	except (TypeError, ValueError):
		return default


def _iso(value) -> str | None:
	if not value:
		return None
	return get_datetime(value).isoformat(sep=" ")


def _age_days(creation, now: datetime) -> int:
	if not creation:
		return 0
	return max(0, (now - get_datetime(creation)).days)


def _task_row(row, now: datetime, task_view_fn) -> dict:
	as_dict = getattr(row, "as_dict", None)
	result = as_dict() if callable(as_dict) else dict(row)
	result["due_on"] = _iso(result.get("due_on"))
	result["review_on"] = _iso(result.get("review_on"))
	result["creation"] = _iso(result.get("creation"))
	result["modified"] = _iso(result.get("modified"))
	result["view"] = task_view_fn(row.get("status"), row.get("review_on"), now=now)
	result["age_days"] = _age_days(row.get("creation"), now)
	result["source_label"] = (
		f"{row.get('reference_doctype')}: {row.get('reference_name')}"
		if row.get("reference_doctype") and row.get("reference_name")
		else "No linked source"
	)
	return result


def _sort_rows(rows: list, now: datetime) -> list:
	return sorted(
		rows,
		key=lambda row: (
			SEVERITY_RANK.get(getattr(row, "severity", None) or row.get("severity"), 9),
			get_datetime(getattr(row, "due_on", None) or row.get("due_on") or "9999-12-31"),
			get_datetime(getattr(row, "creation", None) or row.get("creation") or now),
		),
	)


def _task_filters(
	*,
	user: str,
	view: str,
	department: str | None,
	task_type: str | None,
	horizon: int,
	terminal_statuses,
):
	now = now_datetime()
	filters = []
	if view in {"mine", "due_today", "overdue", "blocked", "waiting", "completed"}:
		filters.append(["owner_user", "=", user])
	if department:
		filters.append(["department", "=", department])
	if task_type:
		filters.append(["task_type", "=", task_type])

	if view == "completed":
		filters.append(["status", "in", list(terminal_statuses)])
	elif view in {"mine", "due_today", "overdue", "blocked", "waiting"}:
		filters.append(["status", "not in", list(terminal_statuses)])
	else:
		filters.append(["status", "not in", list(terminal_statuses)])

	if view == "due_today":
		filters.extend(
			[
				["due_on", ">=", now.replace(hour=0, minute=0, second=0, microsecond=0)],
				["due_on", "<", now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)],
			]
		)
	elif view == "overdue":
		filters.append(["due_on", "<", now])
	elif view in {"blocked", "waiting"}:
		filters.append(["status", "=", "Blocked"])
	elif view in {"mine", "all"}:
		filters.append(["due_on", "<", add_to_date(now, days=horizon)])

	return filters


def _validate_view(view: str | None, allowed: set[str]) -> str:
	view = (view or "mine").strip().lower()
	if view not in allowed:
		frappe.throw(_("Unknown queue view: {0}").format(view), frappe.ValidationError)
	return view


@frappe.whitelist()
@frappe.read_only()
def get_my_work(
	view: str = "mine",
	department: str | None = None,
	task_type: str | None = None,
	horizon: int | str = 7,
	limit: int | str = 100,
) -> dict:
	"""Return the current user's permission-filtered task queue."""
	require_enabled("easy_ui_my_work")
	terminal_statuses, task_view_fn = _task_contract()
	view = _validate_view(view, {"mine", "due_today", "overdue", "blocked", "waiting", "completed"})
	now = now_datetime()
	rows = frappe.get_list(
		"Lumirise Task",
		filters=_task_filters(
			user=frappe.session.user,
			view=view,
			department=department,
				task_type=task_type,
				horizon=_parse_horizon(horizon),
				terminal_statuses=terminal_statuses,
			),
		fields=list(TASK_FIELDS),
		order_by="due_on asc, modified desc",
		limit=_parse_limit(limit),
	)
	if view == "blocked":
		rows = [
			row for row in rows if task_view_fn(row.get("status"), row.get("review_on"), now=now) == "blocked"
		]
	elif view == "waiting":
		rows = [
			row for row in rows if task_view_fn(row.get("status"), row.get("review_on"), now=now) == "waiting"
		]
	rows = _sort_rows(rows, now)
	return {
		"view": view,
		"generated_at": now.isoformat(sep=" "),
		"read_only": True,
		"actions_enabled": False,
		"count": len(rows),
		"rows": [_task_row(row, now, task_view_fn) for row in rows],
	}


def _attention_task_rows(now: datetime, limit: int, terminal_statuses, task_view_fn) -> list[dict]:
	"""Aggregate only open tasks visible through the normal permission query."""
	rows = frappe.get_list(
		"Lumirise Task",
		filters=[["status", "not in", list(terminal_statuses)]],
		fields=list(TASK_FIELDS),
		order_by="due_on asc, creation asc",
		limit=limit,
	)
	result = []
	for row in rows:
		view = task_view_fn(row.get("status"), row.get("review_on"), now=now)
		if (
			row.get("severity") not in {"High", "Critical"}
			and view not in {"blocked"}
			and not row.get("escalated")
		):
			continue
		item = _task_row(row, now, task_view_fn)
		item["reason_bucket"] = (
			"overdue approval" if row.get("escalated") else row.get("blocker_code") or "operational exception"
		)
		item["next_action"] = (
			"Open Source" if row.get("reference_doctype") and row.get("reference_name") else "Review Task"
		)
		result.append(item)
	return sorted(
		result,
		key=lambda row: (
			SEVERITY_RANK.get(row.get("severity"), 9),
			row.get("age_days", 0),
		),
	)


def _attention_health_rows(now: datetime, limit: int) -> list[dict]:
	if not frappe.has_permission("Health Check Run", ptype="read"):
		return []
	last = frappe.get_list(
		"Health Check Run",
		fields=["name", "run_datetime", "overall_status", "summary"],
		order_by="run_datetime desc",
		limit=1,
	)
	if not last or last[0].overall_status not in {"Amber", "Red"}:
		return []
	return [
		{
			"name": last[0].name,
			"severity": "Critical" if last[0].overall_status == "Red" else "High",
			"problem": f"Latest health check is {last[0].overall_status}",
			"business_impact": last[0].summary,
			"source_label": f"Health Check Run: {last[0].name}",
			"owner_user": None,
			"age_days": _age_days(last[0].run_datetime, now),
			"reason_bucket": "system health",
			"next_action": "Open Source",
			"read_only": True,
		}
	][:limit]


@frappe.whitelist()
@frappe.read_only()
def get_needs_attention(
	department: str | None = None,
	task_type: str | None = None,
	limit: int | str = 100,
) -> dict:
	"""Return a permission-aware exception aggregate without another status store."""
	require_enabled("easy_ui_needs_attention")
	terminal_statuses, task_view_fn = _task_contract()
	limit = _parse_limit(limit)
	now = now_datetime()
	rows = _attention_task_rows(now, limit, terminal_statuses, task_view_fn)
	if department:
		rows = [row for row in rows if row.get("department") == department]
	if task_type:
		rows = [row for row in rows if row.get("task_type") == task_type]
	rows.extend(_attention_health_rows(now, max(0, limit - len(rows))))
	rows.sort(
		key=lambda row: (
			SEVERITY_RANK.get(row.get("severity"), 9),
			row.get("age_days", 0),
		)
	)
	return {
		"generated_at": now.isoformat(sep=" "),
		"read_only": True,
		"actions_enabled": False,
		"count": len(rows[:limit]),
		"rows": rows[:limit],
		"sources": ["Lumirise Task", "Health Check Run"],
	}
