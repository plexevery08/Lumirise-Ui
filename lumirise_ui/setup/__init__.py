"""Idempotent setup owned by the standalone Lumirise UI app.

The app owns rollout controls and navigation metadata, while ``lumirise_custom``
continues to own business DocTypes, task contracts, and state-changing handlers.
Every hook is safe to run repeatedly and remains fail-closed when the rollout
flags are absent or disabled.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from lumirise_ui.feature_flags import SETTINGS_DOCTYPE

UI_ROLLOUT_FIELDS = (
	{
		"fieldname": "sec_easy_ui_rollout",
		"fieldtype": "Section Break",
		"label": "Easy-use UI Rollout Controls",
		"insert_after": "default_plan_lead_days",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_role_workspaces",
		"fieldtype": "Check",
		"label": "Enable Role Workspaces",
		"default": "0",
		"description": "Show role-specific Workspace entry points; disabling restores pilot users and hides the routes.",
		"insert_after": "sec_easy_ui_rollout",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_my_work",
		"fieldtype": "Check",
		"label": "Enable My Work",
		"default": "0",
		"description": "Expose the read-only My Work queue.",
		"insert_after": "easy_ui_role_workspaces",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_needs_attention",
		"fieldtype": "Check",
		"label": "Enable Needs Attention",
		"default": "0",
		"description": "Expose the read-only Needs Attention queue.",
		"insert_after": "easy_ui_my_work",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_order_360",
		"fieldtype": "Check",
		"label": "Enable Order 360",
		"default": "0",
		"description": "Expose the read-only Order 360 surface when implemented.",
		"insert_after": "easy_ui_needs_attention",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_material_360",
		"fieldtype": "Check",
		"label": "Enable Material 360",
		"default": "0",
		"description": "Expose the read-only Material 360 surface when implemented.",
		"insert_after": "easy_ui_order_360",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "col_easy_ui_rollout",
		"fieldtype": "Column Break",
		"insert_after": "easy_ui_material_360",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_stock_control",
		"fieldtype": "Check",
		"label": "Enable Stock Control",
		"default": "0",
		"description": "Expose the read-only Stock Control surface when implemented.",
		"insert_after": "col_easy_ui_rollout",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_quality_queue",
		"fieldtype": "Check",
		"label": "Enable Quality Queue",
		"default": "0",
		"description": "Expose the read-only Quality Queue when implemented.",
		"insert_after": "easy_ui_stock_control",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_state_actions",
		"fieldtype": "Check",
		"label": "Enable Easy-use State Actions",
		"default": "0",
		"description": "Master kill switch for later state-changing UI actions. Off by default.",
		"insert_after": "easy_ui_quality_queue",
		"module": "Lumirise UI",
	},
	{
		"fieldname": "easy_ui_scanner_actions",
		"fieldtype": "Check",
		"label": "Enable Scanner Actions",
		"default": "0",
		"description": "Separate kill switch for later scanner mutations. Off by default.",
		"insert_after": "easy_ui_state_actions",
		"module": "Lumirise UI",
	},
)


def ensure_rollout_fields() -> None:
	"""Add only missing UI flag fields to the shared settings DocType.

	Phase 0 branches may already ship these as standard fields. The metadata
	check prevents duplicate Custom Fields in that case; on an older
	``lumirise_custom`` branch this keeps the new app independently installable
	while leaving the business app's JSON untouched.
	"""
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return

	meta = frappe.get_meta(SETTINGS_DOCTYPE, cached=False)
	missing = [field for field in UI_ROLLOUT_FIELDS if not meta.has_field(field["fieldname"])]
	if missing:
		create_custom_fields({SETTINGS_DOCTYPE: missing}, update=False)


def before_install() -> None:
	from lumirise_ui.workspace_routing import ensure_workspace_access_roles

	ensure_workspace_access_roles()


def after_install() -> None:
	after_migrate()


def before_migrate() -> None:
	from lumirise_ui.workspace_routing import ensure_workspace_access_roles

	ensure_workspace_access_roles()


def after_migrate() -> None:
	ensure_rollout_fields()
	from lumirise_ui.workspace_routing import ensure_daily_queue_shortcuts, sync_role_workspace_rollout

	sync_role_workspace_rollout()
	ensure_daily_queue_shortcuts()


def on_settings_update(doc, method=None) -> None:
	"""Apply the role-workspace kill switch immediately after settings save."""
	from lumirise_ui.workspace_routing import sync_role_workspace_rollout

	sync_role_workspace_rollout(enabled=bool(doc.get("easy_ui_role_workspaces")))
