# Explicit compilation-unit evidence

The SHA256 macro error in the earlier evidence was a compilation-unit mismatch.
Caliptra's filelist lists `caliptra_sva.svh` before `sha256_reg.sv`, which uses its
macro without a local include. Slang defaults to separate compilation units;
its documented `--single-unit` shares preprocessing scope across ordered files.
See the [official manual](https://sv-lang.com/user-manual.html#compilation-units).
QD-Lint now exposes this as `--slang-single-unit`, without changing defaults or
trying alternative configurations automatically.

## Named probes

Application pins: Caliptra v2.1.2 `49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e`;
OpenTitan `7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`. Both worktrees were clean
before and after runs. No application source or diagnostic suppression changed.

| Slang configuration | Engine / wrapper exit | Native findings |
|---|---|---|
| SHA256, default separate units | 1 / 1 | Unknown `CALIPTRA_ASSERT_KNOWN` |
| SHA256, single unit, upstream default defines | 0 / 0 | Empty |
| SHA256, single unit, `CLP_ASSERT_ON` | 0 / 0 | Empty |
| Caliptra SECDED, single unit | 0 / 0 | Empty |
| OpenTitan SECDED, single unit | 0 / 0 | Empty |

Assertions are disabled by the default Caliptra macro configuration. The checked-in
`pilots/caliptra-sha256-assertions.vf` explicitly enables them and includes the
unchanged upstream filelist. Independent preprocessing with `slang -E` confirms
`ERR_HWIF_IN: assert property` exists in that configuration. This proves assertion
syntax reaches the frontend; it does not prove temporal properties or execute DV.
No claim of full upstream DV configuration parity is made.

For every row, the engine's own `-f` reader independently reproduced the wrapper's
engine status and native JSON findings. This is a transport/configuration oracle,
not an independent HDL semantic implementation. Verilator is unchanged: the
earlier width findings and native SARIF incompatibility remain unresolved.

## Commands and version matrix

Slang `11.0.448+e222e7dc0`; Python 3.14.7 and Apple Python 3.9.6. Both Python
versions pass all 22 tests (17 existing, five new). The real slang regression
checks default macro isolation, successful ordered sharing, and reversed-order
failure against direct engine invocations. It explicitly skips if slang is absent;
current CI installs only Verilator, so green CI cannot prove slang compatibility.
Other tests check engine isolation, rejected irrelevant options, preserved
diagnostics and compilation-mode fingerprint sensitivity.

From the repository root, with `CALIPTRA_ROOT` and `OPENTITAN_ROOT` set to the pins:

```sh
python3 -m unittest -v
/usr/bin/python3 -m unittest -v
./qd-lint check --filelist pilots/caliptra-sha256-assertions.vf \
  --top sha256_ctrl --engine slang --slang-single-unit \
  --audit-inputs --native-diagnostics --json /tmp/qd-sha256-assertions.json
slang --lint-only --top sha256_ctrl --single-unit \
  -f pilots/caliptra-sha256-assertions.vf --diag-json /tmp/direct-sha256.json
slang -E --single-unit -D CLP_ASSERT_ON \
  -f "$CALIPTRA_ROOT/src/sha256/config/sha256_ctrl.vf" > /tmp/sha256-preprocessed.sv
```

Repeat the wrapper and native-reader commands with the original SHA256 filelist,
with and without the single-unit options, for the first two rows. SECDED commands
are in EVIDENCE.md; add the corresponding single-unit option for these probes.
Local raw logs, exact argv, report hashes, timings and replay script are in
`../evidence/lint-compilation-unit/`, not published release artifacts. Observed
wrapper wall times with audit/native capture were 0.071–0.086 seconds across the
five initial probes on this macOS host; this is not a scaling benchmark.

A fresh QD-Lint clone passed all 22 tests and repeated all five pilot outcomes
against the same clean application checkouts. Native findings matched after
resolving locations against each report's working directory. The initial raw
comparison correctly failed because slang renders the default SHA256 error with
a relative path; both original reports remain retained. This is tool-workspace
reproduction, not an independent application checkout or second-host qualification.
The actual `oss-cad-suite/libexec/slang` binary SHA-256 was
`d1a8064cfc5b1047d60217e770832bebbdaf10c5b6a5b9ba4a68181564678c7a`.

The source-only legacy hash intentionally remains unchanged by compilation mode.
The audited manifest hash changes. Defaults retain the old report shape and hash.
Grouped compilation units, library search, full preprocessing dependency closure,
cross-engine rule equivalence and production qualification remain unsupported.
