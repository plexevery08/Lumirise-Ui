import inspect
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from lumirise_ui import operational_api
from lumirise_ui.feature_flags import SETTINGS_DOCTYPE


def _set_flag(fieldname: str, value: int) -> None:
	frappe.db.set_single_value(SETTINGS_DOCTYPE, fieldname, value)


class TestPhaseOneDOperationalQueues(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		_set_flag("easy_ui_stock_control", 0)
		_set_flag("easy_ui_quality_queue", 0)

	def tearDown(self):
		_set_flag("easy_ui_stock_control", 0)
		_set_flag("easy_ui_quality_queue", 0)
		super().tearDown()

	def test_operational_queues_fail_closed_before_any_query(self):
		with patch.object(frappe, "get_list", wraps=frappe.get_list) as get_list:
			with self.assertRaises(frappe.PermissionError):
				operational_api.get_stock_control()
			with self.assertRaises(frappe.PermissionError):
				operational_api.get_quality_queue()
		self.assertFalse(get_list.called)

	def test_queue_contracts_are_explicitly_read_only(self):
		source = inspect.getsource(operational_api)
		self.assertGreaterEqual(source.count('"actions_enabled": False'), 2)
		self.assertEqual(source.count("@frappe.read_only()"), 2)
