"""Native, reversible role-Workspace routing for the Phase 1A shell.

Frappe v16 already routes a Desk user through ``User.default_workspace`` and
uses the permitted public Workspaces as its switcher.  This module confines the
custom behavior to rollout eligibility, a dedicated access role per Workspace,
and restoration of the user's previous default.  No business-document action is
exposed here.
"""

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import now_datetime

from lumirise_ui.feature_flags import is_enabled, require_enabled


@dataclass(frozen=True, slots=True)
class RoleWorkspace:
	key: str
	name: str
	access_role: str
	operational_roles: frozenset[str]


ROLE_WORKSPACES = (
	RoleWorkspace(
		key="rm_stores",
		name="Lumirise RM Stores",
		access_role="Lumirise RM Stores Workspace",
		operational_roles=frozenset({"Factory Store Manager", "Stock Manager", "Stock User"}),
	),
	RoleWorkspace(
		key="quality",
		name="Lumirise Quality",
		access_role="Lumirise Quality Workspace",
		operational_roles=frozenset({"Quality User", "Quality Inspector", "Quality Manager"}),
	),
	RoleWorkspace(
		key="planning",
		name="Lumirise Planning",
		access_role="Lumirise Planning Workspace",
		operational_roles=frozenset({"Planning User", "Planning Manager"}),
	),
	RoleWorkspace(
		key="purchase",
		name="Lumirise Purchase",
		access_role="Lumirise Purchase Workspace",
		operational_roles=frozenset({"Purchase User", "Purchase Manager", "Purchase Head"}),
	),
)

WORKSPACE_BY_NAME = {spec.name: spec for spec in ROLE_WORKSPACES}
WORKSPACE_NAMES = frozenset(WORKSPACE_BY_NAME)
WORKSPACE_ACCESS_ROLES = frozenset(spec.access_role for spec in ROLE_WORKSPACES)

DAILY_QUEUE_SHORTCUTS = (
	("My Work", "lumirise-my-work", "Blue"),
	("Needs Attention", "lumirise-needs-attention", "Red"),
)

TRACE_VIEW_SHORTCUTS = (
	("Order 360", "lumirise-order-360", "Blue", "easy_ui_order_360"),
	("Material 360", "lumirise-material-360", "Green", "easy_ui_material_360"),
)


def ensure_workspace_access_roles() -> None:
	"""Create the dedicated pilot roles before Workspace metadata is imported."""
	for role_name in sorted(WORKSPACE_ACCESS_ROLES):
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)


def ensure_daily_queue_shortcuts() -> None:
	"""Add the Phase 1B read-only pages to each shipped role workspace.

	The workspace files remain the stable base navigation contract.  This small
	idempotent reconciliation keeps the page links synchronized after standard
	Workspace JSON is imported, and is safe to run while both queue flags are off.
	"""
	if not frappe.db.exists("DocType", "Workspace"):
		return

	for spec in ROLE_WORKSPACES:
		if not frappe.db.exists("Workspace", spec.name):
			continue
		workspace = frappe.get_doc("Workspace", spec.name)
		content = frappe.parse_json(workspace.content or "[]")
		if not isinstance(content, list):
			content = []
		child_labels = {row.label for row in workspace.shortcuts}
		content_labels = {
			block.get("data", {}).get("shortcut_name") for block in content if block.get("type") == "shortcut"
		}
		changed = False

		for index, (label, page_name, color) in enumerate(DAILY_QUEUE_SHORTCUTS, start=1):
			if not frappe.db.exists("Page", page_name):
				continue
			if label not in child_labels:
				workspace.append(
					"shortcuts",
					{
						"label": label,
						"link_to": page_name,
						"type": "Page",
						"color": color,
						"doc_view": "",
					},
				)
				child_labels.add(label)
				changed = True
			if label not in content_labels:
				content.append(
					{
						"id": f"lr{spec.key}daily{index}",
						"type": "shortcut",
						"data": {"shortcut_name": label, "col": 3},
					}
				)
				content_labels.add(label)
				changed = True

		if changed:
			workspace.content = frappe.as_json(content)
			workspace.save(ignore_permissions=True)


