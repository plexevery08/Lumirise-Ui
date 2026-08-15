frappe.pages["lumirise-ui-control-center"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Lumirise UI Control Center"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$(`<p class="text-muted">${__("Read-only release status. No business transaction or operational action is available here.")}</p>`).appendTo(page.main);
	wrapper.lumirise_page = { page, body: $("<div></div>").appendTo(page.main) };
};

function render_card(parent, label, value, detail, indicator = "blue") {
	const card = $(`<div class="col-sm-4"><div class="card mb-3"><div class="card-body"><div class="text-muted small"></div><div class="h3 mb-1"></div><div class="small text-muted"></div></div></div></div>`);
	card.find(".text-muted.small").first().text(__(label));
	card.find(".h3").text(value).addClass(`text-${indicator}`);
	card.find(".small.text-muted").last().text(__(detail));
	card.appendTo(parent);
}

function render_flags(parent, flags) {
	$(`<h4>${__("Feature flags")}</h4>`).appendTo(parent);
	const table = $("<table class='table table-bordered table-hover'></table>").appendTo(parent);
	const header = $("<tr></tr>").appendTo($("<thead></thead>").appendTo(table));
	["Flag", "Type", "State"].forEach((label) => $("<th></th>").text(__(label)).appendTo(header));
	const body = $("<tbody></tbody>").appendTo(table);
	flags.forEach((flag) => {
		const row = $("<tr></tr>").appendTo(body);
		$("<td></td>").text(flag.name).appendTo(row);
		$("<td></td>").text(flag.kind === "action" ? __("Action") : __("Read-only")).appendTo(row);
		$("<td></td>").text(flag.enabled ? __("Enabled") : __("Disabled")).appendTo(row);
	});
}

function render_pages(parent, pages) {
	$(`<h4>${__("Installed UI pages")}</h4>`).appendTo(parent);
	const table = $("<table class='table table-bordered table-hover'></table>").appendTo(parent);
	const header = $("<tr></tr>").appendTo($("<thead></thead>").appendTo(table));
	["Page", "Route", "Gate", "State"].forEach((label) => $("<th></th>").text(__(label)).appendTo(header));
	const body = $("<tbody></tbody>").appendTo(table);
	pages.forEach((page) => {
		const row = $("<tr></tr>").appendTo(body);
		$("<td></td>").text(page.title).appendTo(row);
		const link = $("<a></a>").attr("href", page.route).text(page.route);
		$("<td></td>").append(link).appendTo(row);
		$("<td></td>").text(page.flag || __("Always available to this role")).appendTo(row);
		$("<td></td>").text(page.enabled ? __("Available") : __("Gated")).appendTo(row);
	});
}

frappe.pages["lumirise-ui-control-center"].on_page_show = function (wrapper) {
	const body = wrapper.lumirise_page.body.empty();
	body.text(__("Loading rollout status…"));
	frappe.call({ method: "lumirise_ui.rollout_status_api.get_rollout_status" })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("The rollout status is unavailable."));
				return;
			}
			const cards = $("<div class='row'></div>").appendTo(body);
			const enabled = result.flags.filter((flag) => flag.enabled).length;
			render_card(cards, "App version", result.app_version, `Updated ${result.generated_at}`);
			render_card(cards, "Read-only flags", `${enabled}/${result.flags.length}`, "Enabled surfaces", enabled ? "green" : "blue");
			render_card(cards, "Task contract", result.gates.task_contract_available ? __("Installed") : __("Missing"), "Phase 0 dependency", result.gates.task_contract_available ? "green" : "orange");
		$(`<p class="alert alert-warning">${__("This page is intentionally read-only. Keep action flags disabled until Phase 0 permission, task-contract, workflow, and rollback gates pass.")}</p>`).appendTo(body);
		render_flags(body, result.flags);
		render_pages(body, result.pages);
		})
		.catch(() => body.text(__("The rollout status page is unavailable for your role.")));
};
