# Real-project reconstruction receipts

These checks reproduce performed cold handoff calculations using a portable bundle,
without source project access. They do not rediscover the project map and are not
blind scientific-accuracy tests. The original independent scripts and first failures
remain in the 3.0 release evidence archive.

```sh
python3 research_cases/retro3/grephene_cold_check.py GREPHENE_BUNDLE NEW_OUTPUT
python3 research_cases/retro3/diffusion_cold_check.py DIFFUSION_BUNDLE NEW_OUTPUT
```

The grephene check reconstructs the four C3 geometries, actual frozen-element
identities and C4 continuation gate, Q/D atom maps and the corrected NEB CI value.
The diffusion check recomputes all 1024 FLEX and 512 RIGID shots with the actual positive
velocity weighting at three commitment times. Neither script executes original
scientific programs or submits jobs. Captured byte hashes are provenance identities,
not expected scientific answers.

Real source trees stay read-only and are not bundled into the product. Local final
workspace/bundle paths and snapshot hashes are recorded in the release manifest.
The source index is essential: capturing a calculation index does not capture every
run it mentions, and selected byte ranges are not complete data tables.

Read `releases/standalone-3.0.0/REPORT.md` for the independent reference scores,
initial cold failures, revealed repair rechecks, residual discovery, three-arm
comparison and untested scope. No initial failure is replaced by a repaired score.
