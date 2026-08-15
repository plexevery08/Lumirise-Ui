"""Permission-aware read-only Inbound and Quality reconciliation board."""

from __future__ import annotations

from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import now_datetime

from lumirise_ui.feature_flags import require_enabled

MAX_LIMIT = 250
SYSTEM_FIELDS = frozenset(
	{"name", "owner", "creation", "modified", "modified_by", "docstatus", "parent", "parenttype", "parentfield", "idx"}
)

BOARD_SECTIONS = (
	{
		"key": "inbound_logistics",
		"title": "Inbound logistics",
		"doctype": "Inbound Logistics",
		"filters": {"status": ["in", ["Dispatched", "In Transit", "Reached Warehouse"]]},
		"fields": (
			"name",
			"status",
			"purchase_order",
			"vendor_pdi",
			"expected_arrival_date",
			"vehicle_no",
			"current_location",
			"receiving_warehouse",
		),
		"order_by": "expected_arrival_date asc, modified desc",
	},
	{
		"key": "rm_packages",
		"title": "Packages needing stores or quality follow-up",
		"doctype": "RM Package",
		"filters": {"status": ["in", ["Pending IQC", "Quarantined", "Rejected"]]},
		"fields": (
			"name",
			"package_barcode",
			"status",
			"item_code",
			"item_name",
			"quantity",
			"uom",
			"current_warehouse",
			"inbound_logistics",
			"iqc",
		),
		"order_by": "modified desc",
	},
	{
		"key": "vendor_pdi",
		"title": "Vendor PDI exceptions",
		"doctype": "Vendor PDI",
		"filters": {"status": ["in", ["PDI Scheduled", "PDI In Progress", "On Hold", "Failed"]]},
		"fields": ("name", "status", "purchase_order", "supplier", "pdi_date"),
		"order_by": "pdi_date asc, modified desc",
	},
	{
		"key": "iqc",
		"title": "IQC exceptions",
		"doctype": "IQC",
		"filters": {"status": ["in", ["IQC Received", "Testing", "On Hold", "Rejected"]]},
		"fields": ("name", "status", "inbound_logistics", "purchase_order", "iqc_date"),
		"order_by": "iqc_date asc, modified desc",
	},
)


def _parse_limit(value: int | str | None) -> int:
	try:
		return max(1, min(int(value or 100), MAX_LIMIT))
	except (TypeError, ValueError):
		return 100


def _json_value(value):
	if isinstance(value, (datetime, date)):
		return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
	return value


def _section_rows(section: dict, limit: int) -> list[dict]:
	doctype = section["doctype"]
	if not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	filters = section["filters"]
	filter_fields = set(filters)
	if any(field not in SYSTEM_FIELDS and not meta.has_field(field) for field in filter_fields):
		return []
	fields = [field for field in section["fields"] if field == "name" or meta.has_field(field)]
	if not fields:
		return []
	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by=section["order_by"],
		limit=limit,
	)
	return [
		{
			**{key: _json_value(value) for key, value in dict(row).items()},
			"doctype": doctype,
		}
		for row in rows
	]


@frappe.whitelist()
@frappe.read_only()
def get_inbound_quality_board(limit: int | str = 100) -> dict:
	"""Return permission-filtered inbound and quality exceptions only."""
	require_enabled("easy_ui_inbound_quality")
	limit = _parse_limit(limit)
	sections = []
	for definition in BOARD_SECTIONS:
		rows = _section_rows(definition, limit)
		sections.append(
			{
				"key": definition["key"],
				"title": definition["title"],
				"doctype": definition["doctype"],
				"rows": rows,
				"count": len(rows),
			}
		)
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"sections": sections,
		"total_rows": sum(section["count"] for section in sections),
	}
