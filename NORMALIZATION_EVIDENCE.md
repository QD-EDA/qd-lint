# Slang diagnostic projection

The pinned slang emitter
[`JsonDiagnosticClient.cpp`](https://github.com/MikePopoloski/slang/blob/e222e7dc0250231312f14c37d47404a49df00fe2/source/diagnostics/JsonDiagnosticClient.cpp)
provides severity/message, optional optionName, and optional file:line:column.
It also preserves include/macro stacks and symbol context in the native record.
QD's opt-in projection keeps one finding per record and a native JSON pointer;
those additional fields and future fields remain in the original native data.
There is no deduplication or invented rule identity. Errors often have no
optionName, so rule_id is null; this cannot yet support stable rule baselines.

Locations are engine-reported coordinates. Absolute paths are lexical, relative
to the recorded working directory; the tool does not resolve aliases or verify
that a SystemVerilog line directive names a physical file. source_verified is always false.
Column units remain the engine's units. Absent locations are not-provided;
malformed locations, pseudo-files beginning `<`, Windows absolute paths and
coordinates outside positive one-to-ten-digit decimal values are unsupported and
mark the projection UNKNOWN. Malformed severity/message/optionName also stays
visible and fails the wrapper, even if the engine exits zero. Native engine status
and reports remain unchanged. Verilator projection is a later adapter; this option
currently rejects both/Verilator rather than claiming normalization there.

Python 3.14.7 and 3.9.6 pass 39 tests: the previous 33 plus six added cases covering
coordinates and pointers, absent locations/rules and empty reports, malformed
fields, oversized coordinates, CLI integration/rejection, and a real slang
undefined-name diagnostic. The real-engine case validates the actual file identity
and that the reported line/column points at the undefined token. This correctly
handles macOS's /var versus /private/var alias. It skips when slang is unavailable.

The unchanged pinned Caliptra SHA256 default separate-unit configuration still
fails with CALIPTRA_ASSERT_KNOWN. The normalized location is sha256_reg.sv:1594:1;
reading that exact source position confirms the macro token. The rule ID remains
null. This verifies this particular mapping, not all slang diagnostics or full
Caliptra lint. Slang used: 11.0.448+e222e7dc0. Application pin:
49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e.

```sh
python3 -m unittest -v
/usr/bin/python3 -m unittest -v
./qd-lint check --filelist "$CALIPTRA_ROOT/src/sha256/config/sha256_ctrl.vf" \
  --top sha256_ctrl --engine slang --native-diagnostics \
  --normalize-diagnostics --json /tmp/normalized-sha256.json
```

Expected wrapper/engine exit: 1/1; normalized status: normalized, one error.
Local raw evidence is in ../evidence/lint-normalization/. Production qualification,
physical source-map verification, cross-engine rule equivalence, reviewed waivers,
baselines and complete dependency closure remain unproven.
