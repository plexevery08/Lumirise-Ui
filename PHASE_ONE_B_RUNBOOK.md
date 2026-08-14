# Phase 1B runbook: reversible daily read-only UI

Run commands from the bench `sites` directory with the Phase 1B app on the
Python path. Keep a database backup before migration.

```bash
export BENCH=/path/to/bench
export PYTHONPATH=/path/to/phase1b/apps
cd "$BENCH/sites"
python -m frappe.utils.bench_helper frappe --site site.com backup --with-files
python -m frappe.utils.bench_helper frappe --site site.com migrate --skip-search-index
python -m frappe.utils.bench_helper frappe --site site.com run-tests \
  --app lumirise_custom --test-category integration --failfast
python -m frappe.utils.bench_helper frappe --site site.com run-tests \
  --app lumirise_ui --test-category integration --failfast
```

## Safe rollout

Keep all three role/read flags off during migration. After the integration
gates pass, enable only the desired read surface in **Lumirise Operations
Settings**:

- `easy_ui_my_work=1` exposes My Work's API/page to authorized users.
- `easy_ui_needs_attention=1` exposes Needs Attention's API/page to authorized
  users.
- `easy_ui_state_actions` and `easy_ui_scanner_actions` stay `0`.

The pages remain read-only even when their individual flags are enabled.

## Rollback levels

1. **Immediate surface rollback:** set both read flags to `0` and clear Desk
   cache. Each API rejects the request with `PermissionError` before querying
   Lumirise Task.
2. **Role-shell rollback:** set `easy_ui_role_workspaces=0` and run
   `frappe --site site.com execute lumirise_ui.workspace_routing.prepare_role_workspace_rollback`.
   This disables active pilots, restores captured default workspaces, removes
   only roles granted by the pilot record, and hides the four role workspaces.
3. **Code rollback:** revert the Phase 1B commit and migrate. The phase adds
   no business transactions or irreversible data migration; the pre-migration
   backup can restore the site if a schema rollback is required.

After rollback, verify that both Page routes either no longer exist (code
rollback) or return the disabled read-only message, all three UI flags are `0`,
and the native ERPNext forms still load.
