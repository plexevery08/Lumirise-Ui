import json
from pathlib import Path

import frappe
from frappe.desk.desktop import get_workspace_sidebar_items
from frappe.tests import IntegrationTestCase

import lumirise_ui
from lumirise_ui.feature_flags import SETTINGS_DOCTYPE
from lumirise_ui.workspace_routing import (
	ROLE_WORKSPACES,
	WORKSPACE_ACCESS_ROLES,
	WORKSPACE_NAMES,
	eligible_workspaces_for_roles,
)


def _workspace_file(workspace_name: str) -> Path:
	folder = frappe.scrub(workspace_name)
	return Path(lumirise_ui.__file__).parent / "workspace" / folder / f"{folder}.json"


def _new_pilot_user(*roles: str, default_workspace: str = "Lumirise"):
	email = f"phase1a-{frappe.generate_hash(length=10).lower()}@example.com"
	return frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Phase 1A Pilot",
			"enabled": 1,
			"send_welcome_email": 0,
			"user_type": "System User",
			"default_workspace": default_workspace,
			"roles": [{"role": role} for role in roles],
		}
	).insert(ignore_permissions=True)


def _set_role_workspace_flag(value: int) -> None:
	frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_role_workspaces", value)


class TestPhaseOneWorkspaceFiles(IntegrationTestCase):
	def test_four_workspaces_are_role_restricted_hidden_and_synchronized(self):
		self.assertEqual(len(ROLE_WORKSPACES), 4)
		for sequence, spec in enumerate(ROLE_WORKSPACES, start=20):
			workspace = json.loads(_workspace_file(spec.name).read_text())
			content = json.loads(workspace["content"])
			content_shortcuts = {
				block["data"]["shortcut_name"] for block in content if block["type"] == "shortcut"
			}
			child_shortcuts = {row["label"] for row in workspace["shortcuts"]}

			self.assertEqual(workspace["name"], spec.name)
			self.assertEqual(workspace["module"], "Lumirise UI")
			self.assertEqual(workspace["app"], "lumirise_ui")
			self.assertEqual(workspace["public"], 1)
			self.assertEqual(workspace["is_hidden"], 1)
			self.assertEqual(workspace["hide_custom"], 1)
			self.assertEqual(workspace["sequence_id"], sequence)
			self.assertEqual(workspace["roles"], [{"role": spec.access_role}])
			self.assertEqual(content_shortcuts, child_shortcuts)
			self.assertTrue({block["type"] for block in content} <= {"header", "shortcut"})
			self.assertFalse(workspace["charts"])
			self.assertFalse(workspace["number_cards"])
			self.assertFalse(workspace["custom_blocks"])
			self.assertNotIn("for_user", workspace)
			self.assertTrue({row["type"] for row in workspace["shortcuts"]} <= {"DocType", "Report"})

	def test_workspace_targets_are_real_versioned_doctypes_or_reports(self):
		for spec in ROLE_WORKSPACES:
			workspace = json.loads(_workspace_file(spec.name).read_text())
			for shortcut in workspace["shortcuts"]:
				self.assertTrue(
					frappe.db.exists(shortcut["type"], shortcut["link_to"]),
					f"{spec.name}: missing {shortcut['type']} {shortcut['link_to']}",
				)

	def test_workspace_access_roles_exist_and_are_dedicated(self):
		self.assertEqual(len(WORKSPACE_ACCESS_ROLES), len(ROLE_WORKSPACES))
		for spec in ROLE_WORKSPACES:
			self.assertTrue(frappe.db.exists("Role", spec.access_role), spec.access_role)
			self.assertFalse(spec.operational_roles & WORKSPACE_ACCESS_ROLES)


class TestPhaseOneWorkspaceRouting(IntegrationTestCase):
	def test_role_mapping_is_deterministic_and_does_not_infer_unrelated_workspaces(self):
		eligible = eligible_workspaces_for_roles({"Planning User", "Purchase User"})
		self.assertEqual([spec.name for spec in eligible], ["Lumirise Planning", "Lumirise Purchase"])

	def test_flag_off_rejects_pilot_activation(self):
		user = _new_pilot_user("Planning User")
		_set_role_workspace_flag(0)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Lumirise Workspace Pilot",
					"user": user.name,
					"enabled": 1,
					"default_workspace": "Lumirise Planning",
				}
			).insert(ignore_permissions=True)

	def test_pilot_gets_only_eligible_switcher_roles_and_previous_home_is_restored(self):
		user = _new_pilot_user("Planning User", "Purchase User")
		_set_role_workspace_flag(1)
		pilot = frappe.get_doc(
			{
				"doctype": "Lumirise Workspace Pilot",
				"user": user.name,
				"enabled": 1,
				"default_workspace": "Lumirise Planning",
			}
		).insert(ignore_permissions=True)

		user.reload()
		roles = {row.role for row in user.roles}
		self.assertEqual(user.default_workspace, "Lumirise Planning")
		self.assertEqual(pilot.previous_default_workspace, "Lumirise")
		self.assertIn("Lumirise Planning Workspace", roles)
		self.assertIn("Lumirise Purchase Workspace", roles)
		self.assertNotIn("Lumirise Quality Workspace", roles)
		self.assertNotIn("Lumirise RM Stores Workspace", roles)

		previous_user = frappe.session.user
		try:
			frappe.set_user(user.name)
			visible = {page.name for page in get_workspace_sidebar_items()["pages"]}
		finally:
			frappe.set_user(previous_user)
		self.assertTrue({"Lumirise Planning", "Lumirise Purchase"} <= visible)
		self.assertFalse({"Lumirise Quality", "Lumirise RM Stores"} & visible)

		pilot.enabled = 0
		pilot.save(ignore_permissions=True)
		user.reload()
		self.assertEqual(user.default_workspace, "Lumirise")
		self.assertFalse({row.role for row in user.roles} & WORKSPACE_ACCESS_ROLES)
		self.assertTrue(pilot.restored_on)

	def test_disabling_global_flag_restores_every_active_pilot_and_hides_routes(self):
		user = _new_pilot_user("Quality Inspector")
		_set_role_workspace_flag(1)
		pilot = frappe.get_doc(
			{
				"doctype": "Lumirise Workspace Pilot",
				"user": user.name,
				"enabled": 1,
				"default_workspace": "Lumirise Quality",
			}
		).insert(ignore_permissions=True)

		settings = frappe.get_single(SETTINGS_DOCTYPE)
		settings.easy_ui_role_workspaces = 0
		settings.save(ignore_permissions=True)

		pilot.reload()
		user.reload()
		self.assertFalse(pilot.enabled)
		self.assertTrue(pilot.restored_on)
		self.assertEqual(user.default_workspace, "Lumirise")
		self.assertFalse({row.role for row in user.roles} & WORKSPACE_ACCESS_ROLES)
		for workspace_name in WORKSPACE_NAMES:
			self.assertEqual(frappe.db.get_value("Workspace", workspace_name, "is_hidden"), 1)

	def test_preexisting_workspace_role_is_not_removed_on_restore(self):
		user = _new_pilot_user("Planning User", "Lumirise Planning Workspace")
		_set_role_workspace_flag(1)
		pilot = frappe.get_doc(
			{
				"doctype": "Lumirise Workspace Pilot",
				"user": user.name,
				"enabled": 1,
				"default_workspace": "Lumirise Planning",
			}
		).insert(ignore_permissions=True)

		pilot.enabled = 0
		pilot.save(ignore_permissions=True)
		user.reload()
		self.assertIn("Lumirise Planning Workspace", {row.role for row in user.roles})
