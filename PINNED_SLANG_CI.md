# Pinned slang integration lane

The existing distribution-Verilator smoke job remains unchanged. The added Linux
lane requires slang and exercises real parsing, diagnostics and dependency capture
on clean checkouts of the named Caliptra/OpenTitan configurations. It builds slang
`e222e7dc0250231312f14c37d47404a49df00fe2` from source. Four fetched build dependencies
are supplied through CMake's FetchContent source overrides at immutable commits:

| Dependency | Commit |
|---|---|
| fmt | `1be298e1bd68957e4cd352e1f676f00e07dcfb57` |
| boost_regex | `2b3ac0834f31086c6e3c0e0ceb8516e427d5c39d` |
| mimalloc | `acf2fdd329f9dc2a7ffe3f12a133fe7175e39378` |
| tomlplusplus | `30172438cee64926dc41fdd9c11fb3ba5b2ba9de` |

The options come from that slang revision's CMakeLists.txt and
external/CMakeLists.txt. Only the compiler target is built; this does not run or
claim to qualify the upstream compiler test suite. System compiler, CMake, Python
and Ubuntu packages are recorded, not hermetically pinned. Shallow checkout can
change the displayed version suffix; the source commit and binary hash identify
the actual compiler. No floating dependency tags are fetched by CMake.

## Gate and evidence

`ci/run_slang_pilots.py CALIPTRA_ROOT OPENTITAN_ROOT NEW_OUTPUT_DIRECTORY` requires
clean checkouts at the pins in DEPENDENCY_EVIDENCE.md. It runs the same four probes:
assertion-enabled single-unit SHA256, both SECDED configurations, and default
separate-unit SHA256 as the negative configuration. It compares exact native
JSON findings, engine statuses and observed path sets against direct slang `-f`
invocations. Expected file counts (20, 66, 37, 20) are also checked. Preprocessing
must retain `ERR_HWIF_IN: assert property`. This checks assertion syntax inclusion,
not assertion execution or proof. Both application checkouts must remain clean.

The regular 33-test suite runs with slang present, including real source-order,
macro-isolation, broken-module and source-relative-header boundary regressions.
The preexisting Verilator smoke job supplies its separate engine coverage.
Every pilot subprocess has a 120-second timeout; the CI job has a 35-minute limit.

The job uploads raw build logs, CMake cache, source revisions, binary hash, host
packages, test output, exact pilot argv/status/timings, native reports, dependency
lists, preprocessed assertion-enabled RTL and peak-RSS/wall-time observations.
Artifacts survive failed jobs and expire after 30 days; they are development
artifacts, not permanent release qualification bundles.

Run on Ubuntu 24.04 with build-essential, cmake and ninja-build installed:

```sh
bash ci/build_slang_pilots.sh /tmp/new-qd-slang-build
```

Local validation before CI: Python 3.14.7 passes all 33 tests; the pilot runner
passes all four cases with installed slang 11.0.448+e222e7dc0 on macOS. Shell syntax
validation passes. Linux source-build validation is pending the first CI run;
no Linux result is claimed by these local checks.

This lane proves bounded wrapper/engine integration when it passes. The direct
oracle is the same compiler with a different filelist reader, not independent HDL
semantics. It does not establish complete dependencies, cache safety, full-chip
lint, reviewed rule policy, waivers, baselines or production qualification.

## Earlgrey pinmux EDAM lane

The same job now creates a separate Python environment for FuseSoC 2.4.5 and
Edalize 0.6.3. All thirteen resolved Python packages have exact versions and
SHA-256 wheel hashes in ci/pinmux-requirements.txt, selected for Ubuntu x86-64 /
CPython 3.12. The complete dependency set was verified using pip's hash-checking
resolver with that platform/ABI. This lock is not a portable macOS environment;
the supported Linux runner is intentional. System packages remain recorded,
not hermetically pinned.

`ci/run_pinmux_pilot.py OPENTITAN_ROOT NEW_OUTPUT_DIRECTORY` applies the pinned
upstream generic-primitive and Earlgrey mappings via FuseSoC. It rejects
non-deterministic selections and validates the exact 224-entry manifest,
215-source/four-include-directory ordering, generic technology, Earlgrey constants
and pinmux register package. QD's EDAM importer must match Edalize's own reader.
A separate native slang invocation must match zero diagnostics and all 221 observed
file hashes. A deliberately mismatched CLI top must fail before producing a report.
Application sources remain unchanged. Backend deprecation warnings stay in the raw
resolver logs; no compiler warnings or waiver files are suppressed.

The artifact adds package installation/freeze logs, resolver logs, exported EDAM
and original source-directory context, wrapper and native results, exact commands,
negative-case logs, timings and peak RSS. Exported application source copies are
excluded from upload; recreate them using the archived pins and setup command.
The existing four Caliptra/OpenTitan probes and all unit tests still run first.

Local validation: the complete pinmux runner passes with the recorded macOS tools
and isolated resolver environment; the missing-tool invocation fails explicitly.
All 45 tests pass, shell syntax is valid, and the Linux wheel lock resolves with
--require-hashes. The added Linux pinmux lane awaits CI; this does not claim
production qualification or full upstream DV parity. See EDAM_EVIDENCE.md for the
configuration contract and remaining limits.