def ensure_trace_view_shortcuts() -> None:
	"""Reconcile optional trace links without exposing them while flags are off."""
	if not frappe.db.exists("DocType", "Workspace"):
		return

	managed = {label: (page_name, color, flag) for label, page_name, color, flag in TRACE_VIEW_SHORTCUTS}
	for spec in ROLE_WORKSPACES:
		if not frappe.db.exists("Workspace", spec.name):
			continue
		workspace = frappe.get_doc("Workspace", spec.name)
		content = frappe.parse_json(workspace.content or "[]")
		if not isinstance(content, list):
			content = []
		changed = False

		for row in tuple(workspace.shortcuts):
			definition = managed.get(row.label)
			if definition and (not is_enabled(definition[2]) or row.link_to != definition[0]):
				workspace.remove(row)
				changed = True

		filtered_content = []
		for block in content:
			label = block.get("data", {}).get("shortcut_name") if isinstance(block, dict) else None
			definition = managed.get(label)
			if definition and not is_enabled(definition[2]):
				changed = True
				continue
			filtered_content.append(block)
		content = filtered_content

		child_labels = {row.label for row in workspace.shortcuts}
		content_labels = {
			block.get("data", {}).get("shortcut_name")
			for block in content
			if isinstance(block, dict) and block.get("type") == "shortcut"
		}
		for index, (label, page_name, color, flag) in enumerate(TRACE_VIEW_SHORTCUTS, start=1):
			if not is_enabled(flag) or not frappe.db.exists("Page", page_name):
				continue
			if label not in child_labels:
				workspace.append(
					"shortcuts",
					{
						"label": label,
						"link_to": page_name,
						"type": "Page",
						"color": color,
						"doc_view": "",
					},
				)
				child_labels.add(label)
				changed = True
			if label not in content_labels:
				content.append(
					{
						"id": f"{spec.key}trace{index}",
						"type": "shortcut",
						"data": {"shortcut_name": label, "col": 3},
					}
				)
				content_labels.add(label)
				changed = True

		if changed:
			workspace.content = frappe.as_json(content)
			workspace.save(ignore_permissions=True)


def eligible_workspaces_for_roles(roles) -> tuple[RoleWorkspace, ...]:
	"""Return the stable Workspace order for a set of operational roles."""
	role_set = frozenset(roles or ())
	return tuple(spec for spec in ROLE_WORKSPACES if spec.operational_roles & role_set)


def eligible_workspaces_for_user(user: str) -> tuple[RoleWorkspace, ...]:
	return eligible_workspaces_for_roles(frappe.get_roles(user))


def validate_pilot_assignment(user: str, default_workspace: str) -> tuple[RoleWorkspace, ...]:
	require_enabled("easy_ui_role_workspaces")
	user_doc = frappe.get_doc("User", user)
	if not user_doc.enabled or user_doc.user_type != "System User":
		frappe.throw(_("Workspace pilots must be enabled System Users."), frappe.ValidationError)

	eligible = eligible_workspaces_for_roles(row.role for row in user_doc.roles)
	eligible_names = {spec.name for spec in eligible}
	if not eligible:
		frappe.throw(
			_("The pilot has none of the operational roles required by the Phase 1A Workspaces."),
			frappe.PermissionError,
		)
	if default_workspace not in eligible_names:
		frappe.throw(
			_("The selected default Workspace is not authorized by the pilot's operational roles."),
			frappe.PermissionError,
		)
	return eligible


def _parse_granted_roles(value) -> set[str]:
	parsed = frappe.parse_json(value) if value else []
	if not isinstance(parsed, list):
		return set()
	return {role for role in parsed if role in WORKSPACE_ACCESS_ROLES}


def _set_pilot_state(pilot, values: dict) -> None:
	for fieldname, value in values.items():
		pilot.set(fieldname, value)
	if pilot.name and frappe.db.exists(pilot.doctype, pilot.name):
		frappe.db.set_value(pilot.doctype, pilot.name, values, update_modified=False)


