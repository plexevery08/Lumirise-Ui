frappe.pages["lumirise-action-readiness"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Action Readiness"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$(`<p class="text-muted">${__("Read-only inventory of the server-authoritative action registry. No action can be run from this page.")}</p>`).appendTo(page.main);
	wrapper.lumirise_page = { page, body: $("<div></div>").appendTo(page.main) };
};

function add_status_table(parent, result) {
	const table = $("<table class='table table-bordered'></table>").appendTo(parent);
	[
		[__("Mutation adapter"), __("Not implemented")],
		[__("Action registry"), result.registry_available ? __("Installed") : __("Missing")],
		[__("Task contract"), result.task_contract_available ? __("Installed") : __("Missing")],
		[__("Quantity contract"), result.quantity_contract_available ? __("Installed") : __("Missing")],
		[__("State-action flag"), result.state_actions_enabled ? __("Enabled") : __("Disabled")],
		[__("Scanner-action flag"), result.scanner_actions_enabled ? __("Enabled") : __("Disabled")],
	].forEach(([label, value]) => {
		const row = $("<tr></tr>").appendTo(table);
		$("<th></th>").text(label).appendTo(row);
		$("<td></td>").text(value).appendTo(row);
	});
}

function add_actions_table(parent, actions) {
	$("<h4></h4>").text(__("Inventoried actions")).appendTo(parent);
	if (!actions.length) {
		$("<p class='text-muted'></p>").text(__("No server action registry is installed on this site.")).appendTo(parent);
		return;
	}
	const table = $("<table class='table table-bordered table-hover'></table>").appendTo(parent);
	const header = $("<tr></tr>").appendTo($("<thead></thead>").appendTo(table));
	[__("Action"), __("Stage"), __("Source"), __("Confirmation"), __("Easy-use approval"), __("Reversal")].forEach((label) => $("<th></th>").text(label).appendTo(header));
	const body = $("<tbody></tbody>").appendTo(table);
	actions.forEach((action) => {
		const row = $("<tr></tr>").appendTo(body);
		[
			action.label || action.action_id,
			action.stage,
			action.source_doctype || "—",
			action.confirmation_level,
			action.approved_for_easy_ui ? __("Approved") : __("Not approved"),
			action.reversal_route,
		].forEach((value) => $("<td></td>").text(value || "—").appendTo(row));
	});
}

frappe.pages["lumirise-action-readiness"].on_page_show = function (wrapper) {
	const body = wrapper.lumirise_page.body.empty();
	body.text(__("Loading action readiness…"));
	frappe.call({ method: "lumirise_ui.action_readiness_api.get_action_readiness" })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only || result.ready_for_mutation) {
				body.text(__("The action readiness report is unavailable."));
				return;
			}
			$(`<div class="alert alert-warning"><strong>${__("Blocked by safety gates")}</strong><br></div>`)
				.appendTo(body)
				.append(result.blocked_reasons.map((reason) => $("<div></div>").text(reason)));
			add_status_table(body, result);
			$(`<p class="text-muted">${__("Updated {0} · {1} inventoried actions", [result.generated_at, result.actions.length])}</p>`).appendTo(body);
			add_actions_table(body, result.actions);
		})
		.catch(() => body.text(__("The action readiness page is unavailable for your role.")));
};
