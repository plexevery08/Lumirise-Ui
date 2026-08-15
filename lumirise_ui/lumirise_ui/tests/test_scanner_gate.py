from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from lumirise_ui import scanner_api


class TestScannerGate(IntegrationTestCase):
	def test_scanner_shell_is_always_read_only_and_blocked_without_phase_zero(self):
		with patch.object(scanner_api, "_task_contract_available", return_value=False):
			result = scanner_api.get_scanner_gate()

		self.assertTrue(result["read_only"])
		self.assertFalse(result["actions_enabled"])
		self.assertFalse(result["ready_for_mutation"])
		self.assertFalse(result["scanner_enabled"])
		self.assertFalse(result["state_actions_enabled"])
		self.assertIn("lumirise_custom.task_contracts is missing", result["blocked_reasons"])
