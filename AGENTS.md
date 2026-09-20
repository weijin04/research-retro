# Research Retro / historical Research Harness

This repository owns the standalone retrospective unit. Historical implementation plans remain at the root; the shipped engine is `src/research_harness/`.

- Keep scientific source projects read-only. Development receipts belong under `var/`; regressions under `research_cases/`. Installed product state and outputs belong in the target project's `.retro/` or an explicitly selected external workspace, never in the engine repository.
- R2 reconstruction precedes F1 runtime, then E1 evaluation. Never relabel a slice, mock, or inherited judgment as a complete scientific reconstruction.
- Use `rtk proxy uv run retro ...` and `rtk proxy uv run python -m unittest discover -s tests -v`. `rh` is an alias of the standalone CLI. Product installation/Agent docs intentionally use ordinary commands without a personal wrapper.
- `backlog.json` is the editable task registry; regenerate `06_EXECUTION_CHECKLIST.md` after updates.
- Current state and receipts: `CURRENT_STATE.md`. Rerun receipts are under ignored `var/`; reproducible code, cases and manifests are versioned.
- Runtime workers cannot modify the authoritative store or control plane. Builder permissions do not describe runtime isolation.
- The standalone distribution makes no model calls. Historical Jev adapters are development regressions in `research_cases/legacy/` and are excluded from the release; real scientific egress still requires explicit authorization. Never print credentials.
- Runtime exchange contracts and Agent docs are packaged in `src/research_harness/resources/`; root `AGENT.md`, `tools.json` and `contracts/contract.schema.json` link to these authoritative assets. Regenerate tool definitions with `checks/render_tools.py` after editing the public contract.
- Release acceptance: `checks/standalone_acceptance.py` installs offline in a namespace without developer home/source checkout, then exercises the public lifecycle. The unit itself does not require its development isolation tools.
