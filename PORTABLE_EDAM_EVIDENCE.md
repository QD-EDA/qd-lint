# Portable EDAM identity: Earlgrey pinmux

The earlier Linux/local pinmux comparison selected identical design files but
produced different raw manifest hashes because absolute export paths and
`cores[*].core_file` checkout paths differed. The archived Linux artifact does
contain `pinmux/resolved-edam.json`; comparing it with the local export shows
that only `cores` differs at the EDAM top level. The `core_file` paths lead to
different checkout locations. Both raw reports remain valid and distinct.
The [workspace evidence bundle](../evidence/lint-portable-edam-2026-09-24/REPORT.md)
retains both exported EDAM JSON files, QD reports, exact argv and raw streams.

For this probe, two clean OpenTitan checkouts at
`7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19` independently exported the
`lowrisc:earlgrey_ip:pinmux:0.1` default/Icarus EDAM with FuseSoC 2.4.5,
explicit `lowrisc:prim_generic:all:0.1` and
`lowrisc:systems:top_earlgrey:0.1` mappings. Each export had 224 EDAM file
entries and 80 core records. From the repository root, run for each export:

```sh
./qd-lint check --edam-json "$EDAM_JSON" --edam-source-root "$OPENTITAN_ROOT" \
  --top pinmux --engine slang --slang-single-unit --audit-inputs \
  --json "$REPORT_JSON"
python3 -m unittest -q
```

Both runs produced portable identity
`d303bdd63d30dea6e95a493f617a0518ead52260dc6ce5e00fe1ff35efe0e646`,
with `portable_edam_consistency: stable`, `input_consistency: stable`, and slang
exit 0 with zero warnings. Their raw input-manifest hashes differed:
`629ae73e609be633f3e6a578e17efc5bcd60125e971e8ee224f29070f9a4683c`
and `274fe6d64800f6267db378343e70c056757e5bc0ea9e9d72ec06f1363a7568df`.
The second export's 215 ordered sources and four include directories matched
Edalize 0.6.3's independent reader. The pinned pilot's earlier direct slang
and Verilator comparisons remain the engine transport oracle; this run did not
reclassify or waive Verilator's pinmux warnings.
The full `ci/run_pinmux_pilot.py` also passed on the second clean checkout with
the new identity gate and both direct-engine comparisons; its final message
remains `qualification UNKNOWN`.

Python 3.14.7 passed all 52 tests, including a deterministic EDAM mutation
between selection parsing and audit; the engine never ran on that mixed input.
Slang was 11.0.448+e222e7dc0. A timed
second-checkout run took 0.39 s wall and 118,210,560 bytes maximum resident
set size on this macOS host, including the slang invocation and JSON output.
The scope is a selected EDAM configuration and declared input inventory. It
does not prove complete preprocessing dependency closure, stable diagnostics
across engine versions, a safe incremental cache key, or production lint.
