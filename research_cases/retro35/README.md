# Research Retro 3.5 real acceptance

`accept_r655.py` copies the complete historical grephene r655 store into a new
external workspace. The original database and Hessian files stay read-only.
It exercises the public workflow, makes real Jev API calls, retains both raw
field judgments, applies the declared rationale/action repairs and checks the
published projection. Discovery receives no branch name and must supply its own
zero-reference candidates in the independent queue and subsequent contexts.

Run only with authorization for node-text/linked-observation-summary egress and
`TYPESAFE_API_KEY` present in the environment:

```sh
uv run python research_cases/retro35/accept_r655.py \
  --original /path/to/historical-grephene-retro3 \
  --workspace /path/to/new-external-retro35-workspace \
  --output var/retro35/acceptance
```

The original must contain the actual r655 database and frozen publication.
Both output locations must be new, preserving prior failures and receipts.
`acceptance.jsonl`, command request/response files and `result.json` are retained
under the receipt directory; actual Jev requests and answers also reside in the
external workspace's `jev/` directory and authoritative state store.

This is a known-defect acceptance on a real historical project. It is not a blind
scientific benchmark, a general discovery score, or a new Hessian calculation.
Offline software tests use synthetic HTTP responses explicitly and are kept
separate from this real API run.
