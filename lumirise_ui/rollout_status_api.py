"""Read-only rollout diagnostics for the standalone Lumirise UI app.

The control-center endpoint deliberately exposes configuration and release
state only. It does not read business queues, mutate settings, or invoke any
operational action. This gives an administrator a visible way to verify that
the app is installed while every rollout flag remains safely disabled.
"""

from __future__ import annotations

import importlib

import frappe
from frappe.utils import now_datetime

import lumirise_ui
from lumirise_ui.feature_flags import ACTION_FLAGS, READ_SURFACE_FLAGS, all_flags


PAGE_FLAGS = {
	"lumirise-my-work": "easy_ui_my_work",
	"lumirise-needs-attention": "easy_ui_needs_attention",
	"lumirise-order-360": "easy_ui_order_360",
	"lumirise-material-360": "easy_ui_material_360",
	"lumirise-stock-control": "easy_ui_stock_control",
	"lumirise-quality-queue": "easy_ui_quality_queue",
	"lumirise-inbound-quality": "easy_ui_inbound_quality",
	"lumirise-scanner-readiness": "easy_ui_scanner_actions",
}


def _task_contract_available() -> bool:
	try:
		importlib.import_module("lumirise_custom.task_contracts")
	except (ImportError, ModuleNotFoundError):
		return False
	return True


def _page_status() -> list[dict]:
	if not frappe.db.exists("DocType", "Page"):
		return []

	return [
		{
			"name": row.name,
			"title": row.title or row.name,
			"route": f"/app/{row.name}",
			"flag": PAGE_FLAGS.get(row.name),
			"enabled": bool(all_flags().get(PAGE_FLAGS[row.name], False))
			if row.name in PAGE_FLAGS
			else True,
		}
		for row in frappe.get_list(
			"Page",
			filters={"module": "Lumirise UI"},
			fields=["name", "title"],
			order_by="name asc",
			limit=100,
		)
	]


@frappe.whitelist()
@frappe.read_only()
def get_rollout_status() -> dict:
	"""Return a deterministic, non-business-data rollout snapshot."""
	flags = all_flags()
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"app_version": lumirise_ui.__version__,
		"flags": [
			{
				"name": name,
				"kind": "action" if name in ACTION_FLAGS else "read",
				"enabled": flags[name],
			}
			for name in sorted(flags)
		],
		"pages": _page_status(),
		"gates": {
			"task_contract_available": _task_contract_available(),
			"mutation_flags_disabled": not any(flags[name] for name in ACTION_FLAGS),
			"read_surfaces_disabled_by_default": not any(
				flags[name] for name in READ_SURFACE_FLAGS
			),
		},
	}
