# qd-lint

A small SystemVerilog lint runner for reproducible local checks. It wraps the
installed [Verilator](https://verilator.org/) and
[slang](https://github.com/MikePopoloski/slang) executables; it is not an
ASIC signoff replacement for SpyGlass or AscentLint.

```sh
./qd-lint check --filelist design.vf --top top_module --engine both --json lint.json
./qd-lint check --filelist design.sv --top design --engine verilator
python3 -m unittest -v
```

Filelists support source files, nested `-f`, `+incdir+`, `-I`, `+define+`,
`-D`, and `${VARIABLE}` expansion. Relative paths in a list are relative to
that list. Unsupported directives, missing paths, unset variables, and
recursive filelists fail explicitly. Files are passed as argv entries without
shell evaluation.

The JSON report and terminal output include each tool version, exact argv,
SHA-256 snapshot of filelists and source files, raw diagnostics, exit status,
and `clean`, `warning`, or `error` classification. Warnings remain visible
and make the command nonzero; a zero tool status with warnings is not a clean
pass. The source snapshot does not include files discovered indirectly by
preprocessor includes.

## Scoped probe

Caliptra RTL v2.1.2 `caliptra_prim_secded.vf`, top
`caliptra_prim_secded_22_16_enc`, passed with both installed engines (zero
warnings). This checks the listed SECDED RTL hierarchy only; it does not run
Caliptra's unit-test/DV infrastructure or establish signoff coverage.
