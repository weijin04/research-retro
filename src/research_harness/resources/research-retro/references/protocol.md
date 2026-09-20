# Public request examples

Commands return `{"ok":true,"result":...}` or a structured error. Use `retro tools`
for the equivalent JSON functions and `retro call --input FILE` in any host. No
host-specific SDK, model runtime or database access is needed.

## Generate and judge discovery candidates before synthesis

For everyday use, let the product connect the steps:

```sh
retro start PROJECT --workspace W --worker dsh --jev
retro -w W discover
```

Read `W/discovery/latest.md`, choose consequential original checks, and record the
resulting understanding. The next `discover` continues the material pass without
hand-editing an offset. `--question` starts a separate scientific inquiry;
`--query` narrows paths; `--overview` only surveys material and never calls models.
`--worker 'your-worker --json'` accepts the same packet on stdin and candidates on
stdout. No Jev permission means candidates are retained without a Jev verdict.
The dsh shortcut passes bounded text directly when it fits, avoiding repeated tool
reads; larger packets use a named packet file. Its existing model settings stay intact.

The following low-level commands are for targeted material or custom host work.

```sh
retro -w W triage prepare
```

The result points to a `packet.json` containing the goal, bounded source text,
byte hashes, partial-capture flags, current node versions and worker instructions.
Give it to a cheap worker in the current host. To choose material explicitly:

```json
{"materials":[{"path":"notes/old.md"},{"path":"runs/result.json"}],
 "bytes_per_file":12000,"question":"What attempts or connections are missing from the current understanding?"}
```

Run `triage prepare --input selection.json`. Missing or binary material remains
listed. Default selection is a bounded directory census, not scientific relevance.
Workers should search related material when context is missing; a partial excerpt
does not establish that the rest of the file lacks evidence.

The worker returns this shape (all quoted text below is illustrative):

```json
{"packet":"triage-ID-from-prepare",
 "generator":{"name":"cheap worker","model":"actual configured model"},
 "candidates":[
  {"id":"c1","kind":"support","title":"Does the saved observation support the broad claim?",
   "evidence":[{"material":"m2","quote":"exact contiguous original text"}],
   "target":{"text":"The specific proposed claim","material":"m1","quote":"exact original claim text"},
   "why":"A possible condition or inference mismatch worth investigating.",
   "next_check":"Inspect the original method and compute the discriminating quantity."}
 ]}
```

Kinds are `support`, `scope`, `genealogy`, `impact`, `route`, `action`; they select
local question templates, not scientific node types. `scope` also requires a
`dimension`, such as sampling conditions. For `genealogy`, evidence is the possible
retelling and target is its possible underlying source. `target.node` uses a current
node from the packet; a target without source/node is an unverified proposal.
`quote` must match exactly; program checks it before any Jev request.
For `action`, `target.text` names the actual action, not a historical result or the
worker's separate `next_check`. Planned observations do not establish acquired data.

```sh
retro -w W triage judge --input candidates.json
retro -w W triage queue --limit 20
```

Authorize the explicitly selected state with `start --jev` or
`authorize_egress:true` in the request. Calls use bounded per-relation state and
parallel network requests (default 4, configurable `workers`). All distributions,
errors, candidate inputs, actual API model, tokens and timing are retained. Identical
questions on unchanged captured bytes/node revisions reuse receipts; `recheck:true`
explicitly calls again. No probability threshold promotes or rejects scientific state.
`partial` describes the captured file range. Local excerpts also report
`context_truncated`, character ranges and decoding replacements; even a fully
captured file is not necessarily shown in full to Jev.

The strong host now chooses high-information original checks from the queue, changes
the scientific representation when needed, and records actual findings with
`triage_receipts:["semantic:ID", ...]`. Investigated items remain in queue history.
`DISCOVERY_QUEUE.json` travels in exports, alongside original blobs and raw receipts.
Numerical verification and final scientific decisions stay with the strong host.

Any host can generate candidates. Optionally, `triage generate --input worker.json`
runs an explicit argv command with the packet on stdin and JSON on stdout:

```json
{"packet":"triage-ID","command":["your-cheap-worker","--json"],"timeout_s":900}
```

A configured dsh can instead read the named packet through its tools:

```json
{"packet":"triage-ID","command":["dsh","--profile","headless",
 "Read ONLY /absolute/W/triage/triage-ID/packet.json. Follow its candidate-worker instructions. Return ONLY the complete candidate JSON on stdout, without markdown fences. Do not modify source or run scientific calculations."],"timeout_s":900}
```

