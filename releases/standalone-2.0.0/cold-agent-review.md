# Cold handoff review — original acceptance-03 package

**NOT PASSED overall.** Portable integrity, finite model reconstruction, independent recalculation and public replay pass. Actual premise withdrawal propagation fails.

Mode: **cooperative fresh-context**. Only the handoff and installed product were consulted. The package reconstruction and its answers were read before the independent calculation, so this is not target-blind numerical prediction. Host tools were cooperative; the five runs listed below were actually contained.

Research question: does the archived zero establish that A-to-B is physically impossible, or even that the declared deterministic ensemble population remains zero at 200 s? The frozen model is dp/dt=.04(1-p)-.01p, p(0)=0, dt=.001 s, requested 200000 steps. It is synthetic; no physical-system inference is licensed.

Historical association is conditional: archive-a reports gate/500 steps, diagnostic-b plain/200000. Their receipts and output hashes are internally consistent, but project-created receipts cannot authenticate execution. Two compatible histories remain: the recorded processes ran, or the same files/receipts were copied or fabricated without those runs. Conditional commit candidates are two for archive-a and four for diagnostic-b; source identity cannot uniquely establish the historical runtime.

## Independently posed questions and raw-byte evidence

### Can the archived zero test the requested model and time?
No. MODEL specifies positive k=.04/s, return=.01/s, p(0)=0 and ensemble population at 200 s. Gate replaces .04 with zero because cutoff=.05; archive ends at .5 s. Fixing only cap retains zero; fixing only gate gives .019752558 at .5 s; both gives .799963689 at 200 s.

- `MODEL.md`: `artifact:544cfabf980a9f15416c14c3` r1, bytes [0,243), SHA256 `6daffb746e6666ab6f1e1bf785df8644aa523cf3ffdf55a1b7108894062a836f`.
- `protocol.json`: `artifact:14e23f34e141d509818afef1` r1, bytes [0,171), SHA256 `e94d613286f0707c80fae4943a24c69800bfeb3700fb3f7d1998891a985bc36d`.
- `kernels/gate.py`: `artifact:a23f9338aca629bf708038f7` r1, bytes [0,162), SHA256 `2dcfb893ba36d42e30c96dcd30d250d55f1e65762b3d63a1460bc4d3f9182fe1`.
- `driver.py`: `artifact:d3a88595c80dc1ac89d6c5a5` r1, bytes [0,908), SHA256 `28e8cf444b14a61fc94a34d48a712bbbf0b69a4529e270d547dcded62ff86f2f`.
- `results/archive-a/trajectory.csv`: `artifact:4aab29020e2a54951522652a` r1, bytes [0,251), SHA256 `a2c2105c71acf51b0eac40d26654076c58e173b179bd3690c8991f4b6d5b951d`.

### Do repeat files establish independent evidence?
No. Their bytes equal archive-a and both copy_receipt files explicitly identify archive-a as their source. This supports a documented copy lineage, not authenticated external process history or statistical independence. A deterministic population trajectory is not a stochastic replicate.

- `results/repeat-1/copy_receipt.json`: `artifact:8eacdef54232fbbe6a388ee3` r1, bytes [0,131), SHA256 `aaf7dcb6e932425de9ce8dcc204d79c36772cc8514bc76856350d0f08b9a0089`.
- `results/repeat-2/copy_receipt.json`: `artifact:52862f5a518f645327b9f560` r1, bytes [0,131), SHA256 `aaf7dcb6e932425de9ce8dcc204d79c36772cc8514bc76856350d0f08b9a0089`.
- `results/archive-a/trajectory.csv`: `artifact:4aab29020e2a54951522652a` r1, bytes [0,251), SHA256 `a2c2105c71acf51b0eac40d26654076c58e173b179bd3690c8991f4b6d5b951d`.
- `MODEL.md`: `artifact:544cfabf980a9f15416c14c3` r1, bytes [0,243), SHA256 `6daffb746e6666ab6f1e1bf785df8644aa523cf3ffdf55a1b7108894062a836f`.

### Will a matching protocol cache key make the rendered conclusion valid after kernel/cap changes?
No. Cache key includes protocol.json only; cached p_B=0 comes from archive-a. render.py unconditionally renders this value as physical impossibility. Both interventions leave protocol bytes fixed while changing computed p_B, so that key cannot distinguish scientifically different realizations.

