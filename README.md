# qd-lint

`qd-lint` expands a small, explicit subset of SystemVerilog filelist syntax and invokes installed Verilator and/or slang. It keeps each tool's diagnostics visible and records the exact argv and a SHA-256 snapshot of listed inputs. It is a reproducible local lint runner, not a replacement for SpyGlass/AscentLint or ASIC signoff.

## Requirements and quick start

Python 3 is required. Install Verilator, slang, or both for the requested engine; `both` is the default. This self-contained example creates a temporary design and lints it with both tools:

```sh
tmp=$(mktemp -d)
printf 'module demo(input logic a, output logic y); assign y = a; endmodule\n' > "$tmp/demo.sv"
./qd-lint check --filelist "$tmp/demo.sv" --top demo --engine both --json "$tmp/lint.json"
python3 -m unittest -v
```

Use `--engine verilator`, `slang`, or `both`; direct `.sv`/`.v` paths are accepted as well as filelists. Filelists support nested `-f`, `+incdir+`, `-I`, `+define+`, `-D`, and `${VARIABLE}` expansion. Relative source, include, and nested-list paths are relative to the containing filelist. Missing files/directories or variables, cycles, empty source lists, and unsupported directives fail explicitly. Arguments are passed without shell evaluation.

## Results and limits

For each engine, terminal output and optional JSON include executable/version, actual argv, raw diagnostics, tool exit status, classification, and `source_snapshot_sha256`. That hash covers the explicit filelists and source files only; it does not recursively include headers discovered through HDL preprocessing. A warning is visible and makes the command fail; a zero tool exit with warnings is not a clean pass. JSON is written to the path passed to `--json`.

Exit codes: `0` only when every requested engine completes without warnings; `1` when an engine is missing, exits unsuccessfully, or emits a warning; `2` for malformed input or filelist errors. Diagnostic meaning and language coverage remain those of the selected tools; this wrapper does not provide independent parsing or lint signoff.

## Scoped probe

The Caliptra RTL v2.1.2 `caliptra_prim_secded.vf` top `caliptra_prim_secded_22_16_enc` was run with both installed engines with zero warnings. This covered that listed SECDED RTL hierarchy only; it did not run Caliptra unit tests/DV or establish signoff coverage.
