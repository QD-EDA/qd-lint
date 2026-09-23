# Resolved EDAM import and Earlgrey pinmux

QD-Lint imports a bounded JSON serialization of EDAM 0.2.1 instead of reconstructing
FuseSoC dependency selection. It uses the standard library; YAML parsing remains
with the existing FuseSoC environment. Preserve the YAML's directory when emitting
JSON. The source and include ordering was checked independently against Edalize
0.6.3's `_get_fileset_files` / `_add_include_dir`, not another QD parser.

Supported: scalar matching top, ordered systemVerilogSource/verilogSource entries,
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
bundle is development evidence, not a published qualification release. Cross-engine
pinmux validation, independent Linux configuration replay, additional EDAM semantics,
complete dependency closure, waivers and production qualification remain unproven.
