from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from lumirise_ui import action_readiness_api


class TestActionReadiness(IntegrationTestCase):
	def test_report_is_read_only_and_fails_closed_without_custom_contracts(self):
		with (
			patch.object(action_readiness_api, "_import_optional", return_value=None),
			patch.object(action_readiness_api, "is_enabled", return_value=False),
		):
			result = action_readiness_api.get_action_readiness()

		self.assertTrue(result["read_only"])
		self.assertFalse(result["actions_enabled"])
		self.assertFalse(result["ready_for_mutation"])
		self.assertFalse(result["registry_available"])
		self.assertFalse(result["task_contract_available"])
		self.assertFalse(result["quantity_contract_available"])
		self.assertEqual(result["actions"], [])
		self.assertIn("standalone UI mutation adapter is not implemented", result["blocked_reasons"])

	def test_registry_metadata_is_serialized_without_dispatch(self):
		class Target:
			doctype = "Stock Entry"
			permissions = ("create", "submit")

		class Contract:
			action_id = "stock.example"
			label = "Example"
			stage = "stock"
			source_doctype = "RM Package"
			authorized_roles = ("Stock User",)
			required_permission = "write"
			target_permissions = (Target(),)
			confirmation_level = "stock_quality_handoff"
			reason_required = True
			effect_summary = "Posts a stock entry."
			reversal_route = "Cancel the stock entry."
			feature_flag = "easy_ui_state_actions"
			approved_for_easy_ui = False

		class Registry:
			ACTION_REGISTRY = {"stock.example": Contract()}

		def import_optional(module_name):
			return Registry if module_name == "lumirise_custom.action_registry" else object()

		with (
			patch.object(action_readiness_api, "_import_optional", side_effect=import_optional),
			patch.object(action_readiness_api, "is_enabled", return_value=False),
		):
			result = action_readiness_api.get_action_readiness()

		action = result["actions"][0]
		self.assertEqual(action["action_id"], "stock.example")
		self.assertEqual(action["target_permissions"], [{"doctype": "Stock Entry", "permissions": ["create", "submit"]}])
		self.assertFalse(action["approved_for_easy_ui"])
		self.assertFalse(result["actions_enabled"])
