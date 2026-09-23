# Native diagnostic capture evidence — 2026-09-23

This change follows input audit PR #1 and is independently reviewable as a stacked
PR. It uses native engine formats instead of regular expressions over console
messages. Tests were written first and failed on the absent CLI option; a second
red test exposed zero-status/native-warning handling before it was implemented.

## Tests and real probes

From the repository root, `python3 -m unittest -v` and
`/usr/bin/python3 -m unittest -v` pass all 15 tests on Python 3.14.7 and 3.9.6.
Six new tests exercise both formats, clean empty output, engine failure, absent
and malformed reports, wrong shapes, silent-console native findings and unchanged
default invocations. Controlled engine outputs test failure paths without requiring
new engine flags on the existing Ubuntu CI package. These tests do not establish
compatibility with that package's native formats.

Application pins remain Caliptra v2.1.2
`49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e` and OpenTitan
`7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`. Both worktrees were clean before and
after these probes. Filelists and tops are the three configurations in EVIDENCE.md.

The executable resolved by PATH changed since the earlier audit evidence. This
run used `/opt/homebrew/Cellar/verilator/5.050/bin/verilator`, version
`5.050 2026-07-01 rev vUNKNOWN-built20260701`, and slang
`11.0.448+e222e7dc0`. Do not combine these results with the earlier modified
Verilator 5.051 build as if they were one version.

| Configuration | Engine | Native capture | Engine / wrapper exit |
|---|---|---|---|
| Caliptra SECDED | slang | captured, empty findings | 0 / 0 |
| OpenTitan SECDED | slang | captured, empty findings | 0 / 0 |
| Caliptra SHA256 | slang | captured assertion-macro error, precise location | 1 / 1 |
| Caliptra SECDED | Verilator 5.050 | malformed SARIF retained | 0 / 1 |
| OpenTitan SECDED | Verilator 5.050 | malformed SARIF retained | 0 / 1 |
| Caliptra SHA256 | Verilator 5.050 | captured SARIF with width and other findings | 1 / 1 |

In the clean Verilator runs the emitted object lacks a comma between `tool` and
`invocations`; Python's JSON decoder reports line 15, column 26. A separate broken
SV probe also emitted malformed SARIF. No repair, dropped diagnostic, engine
replacement or source edit was made to manufacture a pass. A compatible Verilator
native-export build is an unresolved qualification requirement.

Plain and native-enabled invocations were compared for all six cases. Their engine
exit statuses and console diagnostics match, excluding only retained Verilator
wall-time telemetry from comparison. Native formats retain source location fields;
this slice does not prove completeness of all locations or a common rule model.
Slang's SHA256 report locates `CALIPTRA_ASSERT_KNOWN` at `sha256_reg.sv:1594:1`.

## Replay and artifacts

Set `CALIPTRA_ROOT` and `OPENTITAN_ROOT` to the pins above, then use the commands in
EVIDENCE.md with `--native-diagnostics` and separate output report paths. For example:

```sh
./qd-lint check \
  --filelist "$CALIPTRA_ROOT/src/sha256/config/sha256_ctrl.vf" \
  --top sha256_ctrl --engine slang --native-diagnostics \
  --json /tmp/qd-sha256-native.json
# Expected exit 1 with the observed assertion-macro diagnostic.
```

The local session bundle `../evidence/native-diagnostics/` contains the paired
plain/native reports and logs, standalone broken-SV probe, exact argv and resolved
executable/version hashes in `summary.json`, plus a replay script. The script
verifies application pins and clean working trees. Those logs are not hosted by
this repository. Temporary native-file paths vary between runs; compare findings
and engine statuses, not complete report bytes.

Qualification remains incomplete: full schemas, severity vocabularies across
versions, stable finding identities, common rule policy, reviewed waivers,
baselines, timeout/resource controls and independent-workspace replays remain
roadmap work. The evidence supports native capture and fail-closed compatibility
handling on these named probes, not production lint or general signoff.
