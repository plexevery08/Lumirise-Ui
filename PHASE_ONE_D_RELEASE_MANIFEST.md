# Phase 1D release manifest: operational read-only queues

Phase 1D adds two guarded, read-only operational queues:

- **Stock Control** — open stock mismatch/store exception tasks plus
  permission-visible negative warehouse balances.
- **Quality Queue** — open quality/rejection/approval tasks plus pending or
  failed Quality Inspection, IQC, Vendor PDI, and Customer PDI records.

The queues use existing ERPNext and Lumirise records through `frappe.get_list`.
They do not create a shadow status store, mutate stock, acknowledge a task,
assign a user, approve a quality record, or launch a scanner action.

## Rollout gates

Keep `easy_ui_stock_control` and `easy_ui_quality_queue` at `0` until:

1. The Phase 0 custom task contract is installed and the Phase 0–1C suites pass.
2. The queue tests prove both flags reject requests before any database list
   query.
3. Users only see records permitted by the native ERPNext/Lumirise permissions.
4. A second migration is idempotent and does not duplicate queue shortcuts.
5. Turning either flag off removes only its app-owned shortcut and leaves native
   navigation and business records unchanged.

The state-action and scanner flags remain `0`; those capabilities are a later,
separately reviewed phase.
