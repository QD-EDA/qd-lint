# QD-Lint: reproducible project lint evidence

## Current capability

Baseline `780acdfc0fcad0af377b68d33495a7c421bc261b`: four Python tests.
CI installs the distribution Verilator, then runs `python3 -m unittest -v`;
slang is not installed or required there. The runner expands a bounded filelist
syntax, invokes established engines, retains raw diagnostics, and fails warnings.
Its legacy hash covers listed files, not expanded configuration or include closure.
Its `-f` paths are relative to the containing list: this is QD's existing dialect,
not Verilator's native current-directory `-f` semantics. Do not silently change it.

## Stages and interfaces

1. **Next useful slice (this change):** opt-in resolved-input audit in JSON:
   ordered sources, lists, include search paths, defines, top, engine selection,
   per-file SHA-256 and deterministic configuration fingerprint. Inventory all
   regular files recursively under declared include directories, regardless of
   suffix, and fail on symlinks/special entries in that inventory. This catches
   header-only changes and environment-selected roots without parsing SV. Label
   dependency completeness UNKNOWN: source-relative, absolute, implicit tool
   includes and concurrent source edits are not proven closed. Preserve the
   legacy hash and normal lint behavior. No cache may treat this as a full key.
2. **Pinned pilot:** Caliptra `caliptra_prim_secded.vf`, top
   `caliptra_prim_secded_22_16_enc`, plus `sha256_ctrl.vf`/`sha256_ctrl` as a
   diagnostics-retention case. OpenTitan `lowrisc:prim:secded:0.1` `files_rtl`,
   top `prim_secded_22_16_enc`, generic RTL; preserve file order from the pinned
   core. Compare wrapper results against direct Verilator and slang invocations.
   Next expand to pinmux via FuseSoC `fileset_ip`; require the resolved manifest
   to include `pinmux_reg_pkg.sv`. Do not invent a replacement fileset resolver.
3. **Project CI:** import generated FuseSoC/Edalize configurations with explicit
   top/fileset/technology/parameters. Obtain actual preprocessing dependencies
   from each engine and prove closure before enabling incremental reuse. Normalize
   rule/severity/path/line/column with raw-log references; retain unmapped text.
   Add rule policy, reviewed waivers and baselines without deleting findings;
   report new/resolved/unchanged and waived counts separately. Detect stale
   baselines on configuration/tool changes. No warning suppression to get green.
4. **Production qualification:** qualify named lint configurations and a frozen
   rule policy, never all SystemVerilog or ASIC signoff. Include clean and failing
   runs on both projects; ensure every requested engine ran. A missing engine,
   timeout, parse failure, or unknown dependency closure invalidates reuse.

## Evidence and release criteria

- Inputs: direct SV or documented filelists, selected top/engine, environment
  expansions; later a generated configuration manifest and reviewed rule policy.
  Outputs: raw logs, engine versions/argv/status, input manifest and fingerprint;
  later precise normalized findings, baseline deltas and waiver audit trail.
- Unsupported now: generic compiler flags, native `-F`, wildcards/libraries,
  arbitrary build graphs, semantic rule equivalence, automatic waiver approval,
  complete preprocessing dependency discovery. Fail unsupported input explicitly.
- Corpus: original parser cases and broken RTL; header edits, same list with
  different environment roots/defines, source/include ordering, nested lists,
  empty include directories, symlinks, malformed input, missing tools; pinned
  clean SECDED and diagnostic-rich SHA256/pinmux configurations.
- Independent oracles: direct engines with independently assembled argv and
  reviewed upstream core/filelist order; compare exact diagnostic text and exit
  status. Engine agreement is lint evidence, not functional correctness.
- Version matrix: Python 3.9/3.14, Verilator and slang as separate mandatory
  integration lanes. Development observations are Verilator 5.051
  `v5.050-196-g7dcd4e0b6 (mod)` and slang `11.0.448+e222e7dc0`;
  immutable binary/container hashes are required before qualification. Existing
  floating Ubuntu package CI remains a smoke lane, not the qualified matrix.
- Targets: manifest <=5 s/512 MiB for 10k files/100 MiB; bounded pilot lint
  <=60 s/2 GiB; full pinmux lint <=5 min/4 GiB; complete-dependency incremental
  rerun <=20% of full time. Measure before promising these budgets.
