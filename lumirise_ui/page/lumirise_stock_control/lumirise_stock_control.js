frappe.pages["lumirise-stock-control"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Stock Control"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$("<div class='lumirise-queue-help text-muted'></div>")
		.text(__("Read-only stock exceptions. Open the source document in ERPNext to investigate; no stock action is available here."))
		.appendTo(page.main);
	const body = $("<div class='lumirise-queue-body'></div>").appendTo(page.main);
	wrapper.lumirise_page = { page, body };
};

function render_table(parent, title, rows, columns) {
	$(`<h4>${__(title)}</h4>`).appendTo(parent);
	if (!rows || !rows.length) {
		$("<p class='text-muted'></p>").text(__("No readable records.")).appendTo(parent);
		return;
	}
	const table = $("<table class='table table-bordered table-hover'></table>").appendTo(parent);
	const header = $("<tr></tr>").appendTo($("<thead></thead>").appendTo(table));
	columns.forEach((column) => $("<th></th>").text(__(column.label)).appendTo(header));
	const tbody = $("<tbody></tbody>").appendTo(table);
	rows.forEach((row) => {
		const tr = $("<tr></tr>").appendTo(tbody);
		columns.forEach((column) => $("<td></td>").text(row[column.field] || "").appendTo(tr));
		if (row.doctype && row.name) {
			tr.css("cursor", "pointer").on("click", () => frappe.set_route("Form", row.doctype, row.name));
		}
	});
}

frappe.pages["lumirise-stock-control"].on_page_show = function (wrapper) {
	const body = wrapper.lumirise_page.body.empty();
	body.text(__("Loading read-only stock control…"));
	frappe.call({ method: "lumirise_ui.operational_api.get_stock_control" })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("This stock control view is unavailable."));
				return;
			}
			$("<p class='text-muted'></p>")
				.text(__("Updated {0} · {1} tasks · {2} negative bins", [
					result.generated_at,
					result.counts.stock_tasks,
					result.counts.negative_bins,
				]))
				.appendTo(body);
			render_table(body, "Open stock tasks", result.stock_tasks, [
				{ field: "severity", label: "Severity" },
				{ field: "priority", label: "Priority" },
				{ field: "title", label: "Task" },
				{ field: "department", label: "Department" },
				{ field: "status", label: "Status" },
				{ field: "reference_name", label: "Source" },
			]);
			render_table(body, "Negative warehouse balances", result.negative_bins, [
				{ field: "item_code", label: "Item" },
				{ field: "warehouse", label: "Warehouse" },
				{ field: "actual_qty", label: "Actual quantity" },
				{ field: "reserved_qty", label: "Reserved quantity" },
				{ field: "company", label: "Company" },
			]);
		})
		.catch(() => body.text(__("This stock control view is disabled or unavailable for your role.")));
};
