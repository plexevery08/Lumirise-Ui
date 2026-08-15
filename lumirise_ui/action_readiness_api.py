"""Read-only diagnostics for the future registry-driven action UI.

The standalone UI app must not copy business action handlers from
``lumirise_custom``.  Instead it inspects the custom app's Phase 0 registry
when that contract is installed and reports why an action is (or is not) safe
to expose.  This endpoint never dispatches a registry method and always keeps
the mutation gate closed; a later release can add an adapter only after the
server-side registry and rollback tests are approved.
"""

from __future__ import annotations

import importlib

import frappe
from frappe.utils import now_datetime

from lumirise_ui.feature_flags import is_enabled


def _import_optional(module_name: str):
	try:
		return importlib.import_module(module_name)
	except (ImportError, ModuleNotFoundError):
		return None


def _contract_summary(contract) -> dict:
	"""Serialize only review metadata from a custom-app registry contract."""
	targets = []
	for target in getattr(contract, "target_permissions", ()) or ():
		targets.append(
			{
				"doctype": getattr(target, "doctype", ""),
				"permissions": list(getattr(target, "permissions", ()) or ()),
			}
		)
	return {
		"action_id": getattr(contract, "action_id", None),
		"label": getattr(contract, "label", ""),
		"stage": getattr(contract, "stage", ""),
		"source_doctype": getattr(contract, "source_doctype", None),
		"authorized_roles": list(getattr(contract, "authorized_roles", ()) or ()),
		"required_permission": getattr(contract, "required_permission", None),
		"target_permissions": targets,
		"confirmation_level": getattr(contract, "confirmation_level", ""),
		"reason_required": bool(getattr(contract, "reason_required", False)),
		"effect_summary": getattr(contract, "effect_summary", ""),
		"reversal_route": getattr(contract, "reversal_route", ""),
		"feature_flag": getattr(contract, "feature_flag", None),
		"approved_for_easy_ui": bool(getattr(contract, "approved_for_easy_ui", False)),
	}


def _registry_snapshot() -> tuple[bool, list[dict], str | None]:
	registry = _import_optional("lumirise_custom.action_registry")
	if registry is None:
		return False, [], "lumirise_custom.action_registry is missing"

	try:
		actions = [
			_contract_summary(contract)
			for _, contract in sorted(
				(registry.ACTION_REGISTRY or {}).items(), key=lambda item: item[0]
			)
		]
	except (AttributeError, TypeError, ValueError):
		return False, [], "the custom action registry is not readable"
	return True, actions, None


@frappe.whitelist()
@frappe.read_only()
def get_action_readiness() -> dict:
	"""Return registry metadata and a fail-closed mutation readiness report."""
	registry_available, actions, registry_error = _registry_snapshot()
	task_contract_available = _import_optional("lumirise_custom.task_contracts") is not None
	quantity_contract_available = _import_optional("lumirise_custom.quantity_contracts") is not None
	state_actions_enabled = is_enabled("easy_ui_state_actions")
	scanner_actions_enabled = is_enabled("easy_ui_scanner_actions")
	approved_actions = [action for action in actions if action["approved_for_easy_ui"]]

	blocked_reasons = []
	if not registry_available:
		blocked_reasons.append(registry_error or "action registry is unavailable")
	if not task_contract_available:
		blocked_reasons.append("lumirise_custom.task_contracts is missing")
	if not quantity_contract_available:
		blocked_reasons.append("lumirise_custom.quantity_contracts is missing")
	if not state_actions_enabled:
		blocked_reasons.append("easy_ui_state_actions is disabled")
	if not scanner_actions_enabled:
		blocked_reasons.append("easy_ui_scanner_actions is disabled")
	if not approved_actions:
		blocked_reasons.append("no action is approved for easy-use UI")
	blocked_reasons.append("standalone UI mutation adapter is not implemented")

	return {
		"read_only": True,
		"actions_enabled": False,
		"generated_at": now_datetime().isoformat(sep=" "),
		"ready_for_mutation": False,
		"registry_available": registry_available,
		"registry_error": registry_error,
		"task_contract_available": task_contract_available,
		"quantity_contract_available": quantity_contract_available,
		"state_actions_enabled": state_actions_enabled,
		"scanner_actions_enabled": scanner_actions_enabled,
		"approved_action_count": len(approved_actions),
		"blocked_reasons": blocked_reasons,
		"actions": actions,
	}
