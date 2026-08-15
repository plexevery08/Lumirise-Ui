# Phase 2 read-only manifest: Inbound & Quality board

The `lumirise-inbound-quality` Page reconciles permission-visible records
from existing ERPNext/Lumirise DocTypes:

- Inbound Logistics stages
- RM Packages pending IQC, quarantined or rejected
- Vendor PDI exceptions
- IQC exceptions

The endpoint is feature-gated by `easy_ui_inbound_quality`, defaults to off,
uses `frappe.get_list`, and returns `read_only: true` and
`actions_enabled: false`. It does not create packages, issue samples, put
away stock, submit inspections, or call any mutation method.

The Phase 0 task contract and action registry remain prerequisites for any
future scanner or state-changing action on top of this board.
