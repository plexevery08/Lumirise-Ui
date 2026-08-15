"""Read-only Phase 1D operational queues.

These queues aggregate existing permission-filtered task, stock, and quality
records. They deliberately do not infer a new status machine and expose no
mutation or scanner action. The authoritative task contract is loaded only
after the corresponding feature flag is enabled.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from lumirise_ui.feature_flags import require_enabled
from lumirise_ui.trace_api import _available_fields, _parse_limit, _rows
from lumirise_ui.ui_api import _task_contract

TASK_FIELDS = (
	"name",
	"title",
	"status",
	"priority",
	"severity",
	"task_type",
	"department",
	"owner_user",
	"supervisor_user",
	"reference_doctype",
	"reference_name",
	"due_on",
	"due_date",
	"blocker_code",
	"blocker_reason",
	"source_event",
	"modified",
)

PRIORITY_RANK = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _sort_tasks(rows: list[dict]) -> list[dict]:
	return sorted(
		rows,
		key=lambda row: (
			SEVERITY_RANK.get(row.get("severity"), 9),
			PRIORITY_RANK.get(row.get("priority"), 9),
			row.get("due_on") or row.get("due_date") or "9999-12-31",
			row.get("modified") or "",
		),
	)


def _task_rows(extra_filters: list[list], limit: int) -> list[dict]:
	terminal_statuses, _task_view = _task_contract()
	base_filters = [["status", "not in", list(terminal_statuses)]]
	rows: dict[str, dict] = {}
	for query in extra_filters:
		for row in _rows(
			"Lumirise Task",
			base_filters + query,
			TASK_FIELDS,
			limit=limit,
			order_by="modified desc",
		):
			rows[row["name"]] = row
	return _sort_tasks(list(rows.values()))[:limit]


def _negative_bins(limit: int) -> list[dict]:
	return _rows(
		"Bin",
		[["actual_qty", "<", 0]],
		("name", "item_code", "warehouse", "actual_qty", "reserved_qty", "projected_qty", "company"),
		limit=limit,
		order_by="actual_qty asc, warehouse asc",
	)


QUALITY_SPECS = (
	(
		"Quality Inspection",
		{"Accepted", "Approved"},
		("name", "status", "inspection_type", "item_code", "item_name", "reference_type", "reference_name", "inspected_by"),
	),
	(
		"IQC",
		{"Passed", "Moved to RM", "Cancelled"},
		("name", "status", "purchase_order", "modified"),
	),
	(
		"Vendor PDI",
		{"PDI Passed", "Dispatched", "Cancelled"},
		("name", "status", "supplier", "purchase_order", "modified"),
	),
	(
		"Customer PDI",
		{"Returned to FG - Completed", "Cancelled"},
		("name", "status", "customer", "sales_order", "modified"),
	),
)


def _quality_rows(limit: int) -> list[dict]:
	rows = []
	for doctype, closed_statuses, fields in QUALITY_SPECS:
		if "status" not in _available_fields(doctype, ("status",)):
			continue
		for row in _rows(doctype, [], fields, limit=limit, order_by="modified desc"):
			if row.get("status") in closed_statuses:
				continue
			row["queue_kind"] = doctype
			rows.append(row)
	return rows[:limit]


@frappe.whitelist()
@frappe.read_only()
def get_stock_control(limit: int | str = 100) -> dict:
	"""Return open stock exception tasks and permission-visible negative bins."""
	require_enabled("easy_ui_stock_control")
	limit = _parse_limit(limit)
	stock_tasks = _task_rows(
		[
			[["task_type", "in", ["Stock Mismatch", "Defect / Rejection"]]],
			[["department", "like", "%Stores%"]],
		],
		limit,
	)
	negative_bins = _negative_bins(limit)
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"stock_tasks": stock_tasks,
		"negative_bins": negative_bins,
		"counts": {"stock_tasks": len(stock_tasks), "negative_bins": len(negative_bins)},
	}


@frappe.whitelist()
@frappe.read_only()
def get_quality_queue(limit: int | str = 100) -> dict:
	"""Return open quality tasks and pending/failed quality records."""
	require_enabled("easy_ui_quality_queue")
	limit = _parse_limit(limit)
	quality_tasks = _task_rows(
		[
			[["task_type", "in", ["Defect / Rejection", "Approval"]]],
			[["department", "like", "%Quality%"]],
		],
		limit,
	)
	quality_records = _quality_rows(limit)
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"quality_tasks": quality_tasks,
		"quality_records": quality_records,
		"counts": {"quality_tasks": len(quality_tasks), "quality_records": len(quality_records)},
	}
