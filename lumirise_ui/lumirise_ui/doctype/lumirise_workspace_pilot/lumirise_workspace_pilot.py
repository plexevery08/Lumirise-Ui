# Copyright (c) 2026, riddhi solanki and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from lumirise_ui.workspace_routing import (
	activate_pilot,
	deactivate_pilot,
	validate_pilot_assignment,
)


class LumiriseWorkspacePilot(Document):
	def validate(self):
		if self.enabled:
			validate_pilot_assignment(self.user, self.default_workspace)

	def on_update(self):
		if self.enabled:
			activate_pilot(self)
		else:
			deactivate_pilot(self)

	def on_trash(self):
		deactivate_pilot(self)
