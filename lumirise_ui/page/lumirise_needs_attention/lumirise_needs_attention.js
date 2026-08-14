frappe.pages["lumirise-needs-attention"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Needs Attention"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$("<div class='lumirise-queue-help text-muted'></div>")
		.text(__("Read-only shadow view. It aggregates permission-visible task and health facts."))
		.appendTo(page.main);
	$("<div class='lumirise-queue-body'></div>").appendTo(page.main);
	wrapper.lumirise_page = page;
};

frappe.pages["lumirise-needs-attention"].on_page_show = function (wrapper) {
	const page = wrapper.lumirise_page;
	const route_options = frappe.route_options || {};
	frappe.route_options = null;
	frappe.call({
		method: "lumirise_ui.ui_api.get_needs_attention",
		args: route_options,
	}).then((response) => {
		const result = response.message;
		const body = $(page.main).find(".lumirise-queue-body").empty();
		if (!result || result.actions_enabled) {
			body.text(__("This read-only queue is unavailable."));
			return;
		}
		$(`<p class="text-muted">${__("{0} records", [result.count])} · ${__("Updated {0}", [result.generated_at])}</p>`).appendTo(body);
		if (!result.rows.length) {
			$(`<div class="empty-state text-muted">${__("Nothing needs attention in this scope.")}</div>`).appendTo(body);
			return;
		}
		const table = $("<table class='table table-bordered table-hover'></table>").appendTo(body);
		$("<thead><tr><th>Severity</th><th>Problem</th><th>Impact</th><th>Source</th><th>Owner</th><th>Age</th><th>Next action</th></tr></thead>").appendTo(table);
		const tbody = $("<tbody></tbody>").appendTo(table);
		result.rows.forEach((row) => {
			const tr = $("<tr></tr>").appendTo(tbody);
			[ row.severity || "", row.title || row.problem || "", row.business_impact || "", row.source_label || "", row.owner_user || "", `${row.age_days || 0}d`, row.next_action || "Open Source" ].forEach((value) => $("<td></td>").text(value).appendTo(tr));
			tr.on("click", () => {
				if (row.reference_doctype && row.reference_name) {
					frappe.set_route("Form", row.reference_doctype, row.reference_name);
				} else if (row.name) {
					frappe.set_route("Form", "Health Check Run", row.name);
				}
			});
		});
	});
};
