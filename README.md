# Research Retro 2.0

A local research reconstruction product for a controlling researcher or Agent.
Retro freezes source bytes and Git history, recovers conditional parameters and
execution candidates, manages investigations, runs isolated probes, and delivers
a portable `ReconstructionPackage`. The core makes no model calls or network calls.

## Install

Python **3.11+ on POSIX**. Install into your own environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install /path/to/research_retro-2.0.0-py3-none-any.whl
.venv/bin/retro init /path/to/research-project
.venv/bin/retro -w /path/to/research-project/.retro snapshot
.venv/bin/retro -w /path/to/research-project/.retro recover --snapshot latest
```

From source: `uv sync`, then `uv run retro ...`. `rh` is the same CLI. No global
installation or provider credentials are needed. The release includes an offline
Linux CPython 3.14 wheelhouse; ordinary pip resolves dependencies for other supported
Python environments. Linux `bwrap` and `/usr/bin/python3` are required only for the
optional contained runner. `retro -w WORKSPACE capabilities` checks availability.

## Use the product

The 2.0 workflow is **snapshot → recover → investigate → probe → close → export**.
All state lives in the selected workspace, defaulting to `PROJECT/.retro`.
Scientific source files are read-only. Recovery executes no project code.

| Task | Command |
|---|---|
| Freeze bytes, asset gaps and bounded Git DAG | `retro -w W snapshot` |
| Recover conditional values and historical producer alternatives | `retro -w W recover --snapshot ID` |
| Inspect a finding's original bytes and rule | `retro -w W explain FINDING` |
| Define scope, goals, obligations and material roles | `retro -w W task scope --input scope.json` |
| Start a version-bound evidence-first investigation | `retro -w W task next --scope SCOPE` |
| Read, seal initial hypotheses, then reveal narratives/methods | `retro -w W task packet ID`, `task seal ID --input initial.json`, `task reveal ID` |
| Freeze a discriminating probe | `retro -w W probe plan OBLIGATION --input probe.json` |
| Execute and separately check preregistered predicates | `retro -w W probe run SPEC --isolation required`, `probe evaluate RECEIPT` |
| Submit completed scoped review | `retro -w W task submit TASK --input result.json` |
| Check comparability / signed support / dependency impact | `contrast A B --observable ID`, `support --scope JSON`, `impact ID` |
| Freeze completion and export | `retro -w W close --scope SCOPE`, `export --closure CLOSURE` |
| Query and replay without originals | `retro verify-handoff PACKAGE --query-set queries.json` |

[Agent manual](AGENT.md) contains exact request formats and the result template.
[Function definitions](tools.json) use the same dispatcher as shell commands.
[2.0 record schema](contracts/retro2.schema.json) is packaged in the wheel; `records
--input FILE` imports typed entities with explicit revisions. The 1.0
`scan/read/reconstruct/audit/correct/export/inspect/state` workflow remains available.

`closed-resolved` means all required obligations of the frozen scope have supported
answers. `closed-qualified` retains explicit conditions or demonstrated
non-identifiability. `open-blocked` retains missing work, material or capability.
Completion always refers to the frozen scope, question, rules and obligations.

## What recovery establishes

The initial Python analyzer handles literals, dictionaries, basic arithmetic,
conditionals, bounded loops (up to 64 iterations), captured JSON configuration,
literal shell environment bindings, local module functions and registered stdlib
summaries. Larger loops expose one transition and leave final state unknown.
Unregistered calls and unresolved environments remain explicit unknowns. Static
results depend on the recorded language/library/launcher assumptions.

Historical receipt support currently covers JSON records with source hashes and
output hashes. Matching Git blobs provide candidate histories; they do not establish
that a commit ran. Project receipt contents remain **project asserted**. A broker
receipt establishes the newly controlled execution. Five separate axes describe
termination, output integrity, convergence, model applicability and scientific
qualification. Identical output bytes establish content identity, with execution
and statistical independence retained as separate questions.

Findings are investigation candidates. In particular, a cap or conditional change
can be legitimate under an appropriate model. A named review or a preregistered
predicate provides the relevant scoped judgment. Probe success alone discharges
no scientific obligation. Comparisons require explicit observable, units, reference,
object, boundary and sampling definitions; tolerance never merges identities.

## Runtime and persistence

Cooperative investigations use the host's existing permissions; they cannot promise
blind reading. `task run TASK --script FILE` provides a contained initial evidence
projection. `probe run` uses read-only inputs, private output, network/PID isolation,
closed inherited descriptors, dropped capabilities and resource limits. Required
containment refuses execution when unavailable. The legacy `audit check` retains
its documented host-permission behavior.

Every correction and record update preserves history. Positive and negative support
are separate; conflicts block unconditional downstream use while independent OR
paths remain usable. Withdrawing a witness does not prove its conclusion false.
Results can rebase across unrelated transactions with a receipt; changed related
bytes, revisions or policy require reassessment.

Snapshots hash full captured byte ranges with streaming copies. Per-file consistency
is checked; a whole-tree atomic snapshot requires an external freeze. The default
capture limit is 1 MiB per text file and Git recovery is bounded to 128 commits.
Uncaptured assets, unsupported syntax, missing history and candidate limits remain
visible. Set `--capture-max-bytes`, `--scan-max-entries`, `--exclude` or
`--metadata-only` at initialization. No silent workspace or runtime migration occurs.

`retro migrate OLD_WORKSPACE` is a read-only dry-run. `--destination NEW --apply`
copies historical records into a separate workspace as historical assertions;
missing execution information stays unknown. Existing 1.0 workspaces remain usable.

## Delivery and verification

See [current state](CURRENT_STATE.md) and the [2.0 release report](releases/standalone-2.0.0/REPORT.md).
The architecture source is retained under [research_retro_architecture](research_retro_architecture/README.md).
The shipped implementation is `src/research_harness/`; development cases and test
code are excluded from the wheel. Historical releases remain available by tag.

```sh
uv run python -m unittest discover -s tests -v
uv build --wheel
uv run python checks/standalone_acceptance.py --wheelhouse PATH --output NEW_PATH
uv run python checks/retro2_acceptance.py --wheelhouse PATH --output NEW_PATH
```

The installed acceptance runs without developer home, source checkout or network,
with the installed package mounted read-only. The synthetic case includes a
parameter cap, a changed operator, branch histories, copied results, a stale cache
and a withdrawn premise. Four actual isolated interventions are compared with an
independent discrete formula, followed by portable queries and replay. This measures
the declared product behaviors; it is not a benchmark of arbitrary scientific truth
recovery or a real-project blind evaluation.