dsh uses its configured model; select the intended cheap model in that host.
The worker runs with host permissions, not a Retro runtime sandbox. It is optional,
not a dependency. stdout/stderr and command timing are retained in the workspace.
Report actual model/usage from host receipts; do not invent unavailable cost figures.

For later evidence, `triage impact --input changed.json` prepares each supplied
material separately and pairs it with every current claim/route/assumption/question
or node with an action. Use the same `materials` input as prepare. This finds
candidate effects outside declared dependencies before the host decides what to
revise; it changes no scientific node.

## Record a completed investigation

Create this JSON in the Retro workspace after actually reading/checking the material:

```json
{
  "question": "What does this attempt establish?",
  "reviewer": "host or researcher identity",
  "analysis": "Completed original check and what follows from it, not just a plan.",
  "materials": [
    {"key":"data","path":"results/table.csv","role":"evidence"},
    {"key":"method","path":"method.txt","role":"definition","start":1,"end":20},
    {"key":"old","path":"notes/previous.md","role":"history"}
  ],
  "nodes": [
    {"id":"obs:result","type":"observation","title":"Observed result",
     "statement":"The measured result in its actual conditions.","status":"observed",
     "scope":{"conditions":"actual object, units, method, time and limits"},
     "rationale":"What was checked and how.","sources":["data","method"]},
    {"id":"claim:interpretation","type":"claim","title":"Current interpretation",
     "statement":"The bounded inference supported by this observation.","status":"supported",
     "scope":{"conditions":"the same conditions and explicit assumptions"},
     "rationale":"The completed argument, and why alternatives remain or fail.",
     "supports":[["obs:result"]],"sources":["method"],
     "details":{"alternatives":["an explanation not yet distinguished"]}},
    {"id":"route:next","type":"route","title":"Continue this route",
     "statement":"What is still open and why it matters.","status":"open",
     "scope":{"conditions":"scope of the proposed test"},
     "rationale":"The observation needed to distinguish remaining explanations.",
     "requires":["claim:interpretation"],"action":"The concrete next check."}
  ]
}
```

Run `retro -w W record --input W/investigation.json`. This is one operation for a
completed investigation; it captures originals, stores scoped scientific nodes and
updates existing views. Examples describe the format, not scientific evidence.

- Types: `question`, `object`, `attempt`, `observation`, `assumption`, `claim`,
  `route`, `turn`, `gap`, `asset`. Use details for negative knowledge, contradictions,
  intended vs actual execution, reusable code and unusual domain-specific needs.
- Statuses: `observed`, `conditional`, `supported`, `open`, `untested`, `paused`,
  `rejected`, `withdrawn`, `superseded`, `implementation_failed`.
- Each node requires id/type/title/statement/status/scope/rationale. `scope` can be
  a small object using the distinctions the actual investigation needs.
- `sources` selects material keys. Observations require sources. Claims with status
  supported require `supports`, an outer OR of inner AND support paths.
  `counters` has the same syntax for scientific counterevidence. `requires` binds
  indispensable context; `links` is navigation only, without support propagation.
- `materials.path` is source-relative or an absolute path inside the source project.
  `start/end` select 1-based lines; `bytes:[start,end]` captures a bounded byte range.
  Include `sha256` from `retro read` to require the exact bytes you inspected.
  Line numbers inside byte segments are relative to that segment. Capture complete
  datasets needed by a handoff task; an index is not its referenced originals.
- Optional `checks:["checks/recompute.py","checks/result.json"]` snapshots your
  workspace files and exports them as host-generated checks. Retro does not claim
  to have executed them. Keep analysis tied to the actual output.
- Discovery example: add `details.discovery` to a normal question/route/gap with
  `finding`, `importance`, `next_check`, and the materials that motivated it. The
  discovery list then carries a scientific candidate, not a random file preview.

## Revise, merge or split

If later evidence is outside the original project, run `retro -w W add-source /path/to/evidence-directory`.
This adds a read-only source and preserves the existing state. Use absolute material
paths for additional sources; primary-source relative paths keep their meaning.

Read `workflow show ID` for the current record, originals and past revisions;
`workflow impact ID` identifies declared dependents and lexical candidates.
`workflow view` returns all current nodes, while `state history ID` returns history.

For every existing node that you replace or reference in requires/supports/counters,
include the revision you actually inspected:

