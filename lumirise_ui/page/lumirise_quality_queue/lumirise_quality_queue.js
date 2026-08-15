frappe.pages["lumirise-quality-queue"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Quality Queue"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$("<div class='lumirise-queue-help text-muted'></div>")
		.text(__("Read-only quality queue. It aggregates pending/failed quality records and permission-visible quality tasks."))
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

frappe.pages["lumirise-quality-queue"].on_page_show = function (wrapper) {
	const body = wrapper.lumirise_page.body.empty();
	body.text(__("Loading read-only quality queue…"));
	frappe.call({ method: "lumirise_ui.operational_api.get_quality_queue" })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("This quality queue is unavailable."));
				return;
			}
			$("<p class='text-muted'></p>")
				.text(__("Updated {0} · {1} tasks · {2} quality records", [
					result.generated_at,
					result.counts.quality_tasks,
					result.counts.quality_records,
				]))
				.appendTo(body);
			render_table(body, "Open quality tasks", result.quality_tasks, [
				{ field: "severity", label: "Severity" },
				{ field: "priority", label: "Priority" },
				{ field: "title", label: "Task" },
				{ field: "department", label: "Department" },
				{ field: "status", label: "Status" },
				{ field: "reference_name", label: "Source" },
			]);
			render_table(body, "Pending or failed quality records", result.quality_records, [
				{ field: "queue_kind", label: "Source type" },
				{ field: "name", label: "Record" },
				{ field: "status", label: "Status" },
				{ field: "item_code", label: "Item" },
				{ field: "supplier", label: "Supplier" },
				{ field: "customer", label: "Customer" },
				{ field: "purchase_order", label: "Purchase Order" },
				{ field: "sales_order", label: "Sales Order" },
			]);
		})
		.catch(() => body.text(__("This quality queue is disabled or unavailable for your role.")));
};
