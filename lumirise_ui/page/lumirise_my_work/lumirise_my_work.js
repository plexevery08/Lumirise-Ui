frappe.pages["lumirise-my-work"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("My Work"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$("<div class='lumirise-queue-help text-muted'></div>")
		.text(__("Read-only shadow view. Open the source document to take any action."))
		.appendTo(page.main);
	$("<div class='lumirise-queue-body'></div>").appendTo(page.main);
	wrapper.lumirise_page = page;
};

frappe.pages["lumirise-my-work"].on_page_show = function (wrapper) {
	const page = wrapper.lumirise_page;
	const route_options = frappe.route_options || {};
	frappe.route_options = null;
	frappe.call({
		method: "lumirise_ui.ui_api.get_my_work",
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
			$(`<div class="empty-state text-muted">${__("No work matches this view.")}</div>`).appendTo(body);
			return;
		}
		const table = $("<table class='table table-bordered table-hover'></table>").appendTo(body);
		$("<thead><tr><th>Severity</th><th>Due</th><th>Title</th><th>Source</th><th>Business Impact</th><th>Blocker</th><th>Age</th></tr></thead>").appendTo(table);
		const tbody = $("<tbody></tbody>").appendTo(table);
		result.rows.forEach((row) => {
			const tr = $("<tr></tr>").appendTo(tbody);
			[ row.severity || "", row.due_on || "", row.title || "", row.source_label || "", row.business_impact || "", row.blocker_reason || "", `${row.age_days || 0}d` ].forEach((value) => $("<td></td>").text(value).appendTo(tr));
			tr.on("click", () => {
				if (row.reference_doctype && row.reference_name) {
					frappe.set_route("Form", row.reference_doctype, row.reference_name);
				} else {
					frappe.set_route("Form", "Lumirise Task", row.name);
				}
			});
		});
	});
};
