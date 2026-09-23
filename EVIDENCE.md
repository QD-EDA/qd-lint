# Input-audit evidence — 2026-09-23

This slice adds opt-in input provenance, not a lint rule or dependency resolver.
It proves repeatability for immutable inputs at the same absolute paths and
sensitivity to the tested configuration/header changes. It preserves raw engine
failures. Complete preprocessing closure, relocatable hashes, safe cache reuse,
functional correctness and signoff remain unproven.

## Reviewed baseline and preservation

Before implementation, README, SPEC, tests and `.github/workflows/ci.yml` were
read in all six repositories. Baseline local tests passed: CDC 6, Lint 4, UPF 22,
DFT 9, DFD 7; BFM directed simulations and both injected failures passed.
Their exact baseline SHAs are recorded in each ROADMAP.md. Commands, from each
repository root:

```sh
# qd-cdc, qd-lint, qd-dfd
python3 -m unittest -v
# qd-upf, qd-dft
python3 -m unittest discover -s tests -v
# qd-bfm
./run.sh
```

All six latest baseline CI runs were successful:
[CDC](https://github.com/QD-EDA/qd-cdc/actions/runs/35879684564),
[Lint](https://github.com/QD-EDA/qd-lint/actions/runs/35879690808),
[UPF](https://github.com/QD-EDA/qd-upf/actions/runs/35879490305),
[BFM](https://github.com/QD-EDA/qd-bfm/actions/runs/35880654841),
[DFT](https://github.com/QD-EDA/qd-dft/actions/runs/35879724827),
[DFD](https://github.com/QD-EDA/qd-dfd/actions/runs/35880202630).
CI is a smoke check: its package versions float, and Lint CI only installs
Verilator. Neither green CI nor these unit counts implies production readiness.

After implementation, all nine Lint tests pass under Python 3.14.7 and 3.9.6
(`python3 -m unittest -v` and `/usr/bin/python3 -m unittest -v`, in qd-lint).
The five new tests cover repeatability, content/top/engine/define/source-order
changes, empty include roots/order, symlink cycles/dangling links/FIFO rejection,
read failures, missing engines, canonical hashing and legacy report preservation.
The initial new test failed because `audit_inputs` did not exist. No existing
test was removed, weakened or disabled. Executable code changed only in QD-Lint.

## Named pilot results

Caliptra RTL v2.1.2: `49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e`.
OpenTitan: `7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`.
Both application working trees were clean before and after; no RTL/DV edits.

| Filelist / top | Verilator | slang | Inventoried files | Wall time, both engines |
|---|---|---|---:|---:|
| Caliptra `caliptra_prim_secded.vf` / `caliptra_prim_secded_22_16_enc` | clean, exit 0 | clean, exit 0 | 140 | 0.210–0.212 s |
| Caliptra `sha256_ctrl.vf` / `sha256_ctrl` | diagnostics, exit 1 | diagnostics, exit 1 | 38 | 0.221 s |
| OpenTitan `lowrisc:prim:secded:0.1` `files_rtl` / `prim_secded_22_16_enc` | clean, exit 0 | clean, exit 0 | 175 | 0.205–0.218 s |

Each ran twice on one macOS arm64 host, with identical input manifests and hashes.
These are observed wall times, not the roadmap's Linux performance qualification.
Peak RSS and multi-host reproducibility were not measured. Inventory counts
include unused files in include trees and are not elaborated-source counts.

SHA256 remains a **failed configuration**: Verilator emits WIDTHEXPAND diagnostics
in `sha256_reg.sv` and exits nonzero; slang rejects unresolved
`CALIPTRA_ASSERT_KNOWN` at `sha256_reg.sv:1594`. The tool does not insert defines,
waivers, or suppressions to change either outcome. These results do not establish
whether the underlying hardware is correct or whether another intended project
configuration supplies the missing macro.

Direct-engine oracles: Caliptra was also invoked via each engine's native `-f`
reader; OpenTitan argv was independently assembled from the pinned core's
`files_rtl` entries. All six direct statuses and diagnostic texts matched the
wrapper, excluding only Verilator's `- Verilator: Walltime ...` telemetry line
from comparison. Every raw line remains in the logs. `shasum -a 256` independently
matched every manifest file digest. This checks transport and inventory, not
semantic agreement between engines.

## Versions and replay

Local tools (development builds, not a qualified release matrix):

- Python 3.14.7; secondary tests Python 3.9.6.
- Verilator `5.051 devel rev v5.050-196-g7dcd4e0b6 (mod)`.
  Actual `libexec/verilator_bin` SHA-256:
  `2528034031003877498cf7bc943c183f9c692381d8f0540fa55f7b55d153d6bd`.
- slang `11.0.448+e222e7dc0`. Actual `libexec/slang` SHA-256:
  `d1a8064cfc5b1047d60217e770832bebbdaf10c5b6a5b9ba4a68181564678c7a`.
- Baseline BFM: Icarus `14.0 (devel) (s20260301-381-gb5fdf0647-dirty)`.
  Yosys was not needed to run the baseline Python tests; installed version was
  `0.68+80`, git `621d943ac-dirty`.

Set these to clean checkouts at the SHAs above, then run from qd-lint:

```sh
export CALIPTRA_ROOT=/path/to/caliptra-rtl
export OPENTITAN_ROOT=/path/to/opentitan
# Verify the full pins and empty porcelain output first.
git -C "$CALIPTRA_ROOT" rev-parse HEAD
git -C "$CALIPTRA_ROOT" status --porcelain
git -C "$OPENTITAN_ROOT" rev-parse HEAD
git -C "$OPENTITAN_ROOT" status --porcelain
mkdir -p /tmp/qd-lint-evidence
./qd-lint check --filelist "$CALIPTRA_ROOT/src/caliptra_prim/config/caliptra_prim_secded.vf" \
  --top caliptra_prim_secded_22_16_enc --engine both --audit-inputs \
  --json /tmp/qd-lint-evidence/caliptra-secded.json
./qd-lint check --filelist pilots/opentitan-secded.vf \
  --top prim_secded_22_16_enc --engine both --audit-inputs \
  --json /tmp/qd-lint-evidence/opentitan-secded.json
# Expected exit 1 on these versions; preserve the failure and diagnostics.
./qd-lint check --filelist "$CALIPTRA_ROOT/src/sha256/config/sha256_ctrl.vf" \
  --top sha256_ctrl --engine both --audit-inputs \
  --json /tmp/qd-lint-evidence/caliptra-sha256.json
# Independent native-filelist oracle (repeat for SECDED and with slang --top).
verilator --lint-only --top-module sha256_ctrl \
  -f "$CALIPTRA_ROOT/src/sha256/config/sha256_ctrl.vf"
```

`pilots/opentitan-secded.vf` is the reviewed 37-source expansion of the pinned
core's RTL fileset. Its include-only `prim_secded_inc.svh` is supplied through the
include directory, not compiled as a standalone unit. Tool-specific waiver
filesets are not selected. This is a named unwaived configuration, not a claim
that every upstream default lint target was reproduced.

The full session bundle lives alongside the repositories at
`../evidence/lint-input-audit/`: wrapper reports, raw logs, direct-engine logs,
independent digest outputs, exact argv/environment roots, executable and binary
hashes, elapsed times, and the local replay script. SHA-256 identities at those
original absolute paths:

| Pilot | Input manifest SHA-256 |
|---|---|
| Caliptra SECDED | `c8cf10917a4145eb637a50e4bd70375b66a6d82ea74cc187692fcec02c2eaf66` |
| Caliptra SHA256 | `2bac3bdecd891aa9d0db2b934a9109bd5d03b1a24c0c639e5e76a6c7df3bccbf` |
| OpenTitan SECDED | `1e0eb72abc990722d0b8bec41cc7a145c0ec3c0df2dca055a10cf950f0f34c0f` |

Absolute paths make these relocation-sensitive. The full logs are local session
artifacts, not hosted by this repository. The replay commands and pins are
checked in for reviewers. No independent-workspace production qualification,
complete dependency graph, normalized rule policy, reviewed waiver mechanism,
incremental cache or full OpenTitan/Caliptra DV pass is claimed.
