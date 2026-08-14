# Phase 1B release manifest: daily read-only UI

Destination app branch: `main`

Source implementation branch: `agent/easy-ui-phase1b-daily-work` (kept as a
rollback/reference branch in the isolated worktree)

Phase 1B adds the first operational UI surfaces after the Phase 0 safety
foundations and Phase 1A role shell. It is a shadow/read-only release. No
button in this phase assigns, escalates, acknowledges, completes, blocks,
posts stock, or changes accounting state.

## Delivered

- `lumirise-my-work` Page: owner-scoped, permission-filtered Lumirise Task
  queue with Mine, Due Today, Overdue, Blocked, Waiting, and Completed views.
- `lumirise-needs-attention` Page: permission-aware aggregate of high-impact
  Lumirise Tasks and the latest Amber/Red Health Check Run.
- Both pages use read-only whitelisted APIs and return an explicit
  `read_only=true`, `actions_enabled=false` contract.
- Task query conditions and record permissions expose only tasks owned by,
  supervised by, or overseen by the current user (with control-role access
  retained for System Manager and Lumirise Operations).
- Both pages are role-restricted to the four Phase 1A workspace access roles
  plus the two control roles.
- The pages are added as Page shortcuts to every role workspace after standard
  Workspace JSON synchronization.
- The endpoint inventory includes both new whitelisted methods and records
  their independent rollout flags.

## Rollout gates

All of the following must pass before enabling a flag:

1. `easy_ui_role_workspaces`, `easy_ui_my_work`, and
   `easy_ui_needs_attention` remain `0` on the target site.
2. The Phase 0, Phase 1A, and Phase 1B integration suites pass.
3. A non-owner cannot see another user's task through either queue API.
4. The queue APIs make no writes and expose no action capability.
5. A migration followed by a second migration is successful and leaves the
   page/workspace links idempotent.
6. The rollback procedure below hides the role shell and makes both APIs fail
   closed before any task query.

Phase 1C trace views and all state-changing actions remain out of scope until
this shadow release has been observed and separately approved.