def set_role_workspace_visibility(enabled: bool) -> None:
	"""Synchronize the flag to Frappe's server-provided Workspace sidebar."""
	if not frappe.db.exists("DocType", "Workspace"):
		return

	hidden = 0 if enabled else 1
	for workspace_name in WORKSPACE_NAMES:
		if frappe.db.exists("Workspace", workspace_name):
			frappe.db.set_value("Workspace", workspace_name, "is_hidden", hidden, update_modified=False)
	frappe.clear_cache()


def activate_pilot(pilot) -> None:
	"""Grant only eligible shell roles and record the previous native home."""
	eligible = validate_pilot_assignment(pilot.user, pilot.default_workspace)
	set_role_workspace_visibility(True)

	user_doc = frappe.get_doc("User", pilot.user)
	current_roles = {row.role for row in user_doc.roles}
	previously_granted = _parse_granted_roles(pilot.granted_workspace_roles)
	desired_roles = {spec.access_role for spec in eligible}

	for row in tuple(user_doc.roles):
		if row.role in previously_granted - desired_roles:
			user_doc.roles.remove(row)

	added_now = desired_roles - current_roles
	user_doc.append_roles(*sorted(added_now))
	tracked_roles = (previously_granted & desired_roles) | added_now

	new_activation = not pilot.activated_on or bool(pilot.restored_on)
	previous_default = user_doc.default_workspace if new_activation else pilot.previous_default_workspace
	user_doc.default_workspace = pilot.default_workspace
	user_doc.save(ignore_permissions=True)

	_set_pilot_state(
		pilot,
		{
			"previous_default_workspace": previous_default or None,
			"assigned_workspace": pilot.default_workspace,
			"granted_workspace_roles": frappe.as_json(sorted(tracked_roles)),
			"activated_on": now_datetime() if new_activation else pilot.activated_on,
			"restored_on": None,
		},
	)
	frappe.clear_cache(user=pilot.user)


def deactivate_pilot(pilot) -> None:
	"""Remove roles granted by this record and restore its captured home."""
	if not pilot.activated_on or pilot.restored_on:
		return

	user_doc = frappe.get_doc("User", pilot.user)
	granted_roles = _parse_granted_roles(pilot.granted_workspace_roles)
	for row in tuple(user_doc.roles):
		if row.role in granted_roles:
			user_doc.roles.remove(row)

	if user_doc.default_workspace in WORKSPACE_NAMES:
		previous = pilot.previous_default_workspace
		user_doc.default_workspace = (
			previous if previous and frappe.db.exists("Workspace", previous) else None
		)
	user_doc.save(ignore_permissions=True)

	_set_pilot_state(pilot, {"restored_on": now_datetime()})
	frappe.clear_cache(user=pilot.user)


def deactivate_all_role_workspace_pilots() -> int:
	if not frappe.db.exists("DocType", "Lumirise Workspace Pilot"):
		return 0

	names = frappe.get_all(
		"Lumirise Workspace Pilot",
		filters={"enabled": 1},
		pluck="name",
	)
	for name in names:
		pilot = frappe.get_doc("Lumirise Workspace Pilot", name)
		pilot.enabled = 0
		pilot.save(ignore_permissions=True)
	return len(names)


def sync_role_workspace_rollout(enabled: bool | None = None) -> dict[str, int | bool]:
	"""Apply the flag as a fail-closed route and assignment kill switch."""
	rollout_enabled = is_enabled("easy_ui_role_workspaces") if enabled is None else bool(enabled)
	deactivated = 0
	if not rollout_enabled:
		deactivated = deactivate_all_role_workspace_pilots()
	set_role_workspace_visibility(rollout_enabled)
	return {"enabled": rollout_enabled, "deactivated_pilots": deactivated}


def prepare_role_workspace_rollback() -> dict[str, int | bool]:
	"""Bench-callable Level 2 rollback: restore homes, roles, and old routes."""
	deactivated = deactivate_all_role_workspace_pilots()
	set_role_workspace_visibility(False)
	return {"enabled": False, "deactivated_pilots": deactivated}
