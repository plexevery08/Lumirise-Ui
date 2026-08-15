frappe.pages["lumirise-inbound-quality"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Inbound & Quality"),
		single_column: true,
	});
	page.main.addClass("lumirise-readonly-queue");
	$(`<p class="text-muted">${__("Permission-filtered inbound, package, Vendor PDI and IQC exceptions. This board is read-only.")}</p>`).appendTo(page.main);
	wrapper.lumirise_page = { page, body: $("<div></div>").appendTo(page.main) };
};

function render_section(parent, section) {
	$(`<h4>${__(section.title)} <span class="text-muted small">(${section.count})</span></h4>`).appendTo(parent);
	if (!section.rows.length) {
		$("<p class='text-muted'></p>").text(__("No readable exceptions.")).appendTo(parent);
		return;
	}
	const columns = Object.keys(section.rows[0]).filter((field) => !["doctype", "name"].includes(field));
	const table = $("<table class='table table-bordered table-hover'></table>").appendTo(parent);
	const header = $("<tr></tr>").appendTo($("<thead></thead>").appendTo(table));
	[__("Open"), ...columns.map((field) => __(field.replaceAll("_", " ")))].forEach((label) => $("<th></th>").text(label).appendTo(header));
	const body = $("<tbody></tbody>").appendTo(table);
	section.rows.forEach((row) => {
		const tr = $("<tr></tr>").appendTo(body);
		const link = $("<a></a>").text(row.name).on("click", () => frappe.set_route("Form", row.doctype, row.name));
		$("<td></td>").append(link).appendTo(tr);
		columns.forEach((field) => $("<td></td>").text(row[field] ?? "").appendTo(tr));
	});
}

frappe.pages["lumirise-inbound-quality"].on_page_show = function (wrapper) {
	const body = wrapper.lumirise_page.body.empty();
	body.text(__("Loading inbound and quality board…"));
	frappe.call({ method: "lumirise_ui.inbound_quality_api.get_inbound_quality_board" })
		.then((response) => {
			const result = response.message;
			body.empty();
			if (!result || result.actions_enabled || !result.read_only) {
				body.text(__("The inbound and quality board is unavailable."));
				return;
			}
			$(`<p class="text-muted">${__("Updated {0} · {1} readable exceptions", [result.generated_at, result.total_rows])}</p>`).appendTo(body);
			result.sections.forEach((section) => render_section(body, section));
		})
		.catch(() => body.text(__("This board is disabled or unavailable for your role.")));
};
