# Resolved EDAM import and Earlgrey pinmux

QD-Lint imports a bounded JSON serialization of EDAM 0.2.1 instead of reconstructing
FuseSoC dependency selection. It uses the standard library; YAML parsing remains
with the existing FuseSoC environment. Preserve the YAML's directory when emitting
JSON. The source and include ordering was checked independently against Edalize
0.6.3's `_get_fileset_files` / `_add_include_dir`, not another QD parser.

Supported: scalar matching top, ordered systemVerilogSource .sv compilation entries,
is_include_file Boolean and optional include_path, plus preserved metadata in the
hashed original configuration. The importer resolves filesystem paths; it does not
expand environment variables, rerun generators, or establish native backend parity.
Unknown fields/file types, logical_name/copyto, duplicate JSON keys, and nonempty
parameters, tool/flow options, filters, hooks or VPI are explicit input errors.
No waiver file or configuration option is silently removed. The source snapshot
also hashes declared include-only files, including files outside an overridden
include directory. In EDAM mode, the legacy audit field named filelists lists the
EDAM and those headers. It is not an engine dependency-closure claim.

## Real configuration blocker and resolution

OpenTitan `7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19` uses the top-specific core
`lowrisc:earlgrey_ip:pinmux:0.1`. Plain setup non-deterministically selected mixed
ASAP7/generic/Xilinx primitives and Darjeeling constants. Selecting a generic
library dependency alone did not activate the intended top mapping. FuseSoC 2.4.5
requires explicit --mapping options. Reuse the upstream generic and Earlgrey
mapping cores; no replacement core or application source edit is needed.

```sh
fusesoc --cores-root="$OPENTITAN_ROOT" run \
  --mapping=lowrisc:prim_generic:all:0.1 \
  --mapping=lowrisc:systems:top_earlgrey:0.1 \
  --target=default --tool=icarus --setup --build-root="$NEW_BUILD_ROOT" \
  lowrisc:earlgrey_ip:pinmux:0.1
```

The exported configuration has 224 entries: 215 compilation sources and nine
include-only files spanning four directories. It contains pinmux_reg_pkg.sv,
Earlgrey top_pkg/top_racl_pkg and generic primitive implementations. No parameters,
defines, waiver inputs or backend options are present in this selected setup.
Edalize's backend-deprecation warning remains recorded. Icarus setup only resolves
and exports this configuration; it does not establish an Icarus simulation pass.

With EDAM_YAML set to the generated .eda.yml path, use the FuseSoC environment's
existing PyYAML parser to serialize the unchanged configuration beside it:

```sh
python - "$EDAM_YAML" <<'PY'
import json, sys, yaml
from pathlib import Path
p = Path(sys.argv[1])
p.with_suffix('.json').write_text(json.dumps(yaml.safe_load(p.read_text()), indent=2)+'\n')
PY
./qd-lint check --edam-json "$EDAM_JSON" --top pinmux --engine slang \
  --slang-single-unit --audit-inputs --slang-dependencies \
  --native-diagnostics --normalize-diagnostics --json /tmp/pinmux-lint.json
python3 -m unittest -v
/usr/bin/python3 -m unittest -v
```

Set EDAM_JSON to the emitted sibling .eda.json. Observed wrapper/engine exit: 0/0;
native findings: empty; observed files: 221. Ordered sources/includes match the
native Edalize reader. Diagnostics and observed file content hashes match the
previous reviewed filelist and direct slang invocation. This is an explicitly
mapped lint configuration, not full upstream lint/DV or temporal-assertion proof.

Versions: FuseSoC 2.4.5, Edalize 0.6.3, Mako 1.3.10 under Python 3.13.15;
slang 11.0.448+e222e7dc0. Python 3.14.7 and 3.9.6 pass 45 tests, including six new
EDAM tests for order, include overrides, option rejection, malformed/duplicate
JSON, pre-engine rejection and header fingerprint changes. The existing four
pinned CI probes remain separate from this new local pinmux probe.

Raw setup warnings, exported EDAM, native/wrapper results and complete resolved
Python package versions are retained in ../evidence/pinmux-config/. That local
bundle is development evidence, not a published qualification release. Independent
Linux configuration replay, additional EDAM semantics, complete dependency closure,
waivers and production qualification remain unproven.

A fresh QD-Lint checkout passed all 45 tests. A second independent FuseSoC export
repeated the pinmux result and all 221 observed file hashes after normalizing only
the export-root prefix. This used the same host and application checkout.

## Verilator cross-check on the same resolved configuration

`ci/run_pinmux_pilot.py` now compares both wrappers with independently assembled
native commands. Edalize supplies the ordered 215 sources and four include
directories; both QD input manifests must match that ordering. The script retains
raw stdout/stderr, statuses, versions, exact commands, and elapsed times in its
output directory. It compares native Verilator SARIF findings when that installed
version advertises SARIF; otherwise it records `UNSUPPORTED` and still compares
raw diagnostics. The pilot's own pinned-fileset assertion rejects a copied EDAM
missing `pinmux_reg_pkg.sv`; the generic QD EDAM importer has no such IP rule.
The runner requires the engine to fail
when a copied EDAM omits the `pinmux` top source, and checks wrong-top rejection
before engine invocation. No OpenTitan source is changed.

Local replay on clean OpenTitan `7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`
used Python 3.13.15, FuseSoC 2.4.5, Edalize 0.6.3, PyYAML 6.0.3, slang
11.0.448+e222e7dc0 (binary SHA-256
`c38c0fc380ac4c7c48434daa9245d18ad2638b23cd47e14aa82a4a4e7a783ab4`),
and Verilator 5.050 (binary SHA-256
`fb2cc573b1055cf096c90e1efc9966fe56bdb4b265c83590cf2a49f7a0defcdf`).
Run `python ci/run_pinmux_pilot.py "$OPENTITAN_ROOT" "$NEW_EVIDENCE_DIR"`
with those tools on `PATH`; the CI entry point is `ci/build_slang_pilots.sh`.
The local output is `/tmp/qd-lint-pinmux-cross-engine-evidence5/`.

Slang and its wrapper exit 0 with no findings. Direct Verilator and its wrapper
both exit 1 with the same raw diagnostic and SARIF results: upstream
`prim_diff_decode.sv:162:28` has a `WIDTHEXPAND` warning. QD retains Verilator's
fatal-warning status; it does not waive or suppress the finding. Removing the top
source from copied EDAM yields a slang top-module error. A separate development
probe found that slang 11.0.448 accepts EDAM with `pinmux_reg_pkg.sv` omitted,
which is why the pilot checks that required source explicitly rather than treating
an empty diagnostic set as proof of configuration completeness.

The earlier Ubuntu workflow installed Verilator 5.020, which predates SARIF
support, so it checked raw diagnostics only. The pinned Verilator 5.050 source
build now requires SARIF parity and the same `WIDTHEXPAND` location. This result checks each
wrapper against its corresponding direct engine; it does not establish that slang
and Verilator implement equivalent rules. It is not a clean two-engine lint pass
or production qualification.
