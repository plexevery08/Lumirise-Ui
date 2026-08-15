import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

import lumirise_ui
from lumirise_ui import trace_api
from lumirise_ui.feature_flags import SETTINGS_DOCTYPE
from lumirise_ui.workspace_routing import OPERATIONAL_QUEUE_SHORTCUTS, TRACE_VIEW_SHORTCUTS


def _page_file(page_name: str) -> Path:
	folder = f"lumirise_{frappe.scrub(page_name)}"
	return Path(lumirise_ui.__file__).parent / "page" / folder / f"{folder}.json"


def _set_flag(fieldname: str, value: int) -> None:
	frappe.db.set_single_value(SETTINGS_DOCTYPE, fieldname, value)


class TestPhaseOneCTraceViews(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		_set_flag("easy_ui_order_360", 0)
		_set_flag("easy_ui_material_360", 0)

	def tearDown(self):
		_set_flag("easy_ui_order_360", 0)
		_set_flag("easy_ui_material_360", 0)
		super().tearDown()

	def test_trace_views_fail_closed_before_any_query(self):
		with patch.object(frappe, "get_list", wraps=frappe.get_list) as get_list:
			with self.assertRaises(frappe.PermissionError):
				trace_api.get_order_360("SO-TRACE-TEST")
			with self.assertRaises(frappe.PermissionError):
				trace_api.get_material_360("ITEM-TRACE-TEST")
		self.assertFalse(get_list.called)

	def test_pages_are_role_restricted_and_read_only(self):
		expected_roles = {
			"System Manager",
			"Lumirise Operations",
			"Lumirise RM Stores Workspace",
			"Lumirise Quality Workspace",
			"Lumirise Planning Workspace",
			"Lumirise Purchase Workspace",
		}
		for page_name, _route, _color, _flag in TRACE_VIEW_SHORTCUTS + OPERATIONAL_QUEUE_SHORTCUTS:
			page = json.loads(_page_file(page_name).read_text())
			self.assertEqual(page["module"], "Lumirise UI")
			self.assertEqual({row["role"] for row in page["roles"]}, expected_roles)

			page_js = _page_file(page_name).with_suffix(".js").read_text()
			self.assertIn("actions_enabled", page_js)
			self.assertIn("read_only", page_js)
			self.assertNotIn("frappe.db.commit", page_js)

	def test_trace_shortcuts_have_independent_flags(self):
		self.assertEqual(
			[flag for _label, _page, _color, flag in TRACE_VIEW_SHORTCUTS],
			["easy_ui_order_360", "easy_ui_material_360"],
		)
		self.assertEqual(
			[flag for _label, _page, _color, flag in OPERATIONAL_QUEUE_SHORTCUTS],
			["easy_ui_stock_control", "easy_ui_quality_queue"],
		)
