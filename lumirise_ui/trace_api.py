"""Read-only Phase 1C trace views.

The trace surfaces intentionally compose permission-filtered ERPNext lists. They
do not call the business application's mutation handlers, write trace fields, or
create a second source of truth. Every endpoint has its own feature flag and
returns an explicit read-only contract for the client.
"""

from __future__ import annotations

from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from lumirise_ui.feature_flags import require_enabled

MAX_LIMIT = 250
SYSTEM_FIELDS = frozenset(
	{"name", "owner", "creation", "modified", "modified_by", "docstatus", "parent", "parenttype", "parentfield", "idx"}
)


def _parse_limit(value: int | str | None, default: int = 100) -> int:
	try:
		return max(1, min(int(value or default), MAX_LIMIT))
	except (TypeError, ValueError):
		return default


def _required_name(value: str | None, label: str) -> str:
	name = (value or "").strip()
	if not name or len(name) > 140:
		frappe.throw(_("Enter a valid {0}.").format(label), frappe.ValidationError)
	return name


def _available_fields(doctype: str, candidates: tuple[str, ...]) -> list[str]:
	if not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	return [field for field in candidates if field == "name" or meta.has_field(field)]


def _filter_field_names(filters) -> set[str]:
	if isinstance(filters, dict):
		return set(filters)
	if isinstance(filters, (list, tuple)):
		return {row[0] for row in filters if isinstance(row, (list, tuple)) and row}
	return set()


def _json_value(value):
	if isinstance(value, (datetime, date)):
		return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
	return value


def _json_row(row: dict, *, doctype: str | None = None) -> dict:
	result = {key: _json_value(value) for key, value in dict(row).items()}
	if doctype:
		result["doctype"] = doctype
	return result


def _rows(
	doctype: str,
	filters,
	fields: tuple[str, ...],
	*,
	limit: int,
	order_by: str = "name asc",
) -> list[dict]:
	if not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	if any(field not in SYSTEM_FIELDS and not meta.has_field(field) for field in _filter_field_names(filters)):
		return []
	available = _available_fields(doctype, fields)
	if not available:
		return []
	return [
		_json_row(row, doctype=doctype)
		for row in frappe.get_list(
			doctype,
			filters=filters,
			fields=available,
			order_by=order_by,
			limit=limit,
		)
	]


def _one(doctype: str, name: str, fields: tuple[str, ...]) -> dict | None:
	rows = _rows(doctype, {"name": name}, fields, limit=1)
	return rows[0] if rows else None


def _split_refs(value: str | None) -> set[str]:
	return {part.strip() for part in (value or "").split(",") if part.strip()}


def _csv_linked_rows(
	doctype: str,
	fieldname: str,
	name: str,
	fields: tuple[str, ...],
	*,
	limit: int,
) -> list[dict]:
	if fieldname not in _available_fields(doctype, (fieldname,)):
		return []
	rows = _rows(
		doctype,
		[[fieldname, "like", f"%{name}%"]],
		fields,
		limit=limit,
	)
	return [row for row in rows if name in _split_refs(row.get(fieldname))]


def _order_links(order_name: str, *, limit: int) -> dict[str, list[dict]]:
	"""Resolve links without bypassing document permissions.

	The business traceability resolver is intentionally not called here: it uses
	``get_all`` for stamping and is not a suitable UI visibility boundary. These
	queries use ``get_list`` throughout and therefore retain the current user's
	ERPNext permissions.
	"""
	linked = {
		"indents": _rows(
			"Indent",
			{"source_sales_order": order_name},
			("name", "status", "source_sales_order", "lr_source_indent", "lr_source_wo", "lr_source_po"),
			limit=limit,
		),
		"work_orders": _rows(
			"Work Order",
			{"sales_order": order_name},
			("name", "status", "item_name", "qty", "sales_order", "lr_source_po"),
			limit=limit,
		),
		"purchase_orders": _csv_linked_rows(
			"Purchase Order",
			"lr_source_so",
			order_name,
			("name", "supplier", "status", "transaction_date", "grand_total", "lr_source_so", "lr_indent_refs"),
			limit=limit,
		),
		"purchase_receipts": _csv_linked_rows(
			"Purchase Receipt",
			"lr_source_so",
			order_name,
			("name", "supplier", "status", "posting_date", "grand_total", "lr_source_so"),
			limit=limit,
		),
		"delivery_notes": _csv_linked_rows(
			"Delivery Note",
			"lr_source_so",
			order_name,
			("name", "customer", "status", "posting_date", "grand_total", "lr_source_so"),
			limit=limit,
		),
		"sales_invoices": _csv_linked_rows(
			"Sales Invoice",
			"lr_source_so",
			order_name,
			("name", "customer", "status", "posting_date", "grand_total", "lr_source_so"),
			limit=limit,
		),
	}

	# A purchase order may be stamped with its consolidated Indent refs before
	# the SO trace panel is restamped. Include those permission-filtered rows too.
	indent_names = [row["name"] for row in linked["indents"]]
	for indent_name in indent_names:
		for row in _csv_linked_rows(
			"Purchase Order",
			"lr_indent_refs",
			indent_name,
			("name", "supplier", "status", "transaction_date", "grand_total", "lr_source_so", "lr_indent_refs"),
			limit=limit,
		):
			if row["name"] not in {item["name"] for item in linked["purchase_orders"]}:
				linked["purchase_orders"].append(row)

	return linked


