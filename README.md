# Research Retro 1.0.0

A standalone research retrospective unit for a controlling Agent or researcher.
It indexes assets, retains original byte snapshots and provenance, represents
conditional evidence graphs, applies version-bound corrections, and exports complete
handoffs. It makes no model calls and needs no provider, credentials, personal wrapper,
scientific project layout or preinstalled research runtime.

## Install and start

Python **3.11+ on POSIX** is required. Install the release wheel in your own environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install /path/to/research_retro-1.0.0-py3-none-any.whl
.venv/bin/retro init /path/to/research-project
.venv/bin/retro --workspace /path/to/research-project/.retro scan
.venv/bin/retro agent
```

Or from this source checkout: `uv sync`, then `uv run retro ...`. `rh` is an alias
for the same interface. It no longer defaults to a developer's scientific project.
Nothing is installed globally. The only runtime dependency is public `jsonschema`
and its transitive dependencies; a wheelhouse can support offline installation.

The full workflow is **init → scan/read → reconstruct → audit → correct → export**.
The host performs the scientific reasoning using the returned original text and
versioned packets. See [AGENT.md](AGENT.md) for exact commands, compact input examples,
result templates and failure recovery. `retro tools` exports the nine standard
[function definitions](tools.json). `retro call` and direct commands use the same
validation and service code; no host-specific integration code is required.

## Asset boundaries

| Asset | Location and rule |
|---|---|
| Installed engine | `src/research_harness/`: portable services and packaged contracts/manual; runtime never writes here |
| Development regressions | `research_cases/`, `tests/`, `checks/`: excluded from the wheel; historical local paths are fixture provenance only |
| Target state | `PROJECT/.retro/`, or an explicit `--workspace`; config, SQLite, immutable blobs, check receipts and exports stay here |
| Configuration | `WORKSPACE/retro.json`; workspace selection: CLI, then `RETRO_WORKSPACE`, then `CWD/.retro`; no home configuration |

`init PROJECT` defaults to `PROJECT/.retro`. An explicit independent workspace must
be empty on first initialization. The source tree is read-only except for that
explicitly designated state directory, which is excluded from intake. Config uses
project-relative source paths, a 1 MiB capture limit and a 250,000-entry enumeration
limit. Over-budget or unsupported originals remain explicit gaps. A partial scan
reports `enumeration_complete:false`; it never counts as a complete source census.
Configuration changes on an initialized workspace are rejected rather than silently
changing its source authority; initialize another workspace for a new scope.
Set limits at initialization with `--capture-max-bytes N`, `--scan-max-entries N`,
`--exclude COMPONENT` (repeatable) or `--metadata-only`.

The internal Python namespace retains `research_harness` for R2 kernel continuity.
The released distribution is `research-retro`; it contains no research runtime,
model adapter or development case. Existing R2 state and receipts remain untouched.
Historical R2 commands and case adapters are in `research_cases/legacy/`; see the
`r2-0.2.0` tag for that release's original interface. This release does not silently
migrate or reinterpret old scientific state.

## Scientific contract

Captured/parsed, unread, missing original, untested and refuted are separate states.
Reconstruction does not promote historical statements to facts. Qualified evidence
needs a completed scoped audit; numerical/code audits need actual captured execution
receipts. A completed check is still not a certificate of scientific adequacy.

`support_sets` implements outer OR and inner AND with a least fixed point. Revoking
one branch does not destroy another valid branch. Refuted claims **and inferences**
cannot affirm downstream conclusions; the support for a refutation is retained
separately. Corrections retain the original statement, scope, residual assets and
reopening conditions. Original SHA256 changes, relevant read-set changes and policy
changes force reassessment; duplicate bytes and circular arguments add no evidence.

The explicit `audit check` command runs host-authored Python from the workspace for
at most 60 seconds, with captured inputs/output and a scrubbed environment. It has
the caller's OS permissions. It is not an execution sandbox; the controlling host
must review and authorize that code. Scan/reconstruction never execute source scripts.
Native Windows is not certified; WSL/Linux works. No claim is made of automatic
installation or authenticated integration into every named Agent application.

## Release and verification

Freeze tag: **`retro-v1.0.0`**. [Current state](CURRENT_STATE.md),
[acceptance report](releases/standalone-1.0.0/REPORT.md) and
[release manifest](releases/standalone-1.0.0/release.json) retain actual verification.
The acceptance harness builds a clean environment with no developer home or source
checkout, installs an offline wheel, runs a foreign synthetic project through the
public interface and verifies host transport parity plus an independent blank-Agent
handoff. This is a declared synthetic capability test, not a blinded science benchmark.

```sh
uv run python -m unittest discover -s tests -v
uv build --wheel
uv run python checks/standalone_acceptance.py --wheelhouse PATH --output PATH
```

Only the acceptance harness needs Linux `bwrap` for the installation isolation test;
the installed unit does not depend on it. The release bundle includes an offline
wheelhouse and immutable receipts; see the report for exact tested versions and scope.
