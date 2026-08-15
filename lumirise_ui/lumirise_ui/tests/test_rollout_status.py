from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from lumirise_ui import rollout_status_api


class TestRolloutStatus(IntegrationTestCase):
	def test_status_is_read_only_and_reports_disabled_gates(self):
		with patch.object(rollout_status_api, "_task_contract_available", return_value=False):
			result = rollout_status_api.get_rollout_status()

		self.assertTrue(result["read_only"])
		self.assertFalse(result["actions_enabled"])
		self.assertEqual(result["app_version"], "0.3.0")
		self.assertFalse(result["gates"]["task_contract_available"])
		self.assertTrue(result["gates"]["mutation_flags_disabled"])
		self.assertTrue(result["gates"]["read_surfaces_disabled_by_default"])
		page_names = {row["name"] for row in result["pages"]}
		self.assertIn("lumirise-my-work", page_names)
		if frappe.db.exists("Page", "lumirise-ui-control-center"):
			self.assertIn("lumirise-ui-control-center", page_names)
		self.assertTrue(all(not flag["enabled"] for flag in result["flags"]))
