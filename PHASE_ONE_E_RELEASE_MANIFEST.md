# Phase 1E release manifest: rollout control center

Phase 1E adds a read-only administrator page at
`/app/lumirise-ui-control-center`. It reports the installed UI version,
feature-flag state, available UI routes and the Phase 0 task-contract gate.

The page does not read operational queues and cannot change settings,
documents, assignments, stock, quality records or workflow state. It is
available only to `System Manager` and `Lumirise Operations`.

## Safety contract

- `read_only` is always `true`.
- `actions_enabled` is always `false`.
- All mutation flags remain disabled by default.
- Missing `lumirise_custom.task_contracts` is reported as a blocked gate;
  the page does not guess a fallback contract.

## Verification

Run from the bench root:

```bash
bench --site site.com migrate --skip-search-index
bench --site site.com run-tests --app lumirise_ui --module lumirise_ui.lumirise_ui.tests.test_rollout_status
```

Open `/app/lumirise-ui-control-center` as an authorized administrator after
the migration. The existing operational pages remain gated until their
individual flags and Phase 0 prerequisites pass.
