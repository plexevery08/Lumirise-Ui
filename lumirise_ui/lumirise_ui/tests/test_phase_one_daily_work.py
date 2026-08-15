from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

import lumirise_ui
from lumirise_ui import ui_api
from lumirise_ui.feature_flags import SETTINGS_DOCTYPE
from lumirise_ui.workspace_routing import DAILY_QUEUE_SHORTCUTS, ROLE_WORKSPACES

UI_MODULE_PATH = Path(import_module("lumirise_ui.lumirise_ui").__file__).parent


def _user(role: str):
	return frappe.get_doc(
		{
			"doctype": "User",
			"email": f"phase1b-{frappe.generate_hash(length=10).lower()}@example.com",
			"first_name": "Phase 1B Queue",
			"enabled": 1,
			"send_welcome_email": 0,
			"user_type": "System User",
			"roles": [{"role": role}],
		}
	).insert(ignore_permissions=True)


def _task(owner: str, *, title: str, severity: str, status: str = "Open", due_on=None, **values):
	doc = frappe.get_doc(
		{
			"doctype": "Lumirise Task",
			"title": title,
			"owner_user": owner,
			"severity": severity,
			"status": status,
			"due_on": due_on or add_to_date(now_datetime(), days=2),
			**values,
		}
	).insert(ignore_permissions=True)
	return doc


class TestPhaseOneDailyWork(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.original_user = frappe.session.user
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_my_work", 1)
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_needs_attention", 1)

	def tearDown(self):
		frappe.set_user(self.original_user)
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_my_work", 0)
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_needs_attention", 0)
		super().tearDown()

	def test_my_work_is_owner_scoped_and_severity_ordered(self):
		user = _user("Planning User")
		_task(user.name, title="Medium queue item", severity="Medium")
		_task(user.name, title="Critical queue item", severity="Critical")
		other = _user("Planning User")
		_task(other.name, title="Other user's critical item", severity="Critical")

		frappe.set_user(user.name)
		result = ui_api.get_my_work(view="mine")

		self.assertTrue(result["read_only"])
		self.assertFalse(result["actions_enabled"])
		self.assertEqual(
			[row["title"] for row in result["rows"][:2]], ["Critical queue item", "Medium queue item"]
		)
		self.assertNotIn("Other user's critical item", {row["title"] for row in result["rows"]})

	def test_waiting_and_blocked_views_use_task_contract_without_new_status(self):
		user = _user("Quality Inspector")
		_task(
			user.name,
			title="Future review",
			severity="High",
			status="Blocked",
			review_on=add_to_date(now_datetime(), hours=4),
			blocker_code="quality_hold",
			blocker_reason="Awaiting lab evidence.",
		)
		_task(
			user.name,
			title="Due blocker",
			severity="Critical",
			status="Blocked",
			review_on=add_to_date(now_datetime(), hours=-1),
			blocker_code="material_shortage",
			blocker_reason="Awaiting material.",
		)

		frappe.set_user(user.name)
		waiting = ui_api.get_my_work(view="waiting")
		blocked = ui_api.get_my_work(view="blocked")
		self.assertEqual([row["title"] for row in waiting["rows"]], ["Future review"])
		self.assertEqual([row["title"] for row in blocked["rows"]], ["Due blocker"])

	def test_needs_attention_uses_permission_visible_open_tasks_only(self):
		user = _user("Purchase User")
		_task(
			user.name,
			title="Visible shortage",
			severity="Critical",
			business_impact="Supplier promise at risk.",
			blocker_code="material_shortage",
			blocker_reason="No usable stock.",
		)
		other = _user("Purchase User")
		_task(other.name, title="Hidden shortage", severity="Critical")

		frappe.set_user(user.name)
		result = ui_api.get_needs_attention()
		self.assertTrue(result["read_only"])
		self.assertFalse(result["actions_enabled"])
		self.assertIn("Visible shortage", {row["title"] for row in result["rows"]})
		self.assertNotIn("Hidden shortage", {row.get("title") for row in result["rows"]})

	def test_disabled_flags_fail_closed_before_any_query(self):
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_my_work", 0)
		with self.assertRaises(frappe.PermissionError), patch.object(
			frappe, "get_list", wraps=frappe.get_list
		) as get_list:
			ui_api.get_my_work()
		self.assertFalse(
			any(call.args and call.args[0] == "Lumirise Task" for call in get_list.call_args_list)
		)

		frappe.db.set_single_value(SETTINGS_DOCTYPE, "easy_ui_needs_attention", 0)
		with self.assertRaises(frappe.PermissionError), patch.object(
			frappe, "get_list", wraps=frappe.get_list
		) as get_list:
			ui_api.get_needs_attention()
		self.assertFalse(
			any(call.args and call.args[0] == "Lumirise Task" for call in get_list.call_args_list)
		)

	def test_queue_apis_are_read_only_and_expose_no_mutation_contract(self):
		frappe.set_user("Administrator")
		with patch.object(frappe.db, "commit") as commit:
			result = ui_api.get_my_work()
		self.assertTrue(result["read_only"])
		self.assertFalse(result["actions_enabled"])
		commit.assert_not_called()

	def test_pages_are_role_restricted_and_workspace_shortcuts_are_read_only(self):
		for page_name in (page for _, page, _ in DAILY_QUEUE_SHORTCUTS):
			page = frappe.get_doc("Page", page_name)
			self.assertEqual(page.module, "Lumirise UI")
			self.assertEqual(
				{row.role for row in page.roles},
				{
					"System Manager",
					"Lumirise Operations",
					"Lumirise RM Stores Workspace",
					"Lumirise Quality Workspace",
					"Lumirise Planning Workspace",
					"Lumirise Purchase Workspace",
				},
			)

		for spec in ROLE_WORKSPACES:
			workspace = frappe.get_doc("Workspace", spec.name)
			shortcuts = {row.label: row for row in workspace.shortcuts}
			for label, page_name, _color in DAILY_QUEUE_SHORTCUTS:
				self.assertEqual(shortcuts[label].type, "Page")
				self.assertEqual(shortcuts[label].link_to, page_name)
				self.assertEqual(shortcuts[label].doc_view, "")

		page_root = UI_MODULE_PATH / "page"
		for folder in ("lumirise_my_work", "lumirise_needs_attention"):
			page_js = (page_root / folder / f"{folder}.js").read_text()
			self.assertIn("actions_enabled", page_js)
			self.assertNotIn("frappe.db.commit", page_js)
