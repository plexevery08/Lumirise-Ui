frappe.pages["lumirise-order-360"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Order 360"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-trace");
	const help = $("<div class='lumirise-trace-help text-muted'></div>")
		.text(__("Read-only trace view. Opening a source document is the only navigation action."))
		.appendTo(page.main);
	const form = $("<div class='form-group row'></div>").appendTo(page.main);
	const input = $("<input class='form-control col-sm-8' type='text'>")
		.attr("placeholder", __("Sales Order name"))
		.appendTo(form);
	const button = $("<button class='btn btn-primary ml-2'></button>")
		.text(__("Load trace"))
		.appendTo(form);
	const body = $("<div class='lumirise-trace-body'></div>").appendTo(page.main);
	wrapper.lumirise_page = { page, input, button, body };

	button.on("click", () => load_order_trace(wrapper));
	input.on("keypress", (event) => {
		if (event.which === 13) load_order_trace(wrapper);
	});
};

function add_table(parent, title, rows, columns) {
	$(`<h4>${__(title)}</h4>`).appendTo(parent);
	if (!rows || !rows.length) {
		$("<p class='text-muted'></p>").text(__("No readable records.")).appendTo(parent);
		return;
	}
	const table = $("<table class='table table-bordered table-hover'></table>").appendTo(parent);
	const header = $("<tr></tr>").appendTo($("<thead></thead>").appendTo(table));
	columns.forEach((column) => $("<th></th>").text(__(column.label)).appendTo(header));
	const body = $("<tbody></tbody>").appendTo(table);
	rows.forEach((row) => {
		const tr = $("<tr></tr>").appendTo(body);
		columns.forEach((column) => $("<td></td>").text(row[column.field] || "").appendTo(tr));
		if (row.doctype && row.name) {
			tr.css("cursor", "pointer").on("click", () => frappe.set_route("Form", row.doctype, row.name));
		}
	});
}

function load_order_trace(wrapper) {
	const state = wrapper.lumirise_page;
	const name = state.input.val().trim();
	const body = state.body.empty();
	if (!name) {
		body.text(__("Enter a Sales Order name."));
		return;
	}
	state.button.prop("disabled", true);
	body.text(__("Loading read-only trace…"));
	frappe.call({ method: "lumirise_ui.trace_api.get_order_360", args: { sales_order: name } })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("This trace view is unavailable."));
				return;
			}
			$("<p class='text-muted'></p>")
				.text(__("Updated {0} · {1} linked records", [result.generated_at, Object.values(result.counts).reduce((a, b) => a + b, 0)]))
				.appendTo(body);
			add_table(body, "Sales Order", [result.sales_order], [
				{ field: "name", label: "Name" },
				{ field: "customer", label: "Customer" },
				{ field: "status", label: "Status" },
				{ field: "transaction_date", label: "Transaction date" },
				{ field: "delivery_date", label: "Delivery date" },
				{ field: "grand_total", label: "Grand total" },
			]);
			add_table(body, "Items", result.items, [
				{ field: "item_code", label: "Item" },
				{ field: "item_name", label: "Description" },
				{ field: "qty", label: "Qty" },
				{ field: "delivery_date", label: "Delivery date" },
			]);
			const labels = {
				indents: "Indents",
				work_orders: "Work Orders",
				purchase_orders: "Purchase Orders",
				purchase_receipts: "Purchase Receipts",
				delivery_notes: "Delivery Notes",
				sales_invoices: "Sales Invoices",
			};
			Object.entries(labels).forEach(([key, label]) => add_table(body, label, result.linked[key], [
				{ field: "name", label: "Name" },
				{ field: "status", label: "Status" },
				{ field: "supplier", label: "Supplier" },
				{ field: "customer", label: "Customer" },
				{ field: "posting_date", label: "Posting date" },
				{ field: "grand_total", label: "Grand total" },
			]));
		})
		.catch(() => body.text(__("This trace view is disabled or unavailable for your role.")))
		.finally(() => state.button.prop("disabled", false));
}

frappe.pages["lumirise-order-360"].on_page_show = function (wrapper) {
	const state = wrapper.lumirise_page;
	const route_options = frappe.route_options || {};
	frappe.route_options = null;
	if (route_options.sales_order || route_options.name) {
		state.input.val(route_options.sales_order || route_options.name);
		load_order_trace(wrapper);
	}
};
