# Research Retro

Turn an existing, long-running research project into an understandable scientific
state: its questions, objects, attempts, route history, reliable results, revised
interpretations and useful next work, with links back to original material.

Cheap workers in your host propose source-backed candidates; Jev judges repeated
local relations before a strong Agent investigates their scientific meaning. Retro
keeps the evidence, history, state and handoff. The original project stays where it
is, read-only; new outputs live in a separate workspace. Worker and Jev services
are optional; the same product also supports direct host investigation.

## Install and start

Python 3.11+ on POSIX. Install the supplied wheel in its own environment:

```sh
python3 -m venv retro-env
retro-env/bin/python -m pip install /path/to/research_retro-3.6.0-py3-none-any.whl
retro-env/bin/retro start /path/to/project --workspace /path/to/project.retro
```

Give the generated **START_HERE.md** to your research Agent with your actual goal.
It contains the source/workspace paths and the complete installed host workflow.
You do not need to create an ontology or arrange a set of investigation obligations.
Repeat `start` to resume; omit `--goal` to retain the existing goal. The default
workspace is the sibling `PROJECT_NAME.retro`.

To use an already configured cheap worker, select it once:

```sh
retro start /path/to/project --workspace /path/to/project.retro --worker dsh --jev
```

The Agent can then run `retro -w /path/to/project.retro discover`. It prepares the
next material batch, generates candidates, asks authorized local Jev questions and
writes **discovery/latest.md**. Repeating the command continues the pass. The dsh
adapter uses your configured model (v4.1flash in the development setup); any JSON
stdin/stdout worker command can be supplied instead. Omitting `--jev` keeps worker
candidates unjudged and usable. `discover --overview` is a quiet material survey.

From this checkout, use `uv run retro start ...`. For an offline installation, unpack
the supplied wheelhouse and add `--no-index --find-links /path/to/wheelhouse` to pip.
The bundled offline dependencies are for the tested Linux/CPython platform; the
product wheel itself is pure Python. This repository is not required after install.

The same commands work through shell access in Codex, Claude Code, Pi, OpenCode or
another strong host. `retro tools` exposes JSON functions, `retro call` invokes them,
and `retro skill --destination NEW_DIRECTORY` copies the packaged host skill.
No particular host SDK or model harness is required. Actual host/platform tests are
reported in [CURRENT_STATE.md](CURRENT_STATE.md); interface compatibility is not a
claim that every host has been tested.

## What the researcher receives

- **SPINE.md** and **index.html**: a short account of the scientific questions,
  important route changes, current understanding, dead/paused work and next entry.
- **RESEARCH_MAP.md**: full scoped statements, reasoning and connections; the browser
  can search all nodes without expanding them into the short spine.
- **HANDOFF.md**, **SOURCE_INDEX.json**, **NAVIGATION.md** and captured originals:
  practical entry, precise source navigation, retained checks and revision history.
- **SCIENTIFIC_STATE.json**: the same current understanding for another Agent.

`retro -w WORKSPACE workflow publish` updates `current/` and keeps a frozen
publication. `retro -w WORKSPACE export` produces an offline bundle whose
START_HERE.md is the recipient's entrance. `retro inspect BUNDLE` verifies all hashes.
An exported bundle is historical; later revisions belong in the active workspace.

## The working loop

The host first surveys material families and history, then follows scientific
questions with its own tools. Discovery and focused reasoning use separate contexts.
Cheap workers propose source-backed local relations from bounded material packets;
Jev judges support, scope and possible derivation before the strong host forms its
mainline. The resulting relation queue guides deeper original checks and representation
changes. An unexplained old result should become a scientific question, route or
missing connection.

```sh
retro -w WORKSPACE discover
retro -w WORKSPACE record --input WORKSPACE/investigation.json
retro -w WORKSPACE spine --input WORKSPACE/spine.json
retro -w WORKSPACE workflow publish
```