```json
{"question":"What changes with the new evidence?","reviewer":"host",
 "analysis":"The performed recheck and its interpretation.",
 "revisions":{"obs:result":1,"claim:interpretation":1,"route:next":1},
 "materials":[{"key":"new","path":"results/new.csv","role":"evidence"}],
 "nodes":["full replacement records go here; this placeholder is not executable"]}
```

New nodes can refer to each other in one record operation. Only named existing
nodes are replaced; other records and independent support stay. A replacement is
a full node, so update rationale/actions and retain needed scope/sources explicitly.
Old versions remain in history. A changed required premise marks dependents for
review; editing only revision pins does not establish a new scientific conclusion.
For splits, mark the former object/route superseded and add the distinct replacements.

## Arrange the short scientific spine

```json
{"sections":[
  {"title":"What we are trying to understand","nodes":["question:main"]},
  {"title":"How the routes evolved","nodes":["route:old","turn:correction"]},
  {"title":"What holds now","nodes":["claim:interpretation"]},
  {"title":"Where to continue","nodes":["route:next"]}
]}
```

Use actual IDs with `retro -w W spine --input W/spine.json`, then
`retro -w W workflow publish`. The headings establish order; all scientific prose
comes from the current nodes. Short statements belong here; large tables and long
reasoning remain in the linked map. `MAINLINE.md` is a compatibility copy of SPINE.
A draft default order is supplied until you select one.

## Explicit local Jev judgment

Enable through `start --jev` or add `authorize_egress:true` to this explicit request:

```json
{"purpose":"Triage a bounded set of historical findings for investigation",
 "state":{"current_question":"the actual question",
          "candidate_a":"source-backed observation and its conditions",
          "candidate_b":"another source-backed observation and its conditions"},
 "questions":{
   "a":{"type":"noul","instructions":"Does candidate_a in this state bear on current_question?"},
   "b":{"type":"noul","instructions":"Does candidate_b in this state bear on current_question?"}
 }}
```

`retro -w W judge --input W/judgment.json` sends exactly the selected state/questions.
Noul returns a `noul` probability. Choice uses a map of named `criteria`; Score uses
2–10 ordered criteria and returns a score/distribution. Independent questions share
state in one call. Optional `revisions:{ID:VERSION}` binds inspected local records.
The receipt includes input, output, usage, timing and API failures. Inspect the raw
answer; there is no default threshold and no automatic change to scientific state.
Do not send entire datasets or use Jev for arithmetic/open-ended reconstruction.

## Optional staged review and completion assessment

`workflow context --input FILE` selects question/materials/focus. Definitions and
evidence appear first; historical spans appear after `workflow seal ID --input FILE`
(with completed `analysis` and `alternatives`) and `workflow reveal ID`. Use the
returned `apply_template` with `workflow apply`. For an ordinary working context,
set `mode:working`, or use the one-step `record` command above.

After performing an actual residual review and fresh-reader follow-up, record an
assessment with `workflow assess --input FILE`:

```json
{"reviewer":"identity", "coverage":{"sufficient":true,"basis":"What was recovered and checked"},
 "residual_review":{"samples":[{"path":"historical material","finding":"What reading found"}],"material_omissions":[]},
 "handoff":{"passed":true,"tasks":["The actual follow-up task"],"receipt":"saved work and result"},
 "limitations":["Explicit scope not reconstructed or unresolved science"],
 "scientific_problem":"The scientific questions still open",
 "continuation":"The concrete next investigation"}
```

These are host reports; do not claim a task happened without its actual receipt.
`workflow publish` and `export` work with draft states. Changed science makes the old
assessment outdated, retains the previous publication and updates current views.
An exported bundle includes captured originals, your attached checks, all revisions,
SPINE, RESEARCH_MAP, SOURCE_INDEX, HANDOFF and a browser reader. Its START_HERE is the
new Agent's entry; `retro inspect BUNDLE` verifies hashes offline. An unlisted original
is not captured. Future revisions belong in an active workspace, not a frozen bundle.

`retro inspect BUNDLE` returns compact verification and the reading entry. `--full`
returns complete state; legacy JSON `retro_inspect` clients retain that full default,
so use `full:false` in new function calls. A source/check filename may have multiple
captures. Resolve the blob bound to the relevant node and revision; host-check
entries in SOURCE_INDEX record `used_by` and capture time. Do not select by array order.
