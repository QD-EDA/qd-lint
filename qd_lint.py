#!/usr/bin/env python3
"""Small, deterministic filelist wrapper for Verilator and slang."""

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path


class InputError(Exception):
    pass


def expand(token):
    def value(match):
        name = match.group(1)
        if name not in os.environ:
            raise InputError(f"environment variable {name} is not set")
        return os.environ[name]

    return re.sub(r"\$\{([^}]+)\}", value, token)


def read_inputs(path):
    sources, incdirs, defines, filelists = [], [], [], []
    active = []

    def parse_file(file):
        file = file.resolve()
        if file in active:
            raise InputError("filelist cycle: " + " -> ".join(map(str, active + [file])))
        if not file.is_file():
            raise InputError(f"filelist not found: {file}")
        active.append(file)
        filelists.append(file)
        try:
            tokens = shlex.split(file.read_text(), comments=True)
            i = 0
            while i < len(tokens):
                token = expand(tokens[i])
                i += 1
                if token == "-f":
                    if i == len(tokens):
                        raise InputError(f"{file}: -f requires a path")
                    nested = expand(tokens[i]); i += 1
                    parse_file((file.parent / nested))
                elif token.startswith("-f") and len(token) > 2:
                    parse_file(file.parent / token[2:])
                elif token.startswith("+incdir+"):
                    incdirs.extend((file.parent / p).resolve() for p in token[8:].split("+") if p)
                elif token.startswith("+define+"):
                    defines.extend(token[8:].split("+"))
                elif token in ("-I", "-D"):
                    if i == len(tokens):
                        raise InputError(f"{file}: {token} requires a value")
                    value = expand(tokens[i]); i += 1
                    (incdirs if token == "-I" else defines).append((file.parent / value).resolve() if token == "-I" else value)
                elif token.startswith("-I") and len(token) > 2:
                    incdirs.append((file.parent / token[2:]).resolve())
                elif token.startswith("-D") and len(token) > 2:
                    defines.append(token[2:])
                elif token.startswith(("-", "+")):
                    raise InputError(f"{file}: unsupported filelist directive {token}")
                else:
                    source = (file.parent / token).resolve()
                    if source.suffix.lower() not in (".sv", ".v", ".svh", ".vh"):
                        raise InputError(f"{file}: unsupported input file {token}")
                    if not source.is_file():
                        raise InputError(f"source file not found: {source}")
                    sources.append(source)
        finally:
            active.pop()

    path = path.resolve()
    if path.suffix.lower() in (".sv", ".v", ".svh", ".vh"):
        if not path.is_file():
            raise InputError(f"source file not found: {path}")
        sources.append(path)
    else:
        parse_file(path)
    if not sources:
        raise InputError("no SystemVerilog source files")
    for incdir in incdirs:
        if not incdir.is_dir():
            raise InputError(f"include directory not found: {incdir}")
    return sources, incdirs, defines, filelists


def classify(log, status):
    if status:
        return "error"
    if re.search(r"\bwarning\b|%Warning", log, re.I):
        return "warning"
    return "clean"


def audit_inputs(sources, incdirs, defines, filelists, top, engine):
    """Inventory declared inputs; this is not an engine dependency graph."""
    paths = set(filelists + sources)

    def walk_error(error):
        raise error

    # ponytail: inventory entire include trees; use engine dependency output
    # before introducing caching or claiming preprocessing closure.
    for incdir in incdirs:
        for directory, dirs, files in os.walk(incdir, onerror=walk_error):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink():
                    raise InputError(f"input audit does not support symlink: {path}")
            paths.update(Path(directory) / name for name in files)
    inventory = []
    for path in sorted(paths):
        if not stat.S_ISREG(path.stat().st_mode):
            raise InputError(f"input audit requires a regular file: {path}")
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        inventory.append({"path": str(path), "sha256": digest.hexdigest()})
    return {"schema_version": 1, "top": top, "engine_selection": engine,
            "sources": list(map(str, sources)), "filelists": list(map(str, filelists)),
            "include_directories": list(map(str, incdirs)), "defines": list(defines),
            "files": inventory, "dependency_closure_complete": False,
            "scope": "listed files and recursive declared include-directory inventory"}


def main():
    parser = argparse.ArgumentParser(prog="qd-lint")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--filelist", required=True, type=Path, help="filelist or direct .sv/.v source")
    check.add_argument("--top", required=True)
    check.add_argument("--engine", choices=("verilator", "slang", "both"), default="both")
    check.add_argument("--json", type=Path)
    check.add_argument("--audit-inputs", action="store_true",
                       help="inventory declared include trees; not complete dependency closure")
    args = parser.parse_args()
    try:
        sources, incdirs, defines, filelists = read_inputs(args.filelist)
        manifest = audit_inputs(sources, incdirs, defines, filelists, args.top, args.engine) if args.audit_inputs else None
    except (InputError, OSError) as exc:
        print(f"qd-lint: {exc}", file=sys.stderr)
        return 2

    digest = hashlib.sha256()
    for path in filelists + sources:
        digest.update(str(path).encode() + b"\0" + path.read_bytes() + b"\0")
    engines = ("verilator", "slang") if args.engine == "both" else (args.engine,)
    results = []
    failed = False
    for engine in engines:
        executable = shutil.which(engine)
        if not executable:
            result = {"engine": engine, "executable": None, "version": None, "argv": [], "diagnostics": "", "exit_status": None, "classification": "error"}
            print(f"{engine}: executable not found", file=sys.stderr)
            results.append(result); failed = True
            continue
        version_run = subprocess.run([executable, "--version"], text=True, capture_output=True)
        version = (version_run.stdout or version_run.stderr).strip()
        argv = [executable, "--lint-only", "--top-module", args.top] if engine == "verilator" else [executable, "--lint-only", "--top", args.top]
        for incdir in incdirs:
            argv += ["-I" + str(incdir)] if engine == "verilator" else ["-I", str(incdir)]
        for define in defines:
            argv += ["-D" + define] if engine == "verilator" else ["-D", define]
        argv += list(map(str, sources))
        run = subprocess.run(argv, text=True, capture_output=True)
        log = run.stdout + run.stderr
        status = run.returncode
        classification = classify(log, status)
        result = {"engine": engine, "executable": executable, "version": version, "argv": argv, "source_snapshot_sha256": digest.hexdigest(), "diagnostics": log, "exit_status": status, "classification": classification}
        results.append(result)
        print(f"[{engine}] {version}\nargv: {shlex.join(argv)}\nsnapshot: {digest.hexdigest()}\nresult: {classification} (exit {status})")
        if log:
            print(log, end="" if log.endswith("\n") else "\n")
        failed |= classification != "clean"
    report = {"top": args.top, "source_snapshot_sha256": digest.hexdigest(), "results": results}
    if manifest is not None:
        fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        report.update(input_manifest=manifest, input_manifest_sha256=fingerprint)
        print(f"input manifest: {fingerprint} (dependency closure UNKNOWN)")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
