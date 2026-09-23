# QD-Lint v0 scope

Build a reproducible open-source SystemVerilog lint runner for Caliptra-style filelists. It is not equivalent to SpyGlass or AscentLint signoff.

CLI: `qd-lint check --filelist design.vf --top TOP --engine verilator|slang|both [--json PATH]`. Accept direct `.sv` inputs too. Expand nested `-f`, `+incdir+`, `+define+`, `-I`, `-D`, and `${CALIPTRA_ROOT}`-style environment variables deterministically; reject missing variables, missing files, cycles, and unsupported filelist directives instead of silently dropping them. Preserve source order and build one argv per engine without shell evaluation. Print executable/version, exact argv, source snapshot hash, diagnostics, engine exit status, and a result classification. A warning must stay visible; `-Wno-fatal` is not a clean lint pass. Nonzero on an engine error, missing tool, or malformed input.

Use installed Verilator and Slang rather than implementing an SV parser. Normalize diagnostics only to the extent supported by their actual output; retain raw logs. Add cheap tests for nested filelists, defines/includes, cycles/missing env, and an intentionally broken SV module. If viable, run one real pinned Caliptra unit target and record scope/limitations; do not edit Caliptra. Add README, Apache-2.0 license, and local test command. Own only this repo; no commit/push/remote creation.
