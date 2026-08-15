### Lumirise UI

Standalone Lumirise easy-use UI surfaces

This app is the dedicated home for Lumirise UI work and keeps Desk pages,
workspaces, and UI-only endpoints separate from the `lumirise_custom` business
app. It depends on ERPNext and `lumirise_custom` for the authoritative
DocTypes, task fields, traceability fields, and safety contracts. UI code should
be moved here before this app is installed on a site.

The app owns the rollout flags as additive Custom Fields when an older
`lumirise_custom` branch does not yet carry the Phase 0 fields. It does not own
the `Lumirise Task` business lifecycle or create state-changing actions. Keep
all UI flags off until the Phase 0 custom-app gates and the UI integration suite
pass on a disposable site. Phase 1C adds the read-only Order 360 and Material
360 views; their flags are independent and remain off by default.
Phase 1D adds guarded read-only Stock Control and Quality Queue views; these
also remain off by default.
The Inbound & Quality board and Action Readiness report are also read-only. The
Action Readiness report can be opened at `/app/lumirise-action-readiness` to
inspect the optional custom-app action registry; it never dispatches an action.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench install-app lumirise_ui
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/lumirise_ui
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
