from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from lumirise_ui import inbound_quality_api


class TestInboundQualityBoard(IntegrationTestCase):
	def test_board_fails_closed_before_query_when_flag_is_off(self):
		with patch.object(frappe, "get_list", wraps=frappe.get_list) as get_list:
			with self.assertRaises(frappe.PermissionError):
				inbound_quality_api.get_inbound_quality_board()
		self.assertFalse(
			any(call.args and call.args[0] in {section["doctype"] for section in inbound_quality_api.BOARD_SECTIONS} for call in get_list.call_args_list)
		)

	def test_board_contract_is_read_only(self):
		self.assertEqual(inbound_quality_api.BOARD_SECTIONS[0]["doctype"], "Inbound Logistics")
		self.assertEqual(inbound_quality_api.BOARD_SECTIONS[1]["doctype"], "RM Package")
