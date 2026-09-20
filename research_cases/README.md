# Development and regression assets

This entire directory is excluded from the standalone wheel and source distribution.
It is not a runtime plugin directory and is never searched by the installed engine.

- `grephene/`, `diffusion/`: original R2 scientific case definitions, checks and reports.
  Absolute source locations in these historical materials are provenance references.
- `legacy/`: R2 case dispatch, domain-specific parsing/comparability profiles,
  model-advice experiments and their local configurations. Tests import these adapters
  explicitly. They cannot be selected by an installed `retro` command.
- `R2_ACCEPTANCE.md` and `HANDOFF_REVIEW.md`: historical release evidence, retained
  without upgrading its scientific or runtime scope.

The current synthetic cross-domain acceptance fixture is constructed by
`checks/standalone_acceptance.py`; it uses no private project data. Generated project
state, captures, receipts and bundles are task outputs under ignored `var/`, not
fixtures embedded in the core distribution.

The supported production lifecycle is documented in the repository's `AGENT.md`.
To reproduce the unmodified historical R2 product use tag `r2-0.2.0` and its original
environment and path declarations. Existing R2 stores are not migrated by this release.
