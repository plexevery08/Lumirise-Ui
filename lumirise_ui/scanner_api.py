"""Read-only scanner readiness diagnostics.

This module intentionally does not accept barcode values or call any stock,
package, Pick List, Stock Entry, or quality mutation method. It is the safe
shell required before a scanner action can be reviewed against the Phase 0
action registry and quantity contract.
"""

from __future__ import annotations

import importlib

import frappe
from frappe.utils import now_datetime

from lumirise_ui.feature_flags import is_enabled


def _task_contract_available() -> bool:
	try:
		importlib.import_module("lumirise_custom.task_contracts")
	except (ImportError, ModuleNotFoundError):
		return False
	return True


@frappe.whitelist()
@frappe.read_only()
def get_scanner_gate() -> dict:
	"""Return scanner prerequisites without accepting or processing a scan."""
	scanner_enabled = is_enabled("easy_ui_scanner_actions")
	state_actions_enabled = is_enabled("easy_ui_state_actions")
	task_contract_available = _task_contract_available()
	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"scanner_enabled": scanner_enabled,
		"state_actions_enabled": state_actions_enabled,
		"task_contract_available": task_contract_available,
		"ready_for_mutation": False,
		"blocked_reasons": [
			reason
			for reason, blocked in (
				("easy_ui_scanner_actions is disabled", not scanner_enabled),
				("easy_ui_state_actions is disabled", not state_actions_enabled),
				("lumirise_custom.task_contracts is missing", not task_contract_available),
			)
			if blocked
		],
	}
