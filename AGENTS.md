# Research Retro / historical Research Harness

This repository owns the standalone Research Retro reconstruction product. Historical implementation plans remain at the root; the shipped engine is `src/research_harness/`.

- Keep scientific source projects read-only. Development receipts belong under `var/`; regressions under `research_cases/`. All new product state and outputs belong in a separate external workspace (default sibling `PROJECT_NAME.retro`), never inside the source project or engine repository. Existing legacy workspaces remain readable.
- R2 reconstruction precedes F1 runtime, then E1 evaluation. Never relabel a slice, mock, or inherited judgment as a complete scientific reconstruction.
- Use `rtk proxy uv run retro ...` and `rtk proxy uv run python -m unittest discover -s tests -v`. `rh` is an alias of the standalone CLI. Product installation/Agent docs intentionally use ordinary commands without a personal wrapper.
- `backlog.json` is the editable task registry; regenerate `06_EXECUTION_CHECKLIST.md` after updates.
- Current state and receipts: `CURRENT_STATE.md`. Rerun receipts are under ignored `var/`; reproducible code, cases and manifests are versioned.
- Runtime workers cannot modify the authoritative store or control plane. Builder permissions do not describe runtime isolation.
- Projection and legacy tools remain offline. Jev is an explicit advisory local judgment service (`triage judge/impact`, custom `judge`, optional `semantic-review`) after per-workspace authorization. Never call it automatically on record/refresh/publish or let a probability threshold revoke scientific support. Historical field-only permissions stay narrow. Historical adapters remain excluded from the release. Never print credentials.
- Runtime exchange contracts and Agent docs are packaged in `src/research_harness/resources/`; root `AGENT.md`, `tools.json` and `contracts/contract.schema.json` link to these authoritative assets. Regenerate tool definitions with `checks/render_tools.py` after editing the public contract.
- Release acceptance: `checks/standalone_acceptance.py` installs offline in a namespace without developer home/source checkout, then exercises the public lifecycle. The unit itself does not require its development isolation tools.

- 2.0 adds `recovery/`, `realization/`, `diagnosis/`, `runner/`, `investigation.py` and `handoff/`. `retro2.schema.json` owns new typed records; the 1.0 contract remains compatible.
- Product acceptance also runs `checks/retro2_acceptance.py`: all four real interventions, typed signed support and portable historical withdrawal/replay. Preserve initial cold-review failures and label repair rechecks accurately.

- 3.0 adds the packaged `research-retro` host skill and `workflow` discovery/context/revision/publication loop on the existing Store/locators/signed support. `retro skill` exposes/install-copies the skill.
- Real-project receipts distinguish initial independent evaluation, revealed repair rechecks and targeted comparisons. Never present these as a general unseen-project benchmark or claim Jev benefit without actual evaluation. Larger Harness integration remains deferred.
- Installed 3.0 acceptance: `checks/retro3_acceptance.py`; run alongside legacy compatibility at release.
- The 3.5 field-gate and forced-context behavior is historical. Its real r655 case stays at `research_cases/retro35/accept_r655.py`; preserve raw failures/receipts and do not reinterpret them as the current defaults.
- The product loop uses direct `record`, separate material-family discovery, a host-selected short `spine`, explicit local `judge`, and the existing state/history/dependency engine. SPINE/MAINLINE use live node text; RESEARCH_MAP keeps detail. Do not add project-specific discovery to core. Next-stage real evaluation lives under `research_cases/product/`, with isolated external source/workspace and evaluator-only references.
- Upstream `triage` prepares byte-bound material for cheap host workers, judges proposed local relations with Jev, and gives strong hosts a source-linked investigation queue. New evidence can generate impact candidates before revision. Preserve generator/model/cost receipts and distinguish candidate signals from scientific state. dsh is an optional configured worker, not a core dependency; its host permissions are not runtime isolation.
