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

## Resolved input audit (opt-in)

```sh
./qd-lint check --filelist design.vf --top TOP --engine both \
  --audit-inputs --json lint.json
```

`--audit-inputs` adds `input_manifest` and `input_manifest_sha256` to the report.
The manifest records ordered sources/filelists/include directories/defines,
selected top and engines, and per-file SHA-256 values. It inventories **all regular
files recursively under explicitly declared include directories**, including
files without HDL suffixes. Duplicate files are hashed once; argument ordering
and duplicate arguments remain visible. Symlinks inside include trees, special
files and unreadable entries fail with input exit code 2, before either engine
runs. A root resolved by the existing filelist parser is recorded at its resolved
absolute path. The legacy `source_snapshot_sha256` is unchanged.

This is a conservative inventory, not a preprocessing dependency graph:
`dependency_closure_complete` is always `false`. Source-relative, absolute and
implicit tool includes outside those directories, libraries and concurrently
modified files are not covered. Tool versions and argv remain in the engine
results; tool binaries and implicit environment are not in the input fingerprint.
Paths are absolute, so relocation changes the fingerprint. Unused include files
also affect it. Do not use this hash alone for cache reuse or qualification.
Use immutable inputs during a run, and put output reports outside input trees.
Audit cost scales with files and bytes under the declared directories; hashing
reads in 1 MiB chunks. Ordinary runs without this option retain their behavior.

The fingerprint is SHA-256 of UTF-8 `json.dumps(input_manifest, sort_keys=True,
separators=(",", ":"))` using Python's default ASCII escaping. It excludes raw
engine logs and their nondeterministic timing telemetry; those logs are preserved.

See [pilot evidence and replay commands](EVIDENCE.md) and the staged
[qualification roadmap](ROADMAP.md). Neither this audit nor the pilots establishes
complete source closure, functional correctness, or signoff.

## Native diagnostic capture (opt-in)

```sh
./qd-lint check --filelist design.vf --top TOP --engine both \
  --native-diagnostics --json lint.json
```

This requests [slang JSON](https://sv-lang.com/command-line-ref.html#diagnostic-control)
with `--diag-json FILE` and [Verilator SARIF](https://verilator.org/guide/latest/exe_verilator.html#cmdoption-diagnostics-sarif-output)
with `--diagnostics-sarif-output FILE`. Console diagnostics remain enabled.
`--json` is required so the native reports survive temporary-file cleanup.
Each engine result adds `native_diagnostics` with `format`, `status`, original
`raw` text, parsed `data`, and an `error` if capture failed. Native locations,
rule identifiers, source ranges, notes and extra fields are retained as emitted,
not flattened into a lossy common format. Paths must be interpreted against the
invocation working directory, recorded in the native-capture result.

Missing output, invalid JSON/UTF-8, unsupported envelopes or malformed result
containers make capture fail and the wrapper exit 1, even if the engine exits 0.
`exit_status` always remains the engine's status. Native warnings/errors also
prevent a clean result when console output is empty; unknown severity is treated
as error. Envelope checks are not full schema or diagnostic-completeness validation.
Unsupported engine flags are ordinary visible failures: no automatic fallback
or second lint invocation. Invocations without this option are unchanged.

The original native text is retained when UTF-8 decoding succeeds; on invalid
UTF-8 the decoding error is recorded rather than substituting characters. Native
reports can contain source excerpts. Temporary report paths and timing metadata
make full reports unsuitable as deterministic fingerprints. This does not yet
provide cross-engine rule policy, waivers, baselines or SARIF conformance certification.
See [native capture evidence](NATIVE_DIAGNOSTICS.md) for the compatibility failure
found in Verilator 5.050 and the supported evidence boundary.
