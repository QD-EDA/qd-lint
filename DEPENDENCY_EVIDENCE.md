# Slang observed-file evidence

Declared include-directory inventory misses source-relative includes outside those
directories. The optional `--slang-dependencies` captures slang's documented
[`--all-deps` output](https://sv-lang.com/command-line-ref.html), one filename per
line. Spaces are preserved; this is not shell or Makefile syntax. Paths resolve
against the recorded engine working directory; symlink targets are hashed. Raw
output is retained, including base64 bytes when UTF-8 decoding fails.

This proves transport and hashing of the engine's observed file list. It does not
establish complete dependency closure, semantic correctness, or safe cache reuse.
Files are hashed after execution, without snapshot isolation. Environment, engine
binary, unobserved include-search candidates, configuration and generated inputs
can still affect results. Newline-containing filenames cannot be represented
unambiguously by this format. No incremental-result cache is introduced.

## Evidence

Python 3.14.7 and Apple Python 3.9.6 pass 33 tests: the existing 27 plus six tests
for dependency capture. Cases include source-relative headers with spaces, changed
header hashes, combined native diagnostics, two-engine isolation, required report
output, and six malformed/missing capture cases with engine exit zero. The real
slang test skips when slang is absent; CI's Verilator installation does not qualify
slang. Real-engine tests ran with slang `11.0.448+e222e7dc0`.

Pinned designs, unchanged from the previous compilation-unit evidence:
Caliptra `49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e` and OpenTitan
`7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19`.

| Configuration | Observed files | Engine / wrapper exit |
|---|---:|---|
| Caliptra SHA256, single unit, CLP_ASSERT_ON | 20 | 0 / 0 |
| Caliptra SECDED, single unit | 66 | 0 / 0 |
| OpenTitan SECDED, single unit | 37 | 0 / 0 |
| Caliptra SHA256, default separate units | 20 | 1 / 1 |

The default SHA256 macro diagnostic remains visible. Each observed path set and
engine status matched a direct slang invocation using its own native `-f` reader.
This independently checks wrapper transport, not HDL semantics. Initial macOS
wall time was 0.064–0.081 seconds per wrapper probe, not a scaling benchmark.

## Reproduction

Set CALIPTRA_ROOT and OPENTITAN_ROOT to clean checkouts of the pins above, then:

```sh
python3 -m unittest -v
/usr/bin/python3 -m unittest -v
./qd-lint check --filelist pilots/caliptra-sha256-assertions.vf \
  --top sha256_ctrl --engine slang --slang-single-unit \
  --slang-dependencies --native-diagnostics --json /tmp/sha256-deps.json
slang --lint-only --top sha256_ctrl --single-unit \
  -f pilots/caliptra-sha256-assertions.vf --all-deps /tmp/direct-deps.txt
```

Repeat with the SECDED filelists/tops from EVIDENCE.md, and the original Caliptra
SHA256 filelist without single-unit options for the negative case. Exact argv,
raw reports and local replay script are in `../evidence/lint-dependencies/`;
these are development evidence, not published qualification artifacts.

A fresh QD-Lint clone repeated all 33 tests and all four real-design probes.
Resolved dependency inventories and their hashes matched exactly across tool
workspaces. This used the same host and application checkouts; it is not a
second-host qualification.
