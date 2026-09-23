#!/usr/bin/env python3
"""Compare bounded pinned-design probes with slang's native filelist reader."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

repo = Path(__file__).resolve().parents[1]
cal, ot, out = map(lambda p: Path(p).resolve(), sys.argv[1:])
out.mkdir()  # Preserve prior evidence rather than overwriting it.
env = dict(os.environ, CALIPTRA_ROOT=str(cal), OPENTITAN_ROOT=str(ot))
commands = []


def run(name, argv):
    start = time.monotonic()
    result = subprocess.run(argv, cwd=repo, env=env, capture_output=True, timeout=120)
    (out/(name+'.stdout')).write_bytes(result.stdout)
    (out/(name+'.stderr')).write_bytes(result.stderr)
    commands.append(dict(name=name, argv=argv, exit_status=result.returncode,
                         seconds=time.monotonic()-start))
    (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return result


for root, pin in ((cal, '49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e'),
                  (ot, '7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19')):
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==pin
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
slang = shutil.which('slang')
assert slang, 'slang is mandatory in this pilot'
(out/'engine.json').write_text(json.dumps({'executable':slang,
    'sha256':hashlib.sha256(Path(slang).resolve().read_bytes()).hexdigest()},indent=2)+'\n')
assert run('version',[slang,'--version']).returncode==0
cases = [
    ('sha256-assert','pilots/caliptra-sha256-assertions.vf','sha256_ctrl',True,0,20),
    ('caliptra-secded',str(cal/'src/caliptra_prim/config/caliptra_prim_secded.vf'),
     'caliptra_prim_secded_22_16_enc',True,0,66),
    ('opentitan-secded','pilots/opentitan-secded.vf','prim_secded_22_16_enc',True,0,37),
    ('sha256-default',str(cal/'src/sha256/config/sha256_ctrl.vf'),'sha256_ctrl',False,1,20)]
for name, filelist, top, single, expected, count in cases:
    report = out/(name+'.json')
    wrapper = run(name,[sys.executable,str(repo/'qd_lint.py'),'check','--filelist',filelist,
        '--top',top,'--engine','slang','--slang-dependencies','--native-diagnostics',
        '--json',str(report)]+(['--slang-single-unit'] if single else []))
    assert wrapper.returncode==expected, name
    result = json.loads(report.read_text())['results'][0]
    assert result['dependencies']['status']=='captured', name
    assert result['native_diagnostics']['status']=='captured', name
    deps, native = out/(name+'.deps'), out/(name+'-native.json')
    direct = run(name+'-direct',[slang,'--lint-only','--top',top,'-f',filelist,
        '--all-deps',str(deps),'--diag-json',str(native)]+(['--single-unit'] if single else []))
    assert direct.returncode==result['exit_status']==expected, name
    assert json.loads(native.read_text())==result['native_diagnostics']['data'], name
    paths = {str((repo/p).resolve()) for p in deps.read_text().splitlines()}
    assert len(paths)==count, name
    assert paths=={f['path'] for f in result['dependencies']['files']}, name
    if expected:
        assert 'CALIPTRA_ASSERT_KNOWN' in result['diagnostics'], name
pre = run('assertion-preprocess',[slang,'-E','--single-unit','-f','pilots/caliptra-sha256-assertions.vf'])
assert pre.returncode==0 and b'ERR_HWIF_IN: assert property' in pre.stdout
for root in (cal, ot):
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
print('PASS: four pinned configurations match native slang; qualification UNKNOWN')
