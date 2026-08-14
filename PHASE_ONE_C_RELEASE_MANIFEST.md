# Phase 1C release manifest: read-only trace views

Destination app branch: `main`

Phase 1C adds two feature-gated, read-only trace surfaces:

- **Order 360** — a permission-filtered Sales Order journey with items and
  readable Indent, Work Order, Purchase, Receipt, Delivery, and Invoice links.
- **Material 360** — a permission-filtered Item view with warehouse balances,
  recent Stock Ledger movements, and readable linked Lumirise Tasks.

Both endpoints return `read_only=true` and `actions_enabled=false`. They use
`frappe.get_list` rather than the business app's `get_all`-based stamping
resolver, so the UI does not widen a user's document visibility. No endpoint
creates, updates, submits, cancels, assigns, or posts any document.

## Rollout gates

Keep `easy_ui_order_360` and `easy_ui_material_360` at `0` during migration.
Before enabling either flag, verify:

1. The Phase 0 `lumirise_custom` task/trace contracts are installed.
2. The Phase 1C integration suite and the existing Phase 0–1B suites pass.
3. A user without read permission cannot see an Order or Material trace.
4. The API responses contain `read_only=true`, `actions_enabled=false`, and no
   mutation method is reachable from the page.
5. A second migration is idempotent and does not duplicate role-workspace
   shortcuts.

The trace shortcuts are reconciled only when their individual flags are on;
turning a flag off removes only the app-owned shortcut and leaves native
ERPNext navigation untouched.