@frappe.whitelist()
@frappe.read_only()
def get_order_360(sales_order: str, limit: int | str = 100) -> dict:
	"""Return a permission-aware, read-only Sales Order journey."""
	require_enabled("easy_ui_order_360")
	order_name = _required_name(sales_order, "Sales Order")
	limit = _parse_limit(limit)
	order = _one(
		"Sales Order",
		order_name,
		("name", "customer", "transaction_date", "delivery_date", "status", "grand_total", "company"),
	)
	if not order:
		frappe.throw(_("Sales Order {0} was not found or is not readable.").format(order_name), frappe.DoesNotExistError)

	items = _rows(
		"Sales Order Item",
		{"parent": order_name, "parenttype": "Sales Order"},
		("name", "item_code", "item_name", "qty", "uom", "delivery_date", "warehouse"),
		limit=limit,
		order_by="idx asc",
	)
	linked = _order_links(order_name, limit=limit)
	counts = {key: len(rows) for key, rows in linked.items()}
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"sales_order": order,
		"items": items,
		"linked": linked,
		"counts": counts,
	}


@frappe.whitelist()
@frappe.read_only()
def get_material_360(item_code: str, limit: int | str = 100) -> dict:
	"""Return permission-filtered stock and recent movement facts for an Item."""
	require_enabled("easy_ui_material_360")
	item_name = _required_name(item_code, "Item")
	item = _one(
		"Item",
		item_name,
		("name", "item_code", "item_name", "stock_uom", "is_stock_item", "has_batch_no", "description"),
	)
	if not item:
		# Item names normally equal item_code, but accepting the explicit code keeps
		# the lookup usable on sites with a custom autoname.
		item_rows = _rows(
			"Item",
			{"item_code": item_name},
			("name", "item_code", "item_name", "stock_uom", "is_stock_item", "has_batch_no", "description"),
			limit=1,
		)
		item = item_rows[0] if item_rows else None
	if not item:
		frappe.throw(_("Item {0} was not found or is not readable.").format(item_name), frappe.DoesNotExistError)

	resolved_code = item.get("item_code") or item["name"]
	bins = _rows(
		"Bin",
		{"item_code": resolved_code},
		("name", "warehouse", "actual_qty", "reserved_qty", "projected_qty", "reserved_qty_for_production"),
		limit=limit,
		order_by="warehouse asc",
	)
	ledger = _rows(
		"Stock Ledger Entry",
		{"item_code": resolved_code},
		("name", "posting_date", "actual_qty", "warehouse", "voucher_type", "voucher_no", "company"),
		limit=limit,
		order_by="posting_date desc, creation desc",
	)

	tasks = _rows(
		"Lumirise Task",
		{"reference_doctype": "Item", "reference_name": item["name"]},
		("name", "title", "status", "priority", "severity", "owner_user", "due_on", "reference_name"),
		limit=limit,
		order_by="modified desc",
	)
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"item": item,
		"stock": {
			"bins": bins,
			"total_actual_qty": sum(flt(row.get("actual_qty")) for row in bins),
			"total_reserved_qty": sum(flt(row.get("reserved_qty")) for row in bins),
			"total_projected_qty": sum(flt(row.get("projected_qty")) for row in bins),
		},
		"recent_movements": ledger,
		"tasks": tasks,
	}