- `cache/population.json`: `artifact:bce87ecf451207037b4a9e90` r1, bytes [0,274), SHA256 `eb941d740d81efc0e43ad73a8b061d27fcd93b05d69cdd27fafcb3b0a841ef50`.
- `render.py`: `artifact:b46add3c18c28e8e85488e9a` r1, bytes [0,169), SHA256 `3a3ee4249db324679b1dc271d74ac12a3eefaa53a88c6b94da34518b4afaa9a6`.
- `protocol.json`: `artifact:14e23f34e141d509818afef1` r1, bytes [0,171), SHA256 `e94d613286f0707c80fae4943a24c69800bfeb3700fb3f7d1998891a985bc36d`.
- `submit.sh`: `artifact:36601f8b9a4da37597f194d3` r1, bytes [0,101), SHA256 `ae8b6d730dc5295747b359b1610fc034f702d2d062e85382e928bd512523c1d0`.
- `driver.py`: `artifact:d3a88595c80dc1ac89d6c5a5` r1, bytes [0,908), SHA256 `28e8cf444b14a61fc94a34d48a712bbbf0b69a4529e270d547dcded62ff86f2f`.

### What survives withdrawal of H0?
C1 AND-depends on H0 and archive-a, so that support route must disappear. C2 only depends on archive-a and can retain the scoped historical-output assertion, with process authenticity still conditional. Positive-rate numerical reconstruction independently survives. The current exported product graph does not execute this reasoning: H0 lookup fails and typed withdrawal returns an empty projection.

- `argument.json`: `artifact:6eca0ade2d7b5883f96601a6` r1, bytes [0,529), SHA256 `ba209b808053117e0d2a8b0a1b634dc40f0289a3ea91f866656249950176b2df`.
- `notes/retraction.txt`: `artifact:2b30b6d2cc04b8783fe957bd` r1, bytes [0,224), SHA256 `ac92a48b1d6bbbb5d548e7f28e54afb49f9a2f96946cd255ca4cbdee440e209c`.
- `results/archive-a/trajectory.csv`: `artifact:4aab29020e2a54951522652a` r1, bytes [0,251), SHA256 `a2c2105c71acf51b0eac40d26654076c58e173b179bd3690c8991f4b6d5b951d`.
- `MODEL.md`: `artifact:544cfabf980a9f15416c14c3` r1, bytes [0,243), SHA256 `6daffb746e6666ab6f1e1bf785df8644aa523cf3ffdf55a1b7108894062a836f`.

## Independent load-bearing calculation

From the captured model and plain Euler implementation, q=1-(k+r)dt and p[n+1]=q p[n]+k dt. Summing the geometric series gives p[N]=k/(k+r)*(1-q^N). The continuous model gives p(t)=k/(k+r)*(1-exp(-(k+r)t)). A new script performed scalar recurrence and separately evaluated the closed form; it did not execute the captured driver.

| gate | steps | duration s | independently iterated p |
|---|---:|---:|---:|
| True | 500 | 0.5 | 0 |
| True | 200000 | 200.0 | 0 |
| False | 500 | 0.5 | 0.019752558048393241 |
| False | 200000 | 200.0 | 0.79996368913533955 |

All archived diagnostic sample points agree with the discrete closed form within 6.9944e-15. At 200 s the continuous value is 0.7999636800561899; Euler error is 9.07915e-9. This establishes numerical agreement for the declared finite model, not physical validity. Increasing the cap alone cannot restore a rate already set to zero.

## Public operation receipts

Contained `inspect /handoff` verified all 46 files (integrity only). Contained `verify-handoff` replay of `execution:ab1d51a684c3435f8c65d7ab2b4766ad` exited 0, with both predicates true. Script SHA256 `f319ebfba07b310d6ca16b56d7bb6afc58d2b6c64e7b5730e80877a770efeaa3`; replay stdout SHA256 `a293aa21453eaca1b6e571c109de02865a57a83fc3e7830cbeadd0324d106f48`.

`withdraw` with `ids:["H0"]` exited 2 (`invalid_state`, message `'H0'`). With the typed hypothesis ID it exited 0 but returned `answer:{}` and `all_passed:true`. The exported records have no relation records and no legacy claim/assumption/inference nodes; C1/C2 dependencies remain historical strings. Thus no before/after support transition was actually demonstrated. The manual dependency explanation above does not pass this gate.

Containment: bwrap unshared all namespaces; read-only installed /venv, /handoff, reviewer scripts and system binaries/libs; private /tmp; no network, /home/sun07ao or /sandbox/case. This covers inspect, independent calculation, replay and both withdrawal calls. It does not make the entire tool-capable agent sandboxed.

## Product usability and completeness

The installed product runs without the original paths and supports an auditable finite reconstruction. The delivery still lacks usable propagation for its own imported dependency assertions. Empty successful withdrawal is especially easy to misread as scientific success. Error text for unknown H0 is not actionable. Public docs need full query examples; inspect floods output with the entire multi-megabyte package. None of these findings required reading implementation source.

Reports contain the exact query results, independent script and complete byte locators. No product or package content was modified.