`retro skill` explains the method; generated `host/references/protocol.md` includes
complete input examples. `discover --question "What might the current understanding miss?"`
starts a new discovery pass. The lower-level `triage` commands support explicit
material selection and custom host workers; `triage impact` finds possible effects of new
evidence before revision. Jev requests require explicit workspace authorization.
`record` saves a completed investigation in one operation:
selected original spans, scientific nodes, reasoning, support and optional check
scripts/results. The host can revise questions, split objects and change routes.
The existing node types suffice; details can express domain-specific distinctions.

For difficult disputed claims, optional `context/seal/reveal/apply` preserves an
initial interpretation before revealing historical prose. It is not required for
ordinary recording. Source hashes, inspected revisions and declared AND/OR support
are still checked; they do not substitute for the host's scientific reasoning.

For a newly supplied evidence directory, use `retro -w WORKSPACE add-source /path/to/evidence` without editing the original project.

When evidence changes, use `workflow refresh` and `workflow impact ID`, investigate
what actually changed, then record revised interpretations/routes/actions together.
Only the affected records change; independent results and prior versions remain.
The short spine reads current node content. A stale dependent's previous advice is
withheld there while its complete record stays in the detailed map and history.

A fresh Agent should perform an actual next task from the handoff. `workflow assess`
records that work, coverage and limits; draft states can still be published and used.
A reconstructed project can retain open scientific questions.

## Optional Jev

Add `--jev` to `start` to authorize explicitly selected local state/questions to
TypeSafe, using `TYPESAFE_API_KEY`. Use `triage judge` for candidate batches before
scientific synthesis and `triage impact` before revision. `retro -w W judge --input
judgment.json` also accepts custom relevance, identity, scope, support or action judgments.
The host chooses typed Noul/Choice/Score questions; independent questions can share
one request. See the packaged examples and [TypeSafe API](https://docs.typesafe.ai/api).

Requests, raw answers, model, token usage, timing and failures are retained. Calls
are explicit: configured discovery and triage judge/impact send their selected state;
record, refresh, resume and publish do not. Model advice
neither changes scientific state nor supplies a probability gate. Offline work is
fully usable. Historical 3.5 field-only authorization stays narrow until explicitly
extended; its premise/action questions remain available as `workflow semantic-review`.

## Existing recovery and audit tools

The 2.0 **snapshot → recover → investigate → probe → close → export** lifecycle
remains available. It supplies conditional historical execution recovery,
comparison, isolated discriminating probes and signed support. The 1.0
`scan/read/reconstruct/audit/correct/export/inspect/state` interface also remains.

[Agent manual](AGENT.md) contains the full contract;
[function definitions](tools.json) use the same dispatcher as shell commands.
The [2.0 record schema](contracts/retro2.schema.json) is packaged with the tools.
A 2.0 `closed-resolved`, `closed-qualified` or `open-blocked` result concerns its
frozen declared obligations; whole-project scientific discovery belongs to the
host reconstruction workflow above.

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

[CURRENT_STATE.md](CURRENT_STATE.md) records the installed acceptance, actual
reconstruction, first failures, subsequent repairs, cold handoff and revision checks.
Historical 3.0/3.5 evidence remains under releases/ and research_cases/; it is not
silently reinterpreted as an unseen-project benchmark or Jev benefit.

```sh
uv run python -m unittest discover -s tests -v
uv build --wheel
uv run python checks/standalone_acceptance.py --wheelhouse PATH --output NEW_PATH
uv run python checks/retro2_acceptance.py --wheelhouse PATH --output NEW_PATH
uv run python checks/retro3_acceptance.py --wheelhouse PATH --output NEW_PATH
```

The installed acceptance uses a fresh offline namespace without developer home or
source checkout, and a read-only installation. Development isolation tools are not
runtime requirements. The public core contains no local-project adapters; historical
cases and scientific parsers remain outside the wheel.

`retro inspect BUNDLE` returns compact verification and the reading entry. `--full`
returns complete state; legacy JSON `retro_inspect` clients retain that full default,
so use `full:false` in new function calls. A source/check filename may have multiple
captures. Resolve the blob bound to the relevant node and revision; host-check
entries in SOURCE_INDEX record `used_by` and capture time. Do not select by array order.
