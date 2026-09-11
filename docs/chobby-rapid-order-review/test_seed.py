#!/usr/bin/env python3
"""Exercise only the exact candidate seed block, then the existing Lua probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import probe


ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'original/packaging/launcher.sh'
CANDIDATE = ROOT / 'candidate/packaging/launcher.sh'
BEGIN = b'# Chobby caches its current lobby version list using the first rapid domain.\n'
END = b'# "potato GPU" mitigation (2026-08-04).'
OFFICIAL = probe.OFFICIAL_ORDER
SEEDED_LINE = b'RapidTagResolutionOrder = ' + OFFICIAL.encode() + b'\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def extract_block():
    original, candidate = ORIGINAL.read_bytes(), CANDIDATE.read_bytes()
    assert sha(original) == '261b5bc123d4a468a944f52de236010b4d285c307203e782f96fdc766142a133'
    assert candidate.count(BEGIN) == candidate.count(END) == 1
    start, end = candidate.index(BEGIN), candidate.index(END)
    block = candidate[start:end]
    assert candidate[:start] + candidate[end:] == original
    assert candidate[:start].endswith(b'  done < "$RES/default_springsettings.cfg"\nfi\n')
    return block


def config_value(raw):
    """Read the effective scalar using ConfigSource.cpp's trim/last-key rules.

    This is a test adapter, not an engine parser qualification. No engine runs.
    """
    value = None
    for line in raw.decode().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, rhs = line.split('=', 1)
        if key.strip() == 'RapidTagResolutionOrder':
            value = rhs.strip()
    return value


def run_block(driver, directory, number):
    env = {'PATH':'/usr/bin:/bin', 'LC_ALL':'C',
           'CFG':str(directory / 'springsettings.cfg'),
           'DIALOG_LOG':str(directory / 'dialog.log')}
    result = subprocess.run(['/bin/bash', str(driver)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = directory / f'run-{number}.stdout.log'
    stderr = directory / f'run-{number}.stderr.log'
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    return {'exit_code':result.returncode, 'stdout_sha256':sha(result.stdout),
            'stderr_sha256':sha(result.stderr),
            'continued':result.stdout == b'continued\n',
            'stdout':result.stdout.decode(), 'stderr':result.stderr.decode()}


def case(output, driver, name, before, expected, mode=None, repeat=False):
    directory = output / name
    directory.mkdir()
    cfg = directory / 'springsettings.cfg'
    if before is not None:
        cfg.write_bytes(before)
    record = {'name':name, 'passed':False, 'expected':expected,
              'before_hex':None if before is None else before.hex(), 'runs':[]}
    try:
        if mode is not None:
            cfg.chmod(mode)
        record['runs'].append(run_block(driver, directory, 1))
    finally:
        if mode is not None:
            cfg.chmod(0o600)
    try:
        after = cfg.read_bytes() if cfg.is_file() else None
        record['after_hex'] = None if after is None else after.hex()
        record['config_sha256'] = sha(after) if after is not None else None
        record['effective_order_adapter'] = config_value(after) if after is not None else None
        dialog = directory / 'dialog.log'
        record['dialog'] = dialog.read_text() if dialog.exists() else None
        run = record['runs'][0]
        if expected in ('read_failure', 'write_failure'):
            assert run['exit_code'] == 1 and not run['continued']
            assert after == before
            assert record['dialog'] and 'springsettings.cfg' in record['dialog']
            assert str(directory) not in record['dialog']
            phrase = 'could not read' if expected == 'read_failure' else 'could not save'
            assert phrase in record['dialog']
            assert run['stderr']
        else:
            assert run['exit_code'] == 0 and run['continued']
            assert record['dialog'] is None and not run['stderr']
            if expected == 'seeded':
                assert after == before + b'\n' + SEEDED_LINE
                assert config_value(after) == OFFICIAL
            else:
                assert expected == 'preserved' and after == before
            if repeat:
                record['runs'].append(run_block(driver, directory, 2))
                assert record['runs'][-1]['exit_code'] == 0
                assert record['runs'][-1]['continued']
                assert cfg.read_bytes() == after
        record['passed'] = True
    except Exception as exc:
        record['error'] = repr(exc)
    save(directory / 'result.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.label):
        parser.error('Use a simple unused label')
    if os.geteuid() == 0:
        parser.error('Real permission-denial cases must run as a normal user')
    protected = [ROOT / 'probe.py', ROOT / 'sources.json', ORIGINAL, CANDIDATE]
    for name in ('inputs', 'fixtures'):
        protected += sorted(p for p in (ROOT / name).rglob('*') if p.is_file())
    before_hashes = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in protected}
    assert before_hashes['probe.py'] == '5149e5049b143c8851abfb19572a666357512001073f3f62f0c7c6727de0b1bd'
    assert before_hashes['sources.json'] == 'b6822ba124a5b9caa51baa75127b478798183a781d7c7987db874b26be36d1fc'
    block = extract_block()
    output = ROOT / 'results' / args.label
    output.mkdir(parents=True, exist_ok=False)
    driver = output / 'exact-seed-block.sh'
    driver.write_bytes(b'''#!/bin/bash
set -uo pipefail
fail_dialog() { printf '%s\\n' "$1" >> "$DIALOG_LOG"; }
''' + block + b"printf 'continued\\n'\n")
    start = time.monotonic()
    syntax = subprocess.run(['/bin/bash', '-n', str(CANDIDATE)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={'PATH':'/usr/bin:/bin', 'LC_ALL':'C'})
    rows = [
        case(output, driver, 'missing-key-repeat', b'RotateLogFiles = 1\n', 'seeded', repeat=True),
        case(output, driver, 'no-final-newline', b'RotateLogFiles = 1', 'seeded'),
        case(output, driver, 'key-equals-custom', b'RapidTagResolutionOrder=custom.example;second.example', 'preserved'),
        case(output, driver, 'leading-space-tab', b' \tRapidTagResolutionOrder\t=\tcustom.example;second.example \n', 'preserved'),
        case(output, driver, 'comment-and-prefix', b'# RapidTagResolutionOrder = ignored.example\nRapidTagResolutionOrderExtra = ignored.example\n', 'seeded'),
        case(output, driver, 'explicit-empty', b'RapidTagResolutionOrder =\n', 'preserved'),
        case(output, driver, 'explicit-whitespace-empty', b'RapidTagResolutionOrder\t= \t\n', 'preserved'),
        case(output, driver, 'duplicate-last-custom', b'RapidTagResolutionOrder = first.example\nRapidTagResolutionOrder=custom.example\n', 'preserved'),
        case(output, driver, 'duplicate-last-empty', b'RapidTagResolutionOrder = first.example\nRapidTagResolutionOrder=\n', 'preserved'),
        case(output, driver, 'unreadable-"-path', b'RotateLogFiles = 1\n', 'read_failure', mode=0o000),
        case(output, driver, 'unwritable-"-path', b'RotateLogFiles = 1\n', 'write_failure', mode=0o400),
        case(output, driver, 'missing-cfg-boundary', None, 'read_failure'),
    ]
    linked = []
    integration = output / 'lua-integration'
    integration.mkdir()
    for row, route in ((rows[0], 'wrapper'), (rows[2], 'engine'), (rows[5], 'wrapper')):
        if not row['passed']:
            continue
        cfg = output / row['name'] / 'springsettings.cfg'
        raw = cfg.read_bytes()
        order = config_value(raw)
        result = probe.scenario(integration, row['name'], order, route=route,
                                repeat=(row['name'] == 'missing-key-repeat'))
        linked.append({'source_config':str(cfg.relative_to(ROOT)), 'config_sha256':sha(raw),
                       'order_read_from_config':order, 'consumer_result':result})
    after_hashes = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in protected}
    assert after_hashes == before_hashes
    result = {'runtime':probe.runtime_info(),
              'evidence_kind':'New execution of the portable adaptation; not a replay of private results',
              'passed':syntax.returncode == 0 and all(r['passed'] for r in rows)
                         and len(linked) == 3 and all(x['consumer_result']['passed'] for x in linked),
              'elapsed_seconds':time.monotonic()-start, 'configuration_cases':len(rows),
              'block_process_invocations':sum(len(r['runs']) for r in rows),
              'lua_integration_cases':len(linked),
              'syntax_check':{'exit_code':syntax.returncode, 'stderr':syntax.stderr.decode()},
              'original_sha256':sha(ORIGINAL.read_bytes()),
              'candidate_sha256':sha(CANDIDATE.read_bytes()),
              'exact_block_sha256':sha(block), 'driver_sha256':sha(driver.read_bytes()),
              'test_sha256':sha(Path(__file__).read_bytes()), 'protected_files_unchanged':before_hashes,
              'scope':'Exact added shell block only, followed by existing pinned Chobby consumer. No full launcher, GUI, engine, network or signals. The ordinary CFG is expected to exist after earlier initialization.',
              'config_value_adapter':'Trim, first = split, last key wins per ConfigSource.cpp; actual engine parsing and default-removal are not executed.',
              'results':rows, 'lua_integration':linked}
    save(output / 'results.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