- Release: all old tests pass; positive/negative/boundary audit cases pass;
  identical immutable inputs repeat identical fingerprints; relevant input
  changes invalidate fingerprints; direct-engine diagnostics/status match;
  two clean-workspace runs and reviewer-approved policy. No general signoff claim.

## Qualification contract

This is a staged plan, not a production qualification claim. No stage is earned
by a green unit suite alone. Keep existing passing behavior and raw diagnostics.
Do not change application RTL/DV, disable assertions, or introduce dummy VIP to
make a pilot pass. A failed pilot is an artifact to retain, not a test to remove.

Named pilot pins (full SHAs, never floating branches):
- Caliptra RTL v2.1.2: `49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e`, generic simulation primitives;
  Adams Bridge v2.0.3: `b77e3d899e828d626cfc2a0d26a6b5704cc121e0` when needed.
- OpenTitan: `7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`; select the named IP fileset, generic technology,
  and record all FuseSoC flags, parameters, generated files, and their digests.
  The later configuration-blocker evidence at `a78922f14a8cc20c7ee569f322a04626f2ac6127`
  is a separate revision, not interchangeable qualification evidence.

Every release candidate needs an immutable evidence bundle: tool Git SHA and
binary hashes; OS/architecture, Python/compiler/simulator/solver versions;
design and submodule SHAs; top, parameters, defines, ordered files/includes,
constraints, libraries, seeds; input/output hashes; exact argv, raw stdout/stderr,
exit codes, wall time and peak RSS. Repeat twice in clean independent workspaces;
compare canonical findings and explain any nondeterminism. Archive the bundle
with the release and publish a supported/unsupported configuration table.

Review every expected finding and every oracle disagreement. Seed known defects
in separate test fixtures and require their detection; never mutate pilot RTL.
Unknowns and exclusions remain counted and visible. Waivers require a stable
finding/configuration identity, owner, independent reviewer, rationale, evidence
hash/link, expiry, and revalidation on any relevant input change. A waiver is a
review disposition, not a proof. No unreviewed waiver or unexplained oracle
mismatch is allowed in the qualified scope. Outside that scope report UNKNOWN
or a clear unsupported error. A version or dependency change reopens qualification.

Performance numbers below are acceptance targets, not measurements. Measure on
a named Linux x86-64 runner with 8 cores and 16 GiB RAM; record hardware and
median of five runs. No automatic threshold relaxation. macOS arm64 is a second
portability lane, not a substitute for the qualification runner.

## Portfolio priority and real-flow blockers

1. **QD-Lint first:** source/configuration fidelity is prerequisite evidence for
   every downstream analysis. OpenTitan pinmux's conditional `fileset_ip` versus
   `fileset_top` selects different register packages. A local pinned matrix probe
   at `a78922f...` reproduced an omitted-package failure from wrong setup flags;
   it was not an RTL defect. Caliptra's generic/technology primitive roots also
   select different sources. Audit these choices before caching or baselining.
2. **QD-BFM second:** Caliptra's README requires licensed Avery AXI and QVIP AHB
   dependencies in full UVMF flows. A bounded independent AXI adapter is useful,
   but cannot cure simulator/UVM/firmware dependencies or replace their APIs.
3. **QD-CDC, then QD-DFD:** real reset/synchronizer and lifecycle/debug cones are
   available; getting complete elaboration and constraints is the next blocker.
   VCD observations and cell annotations cannot establish safety on their own.
4. **QD-UPF and QD-DFT:** do standards/library/topology inventory now; owner-approved
   power intent and scan-mapped collateral are unverified. Do not invent these
   inputs or mistake lack of collateral for a demonstrated design failure.

Primary source anchors (review pinned source, not just current web documentation):
- [Caliptra dependency and configuration README](https://github.com/chipsalliance/caliptra-rtl/blob/49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e/README.md).
- [OpenTitan pinmux fileset selection](https://github.com/lowRISC/opentitan/blob/a78922f14a8cc20c7ee569f322a04626f2ac6127/hw/ip/pinmux/pinmux_reg.core).
- [OpenTitan lifecycle architecture](https://github.com/lowRISC/opentitan/tree/7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19/hw/ip/lc_ctrl/doc).
- [OpenTitan TL DV agent](https://github.com/lowRISC/opentitan/tree/7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19/hw/dv/sv/tl_agent).
