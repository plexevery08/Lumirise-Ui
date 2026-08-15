frappe.pages["lumirise-scanner-readiness"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Scanner Readiness"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$(`<p class="text-muted">${__("Safe scanner shell only. No barcode is accepted and no stock or quality document can be changed from this page.")}</p>`).appendTo(page.main);
	wrapper.lumirise_page = { page, body: $("<div></div>").appendTo(page.main) };
};

function render_gate(body, result) {
	const status = result.ready_for_mutation ? __("Ready") : __("Blocked");
	$(`<div class="alert alert-warning"><strong></strong><br><span></span></div>`)
		.find("strong").text(status).end()
		.find("span").text(result.blocked_reasons.join(" · ")).end()
		.appendTo(body);

	const table = $("<table class='table table-bordered'></table>").appendTo(body);
	const rows = [
		[__("Scanner flag"), result.scanner_enabled ? __("Enabled") : __("Disabled")],
		[__("State-action flag"), result.state_actions_enabled ? __("Enabled") : __("Disabled")],
		[__("Task contract"), result.task_contract_available ? __("Installed") : __("Missing")],
		[__("Mutation contract"), __("Not available")],
	];
	rows.forEach(([label, value]) => {
		const row = $("<tr></tr>").appendTo(table);
		$("<th></th>").text(label).appendTo(row);
		$("<td></td>").text(value).appendTo(row);
	});

	$(`<h4>${__("Preview only")}</h4>`).appendTo(body);
	const input = $("<input class='form-control mb-2' type='text' disabled>")
		.attr("placeholder", __("Barcode input is disabled until the action gate passes"))
		.appendTo(body);
	$("<button class='btn btn-secondary' disabled></button>")
		.text(__("Scan barcode"))
		.appendTo(body);
}

frappe.pages["lumirise-scanner-readiness"].on_page_show = function (wrapper) {
	const body = wrapper.lumirise_page.body.empty();
	body.text(__("Loading scanner gate…"));
	frappe.call({ method: "lumirise_ui.scanner_api.get_scanner_gate" })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("The scanner readiness gate is unavailable."));
				return;
			}
			render_gate(body, result);
		})
		.catch(() => body.text(__("The scanner readiness page is unavailable for your role.")));
};
