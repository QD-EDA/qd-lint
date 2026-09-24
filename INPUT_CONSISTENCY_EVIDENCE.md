# Audited-input consistency probe — 2026-09-24

QD-Lint `fe66fe78207d5163bb273d5907134505ed5d1827` ran against a clean,
unchanged Caliptra RTL v2.1.2 checkout at
`49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e`. From the QD-Lint root:

```sh
CALIPTRA_ROOT=/path/to/clean/caliptra-rtl ./qd-lint check \
  --filelist /path/to/clean/caliptra-rtl/src/caliptra_prim/config/caliptra_prim_secded.vf \
  --top caliptra_prim_secded_22_16_enc --engine slang --slang-single-unit \
  --audit-inputs --native-diagnostics --json /tmp/qd-lint-consistency.json
python3 -m unittest -v
```

The lint command exited 0 with slang `11.0.448+e222e7dc0` clean (exit 0).
Its executable SHA-256 was
`c38c0fc380ac4c7c48434daa9245d18ad2638b23cd47e14aa82a4a4e7a783ab4`.
The 140-file declared-input inventory matched before and after lint, with
manifest SHA-256
`954f8726de02fe0e40118348534e6163b42f705b2e34bb6163a0818fc77a7be8`.
All 48 Python tests passed, including injected changes to a header, a removed
source, and a removed empty include directory. The complete local command,
JSON report and raw streams are retained under
`evidence/lint-input-consistency-2026-09-24/` in the QD-EDA workspace;
that directory is not part of this repository.

This proves the declared-input consistency gate for the tested cases. It does
not establish preprocessing closure, detect a change restored before the
second audit, qualify any lint rule, or establish production signoff. The real
design probe was one local macOS run; peak memory and independent-host
repeatability were not measured.
