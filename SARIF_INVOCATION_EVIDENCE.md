# SARIF invocation failure evidence

A native report with no rule results could previously pass despite declaring a
failed invocation or warning/error tool notification. Five added tests cover
that failure, multi-run/multi-invocation notifications, optional/successful
invocations, malformed containers and unresolved severity. The initial regression
run had nine failing assertions/subtests. All 27 tests now pass under Python
3.14.7 and Apple Python 3.9.6; existing tests remain unchanged.

## Semantics and support boundary

The normative reference is [OASIS SARIF 2.1.0 plus Errata 01](https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os-complete.html),
sections 3.20.14, 3.20.21–22 and 3.58.6. Invocation success is explicit and distinct
from a process's numeric exit status. Tool notifications describe execution or
configuration conditions, separate from findings about source artifacts.

QD-Lint requires Boolean executionSuccessful for each present inline invocation;
false forces error. Every inline execution/configuration notification participates
in gating. Explicit error/warning severities fail; note/none are retained without
failing by themselves. Missing/unknown severity forces error because descriptor
and configuration inheritance are not implemented. This conservative limitation
can reject valid inherited informational notifications; it does not silently
choose a more permissive severity. Optional absent/empty invocations remain
accepted. Invalid containers fail capture, preserving raw text.

This does not validate full SARIF, resolve external property files, certify
complete engine output or implement rule policy. Actual engine exit_status stays
unchanged; a captured report may independently have classification error. Normal
console-only runs and slang capture are unchanged.

## Pinned real-design regression

Repeated the six native probes and their six console-only counterparts from
NATIVE_DIAGNOSTICS.md. Caliptra is clean commit
`49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e`; OpenTitan is clean commit
`7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`. No application sources were edited.

| Configuration | Native engine | Capture / classification |
|---|---|---|
| Caliptra SECDED | slang | captured / clean |
| OpenTitan SECDED | slang | captured / clean |
| Caliptra SHA256, default compilation units | slang | captured / error |
| Caliptra SECDED | Verilator | malformed capture / error |
| OpenTitan SECDED | Verilator | malformed capture / error |
| Caliptra SHA256 | Verilator | captured / error |

Verilator 5.050 still emits malformed SARIF on the clean cases; no repair or
fallback is applied. Slang is 11.0.448+e222e7dc0. Plain/native engine exit statuses
and console text match after excluding Verilator's wall-time telemetry from the
comparison only; raw logs retain it. These real probes preserve known behavior;
the new failure branches are exercised by controlled engine-output fixtures,
not claimed as failures reproduced by current upstream engines.

Commands (set CALIPTRA_ROOT and OPENTITAN_ROOT to the pinned checkouts):

```sh
python3 -m unittest -v
/usr/bin/python3 -m unittest -v
./qd-lint check --filelist "$CALIPTRA_ROOT/src/sha256/config/sha256_ctrl.vf" --top sha256_ctrl --engine verilator --native-diagnostics --json /tmp/sha256-native.json
./qd-lint check --filelist "$CALIPTRA_ROOT/src/caliptra_prim/config/caliptra_prim_secded.vf" --top caliptra_prim_secded_22_16_enc --engine slang --native-diagnostics --json /tmp/caliptra-native.json
./qd-lint check --filelist pilots/opentitan-secded.vf --top prim_secded_22_16_enc --engine slang --native-diagnostics --json /tmp/opentitan-native.json
```

For the full matrix, run each configuration with both engines separately and
repeat without --native-diagnostics using a distinct output path. SHA256 is an
intentional diagnostic-retention case; its failures are not waived.

Local artifacts in `../evidence/lint-sarif-invocations/` retain tests, raw reports,
logs, engine binary hashes/version strings, exact argv and outcomes. They are not
published release artifacts. This gate improves failure visibility; production
qualification, complete dependency closure and broad rule coverage remain open.
