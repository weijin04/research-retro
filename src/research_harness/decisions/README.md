# Jev advisory adapter

`from research_harness.decisions import JevAdapter`

`JevAdapter(record_dir: Path, *, endpoint=None, api_key=None, timeout=25, max_attempts=2, transport=None)`

`evaluate(task_family, state, questions, questions_version, policy_version, requested_model='jev-latest', egress_scope='denied', *, content_version='1', candidate_version='1', source_refs=None, attempt_budget=None, use_cache=True) -> dict`

- Uses `TYPESAFE_API_KEY` without printing or persisting it. Endpoint defaults to `https://api.typesafe.ai/v1/systemone`; HTTPS redirects are rejected.
- Only explicit `synthetic` and `public` declarations permit transmission. Caller must establish provenance; this parameter is not a research-data release mechanism or a worker sandbox. Other scopes yield a privacy-denied receipt containing a hash but no plaintext state/questions.
- Every outcome writes an atomic JSON receipt containing request/versions, raw successful or malformed response, raw probabilities, optional confidence, actual model, usage, latency, retry history and advisory action. HTTP errors retain status/category, not arbitrary error bodies that could echo secrets. No answer authorizes scientific state changes.
- Exact `jev-X.Y.Z` requests can reuse receipts only when actual model matches. Aliases never read cache. Content, candidates, questions and policy versions participate in the key. Cache usage is zero and original usage is separate.
- `attempt_budget` is a caller-supplied remaining parent budget, clamped by local maximum (at most three). Parent task accounting must deduct actual `len(record['attempts'])`; this adapter does not own cross-worker resource budgets.
- Passing a test transport produces simulated responses; tests are distinct from real receipts. Service failures and malformed responses return recoverable error records.

Reproduce the real synthetic Noul/Choice/Score smoke with a Chinese validity boundary:

```
rtk proxy env PYTHONPATH=src .venv/bin/python -m research_harness.decisions
```

No research content is sent by this command. Initial real receipt: `var/receipts/jev/f9fbf3ec9ac1468ca92b904f39ec1e4a.json`, actual model `jev-1.13.0`, usage 712 input / 141 output tokens. This is connectivity/contract evidence and a small boundary check, not calibration.

Contract checked against live official https://docs.typesafe.ai/api.md and https://docs.typesafe.ai/primitives/score.md on 2026-09-20; citation workflow informed by https://docs.typesafe.ai/cookbooks/citation_check.md. Local skill: `/home/sun07ao/.claude/plugins/cache/typesafe-ai/typesafe/0.5.7/skills/typesafe-ai/SKILL.md`.
