# QD-Lint v0 scope

Build a reproducible open-source SystemVerilog lint runner for Caliptra-style filelists. It is not equivalent to SpyGlass or AscentLint signoff.

CLI: `qd-lint check --filelist design.vf --top TOP --engine verilator|slang|both [--json PATH]`. Accept direct `.sv` inputs too. Expand nested `-f`, `+incdir+`, `+define+`, `-I`, `-D`, and `${CALIPTRA_ROOT}`-style environment variables deterministically; reject missing variables, missing files, cycles, and unsupported filelist directives instead of silently dropping them. Preserve source order and build one argv per engine without shell evaluation. Print executable/version, exact argv, source snapshot hash, diagnostics, engine exit status, and a result classification. A warning must stay visible; `-Wno-fatal` is not a clean lint pass. Nonzero on an engine error, missing tool, or malformed input.

Use installed Verilator and Slang rather than implementing an SV parser. Normalize diagnostics only to the extent supported by their actual output; retain raw logs. Add cheap tests for nested filelists, defines/includes, cycles/missing env, and an intentionally broken SV module. If viable, run one real pinned Caliptra unit target and record scope/limitations; do not edit Caliptra. Add README, Apache-2.0 license, and local test command. Own only this repo; no commit/push/remote creation.

## Additive resolved-input audit

`--audit-inputs` opts into a version-1 JSON input manifest and canonical SHA-256,
covering resolved ordered arguments, listed file bytes and all regular files in
recursive declared include trees. Reject symlinks within those trees, non-regular
files and traversal/read failures before engines run. Always declare dependency
closure incomplete. Preserve legacy hashes, diagnostics, status and default CLI
behavior. Engine-based closure, caching, rule normalization and waivers remain
future work in ROADMAP.md. EVIDENCE.md names the exact bounded real-design probes.

## Native diagnostics capture

`--native-diagnostics --json PATH` requests engine-native diagnostic reports in
addition to ordinary console output. Preserve raw native text and parsed content,
validate the supported envelope, retain engine exit status, and fail on missing
or malformed native output. Native warnings/errors cannot become a clean pass.
No silent fallback or diagnostic suppression. This is evidence capture, not full
schema validation or cross-engine rule equivalence.

## Explicit slang compilation unit

`--slang-single-unit` selects the engine's native ordered single compilation unit
for slang only, records the choice in reports and audited fingerprints, and rejects
a Verilator-only invocation. Defaults and diagnostic gating remain unchanged.
This does not support arbitrary compilation-unit groups or library filelists.

## SARIF invocation completeness gate

In native capture, inspect all inline SARIF invocations in all runs. Require
Boolean executionSuccessful on present invocation objects, fail false values,
and gate execution/configuration notifications alongside result diagnostics.
Missing/unknown notification severity must not become clean. Preserve all raw
content, actual process status and existing non-native behavior. This is a
bounded gate, not full SARIF schema or severity-inheritance support.
