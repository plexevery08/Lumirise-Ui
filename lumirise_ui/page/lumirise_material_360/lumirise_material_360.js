frappe.pages["lumirise-material-360"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Material 360"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-trace");
	$("<div class='lumirise-trace-help text-muted'></div>")
		.text(__("Read-only stock and movement view. No stock, accounting, or task action is available here."))
		.appendTo(page.main);
	const form = $("<div class='form-group row'></div>").appendTo(page.main);
	const input = $("<input class='form-control col-sm-8' type='text'>")
		.attr("placeholder", __("Item code"))
		.appendTo(form);
	const button = $("<button class='btn btn-primary ml-2'></button>")
		.text(__("Load material"))
		.appendTo(form);
	const body = $("<div class='lumirise-trace-body'></div>").appendTo(page.main);
	wrapper.lumirise_page = { page, input, button, body };
	button.on("click", () => load_material_trace(wrapper));
	input.on("keypress", (event) => {
		if (event.which === 13) load_material_trace(wrapper);
	});
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
	const body = $("<tbody></tbody>").appendTo(table);
	rows.forEach((row) => {
		const tr = $("<tr></tr>").appendTo(body);
		columns.forEach((column) => $("<td></td>").text(row[column.field] || "").appendTo(tr));
		if (row.doctype && row.name) {
			tr.css("cursor", "pointer").on("click", () => frappe.set_route("Form", row.doctype, row.name));
		}
	});
}

function load_material_trace(wrapper) {
	const state = wrapper.lumirise_page;
	const code = state.input.val().trim();
	const body = state.body.empty();
	if (!code) {
		body.text(__("Enter an Item code."));
		return;
	}
	state.button.prop("disabled", true);
	body.text(__("Loading read-only material view…"));
	frappe.call({ method: "lumirise_ui.trace_api.get_material_360", args: { item_code: code } })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("This material view is unavailable."));
				return;
			}
			$("<p class='text-muted'></p>")
				.text(__("Updated {0} · Actual {1} · Reserved {2} · Projected {3}", [
					result.generated_at,
					result.stock.total_actual_qty,
					result.stock.total_reserved_qty,
					result.stock.total_projected_qty,
				]))
				.appendTo(body);
			render_table(body, "Item", [result.item], [
				{ field: "name", label: "Item code" },
				{ field: "item_name", label: "Description" },
				{ field: "stock_uom", label: "Stock UOM" },
				{ field: "has_batch_no", label: "Batch tracked" },
			]);
			render_table(body, "Warehouse balances", result.stock.bins, [
				{ field: "warehouse", label: "Warehouse" },
				{ field: "actual_qty", label: "Actual" },
				{ field: "reserved_qty", label: "Reserved" },
				{ field: "projected_qty", label: "Projected" },
			]);
			render_table(body, "Recent movements", result.recent_movements, [
				{ field: "posting_date", label: "Date" },
				{ field: "actual_qty", label: "Qty" },
				{ field: "warehouse", label: "Warehouse" },
				{ field: "voucher_type", label: "Voucher type" },
				{ field: "voucher_no", label: "Voucher" },
			]);
			render_table(body, "Linked tasks", result.tasks, [
				{ field: "name", label: "Task" },
				{ field: "title", label: "Title" },
				{ field: "status", label: "Status" },
				{ field: "severity", label: "Severity" },
				{ field: "owner_user", label: "Owner" },
			]);
		})
		.catch(() => body.text(__("This material view is disabled or unavailable for your role.")))
		.finally(() => state.button.prop("disabled", false));
}

frappe.pages["lumirise-material-360"].on_page_show = function (wrapper) {
	const state = wrapper.lumirise_page;
	const route_options = frappe.route_options || {};
	frappe.route_options = null;
	if (route_options.item_code || route_options.name) {
		state.input.val(route_options.item_code || route_options.name);
		load_material_trace(wrapper);
	}
};
