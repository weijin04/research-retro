# Targeted repair recheck — acceptance-04

**PASS for the previously failed propagation gate and public replay.** This is a post-disclosure repair recheck, not a new blind assessment. The original failed acceptance-03 reports remain unchanged.

Only the revised handoff, its public documentation and the installed product were consulted. Public operations ran inside bwrap with all namespaces unshared, read-only /venv and /handoff, private /tmp, no original project, source checkout, developer home or network. Overall agent access remains cooperative.

From records and events: support paths were added in events 323–326; event 327 changed `premise:historical-H0` to `accepted:false`; events 331 and 333 supplied the scoped negative judgment and counter-support for H0. I queried checkpoint 326 before the update, then independently selected the affected and independent branches. Exact scopes, IDs, queries and full output are retained in the JSON report.

| Public projection | H0 | C1 | C2 | Controlled gate witness |
|---|---|---|---|---|
| checkpoint 326, no withdrawal | positive | positive | positive | positive |
| checkpoint 326, withdraw H0 premise | neither | neither | positive | positive |
| checkpoint 327, actual premise update | neither | neither | positive | positive |
| current state | negative | neither | positive | positive |
| checkpoint 326, withdraw gate witness | positive | neither | neither | neither |

These are actual nonempty product outputs, with local assertions checking the transitions. The original all-positive state explicitly lists its conditional assumption. Withdrawing that premise removes C1 support while preserving C2's independent route. Withdrawing the other dependency removes both C1 and C2 while preserving conditional H0, establishing that the result is sensitive to the dependency selected.

Withdrawal is distinct from refutation: counterfactual withdrawal sets the premise's `revoked:true` and yields no negative H0 support. Current H0 has `negative_supported:true`, `revoked:false` because a signed review supplies counter-support. C1 remains `neither`; unsupported does not mean refuted. The actual premise revision removes conditional acceptance and remains `revoked:false`, unlike the counterfactual flag, while correctly giving the same downstream loss of support.

A deliberately nonexistent scope now exits 2 with `invalid_contract: No scientific graph in the requested scope`; it no longer returns a vacuous success.

Public replay of `execution:dfb9a30b1b4040619aaa2f6230fa4caf` exits 0 with both predicates true. Its script hash is `f319ebfba07b310d6ca16b56d7bb6afc58d2b6c64e7b5730e80877a770efeaa3`, output hash `a293aa21453eaca1b6e571c109de02865a57a83fc3e7830cbeadd0324d106f48`. The public operation verified 47 package files, with integrity rather than authenticity assurance.

The repaired frozen delivery now passes this targeted finite-scope gate. Live workspace mutation was outside the authorized read-only material boundary and was not directly tested. Controlled probe support does not authenticate historical execution, and none of these results validates a real physical system or arbitrary future scientific reconstructions.
