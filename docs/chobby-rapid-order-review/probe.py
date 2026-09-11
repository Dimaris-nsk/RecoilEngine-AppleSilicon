#!/usr/bin/env python3
"""Run pinned Chobby backup/restore code against finite local-file fixtures.

No launcher, engine, GUI, network, child processes, signals, or installation.
The configuration input is supplied directly; launcher seeding is not tested.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / 'sources.json').read_text())
import lupa
import lupa.lua51 as lua51

LuaRuntime = lua51.LuaRuntime
assert lua51.LUA_VERSION == (5, 1), 'This probe requires the Lua 5.1 Lupa module'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def runtime_info():
    # Record the implementation actually imported through the caller's environment.
    # Do not disclose local interpreter or module installation paths.
    module = Path(lua51.__file__)
    return {'python_version':sys.version, 'lupa_version':lupa.__version__,
            'lua_version':list(lua51.LUA_VERSION), 'module_name':module.name,
            'module_sha256':sha(module.read_bytes())}


def inputs():
    for item in SOURCES['extracted_files']:
        raw = (ROOT / item['path']).read_bytes()
        assert sha(raw) == item['sha256'], item['path']
        assert hashlib.md5(raw).hexdigest() == item['archive_md5'], item['path']
    main = (ROOT / 'inputs/luamenu/configs/gameconfig/byar/mainconfig.lua').read_bytes()
    path_block = b''.join(main.splitlines(keepends=True)[147:154])
    assert path_block.startswith(b'local chobbyRepoDomain = "repos.springrts.com"')
    assert path_block.rstrip().endswith(b'"/byar-chobby/versions.gz"')
    config = json.loads((ROOT / 'inputs/dist_cfg/config.json').read_bytes())
    settings = [s['launch']['springsettings']['RapidTagResolutionOrder']
                for s in config['setups'] if s['package']['id'] in ('manual-linux', 'manual-win')]
    assert len(settings) == 2 and settings[0] == settings[1]
    return path_block, settings[0]


PATH_BLOCK, OFFICIAL_ORDER = inputs()
ORIGINAL = (ROOT / 'fixtures/versions.gz').read_bytes()
assert sha(ORIGINAL) == SOURCES['versions_fixture']['sha256']
OLD_ROW = SOURCES['versions_fixture']['current_tag'].encode()
NEW_ROW = b'byar-chobby:test,11111111111111111111111111111111,,BYAR Chobby controlled-not-downloaded'
plain = gzip.decompress(ORIGINAL)
assert plain.splitlines().count(OLD_ROW) == 1
changed_plain = plain.replace(OLD_ROW, NEW_ROW)
assert NEW_ROW in changed_plain.splitlines() and OLD_ROW not in changed_plain.splitlines()
CHANGED = gzip.compress(changed_plain, mtime=0)
assert CHANGED != ORIGINAL


class Chobby:
    def __init__(self, directory, order, record):
        self.directory = directory.resolve()
        self.record = record
        self.lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
        glob = self.lua.globals()
        glob.order_input = None if order is None else order.encode()
        glob.record_log = lambda data: record['lua_log'].append(data.decode('utf-8'))
        glob.checked_path = self.checked_path
        glob.read_file = self.read_file
        self.lua.execute(b'''
            Spring = {
              GetConfigString = function(name)
                assert(name == 'RapidTagResolutionOrder')
                return order_input or ''
              end,
              Echo = function(...)
                local args = {...}
                for i = 1, #args do args[i] = tostring(args[i]) end
                record_log(table.concat(args, '\t'))
              end
            }
            local raw_open = io.open
            io.open = function(path, mode)
              assert(mode == 'wb', 'unexpected file operation')
              return raw_open(checked_path(path), mode)
            end
            io.popen = nil
            os = nil
            package = nil
            VFS = {
              LoadFile = read_file,
              Include = function(path)
                assert(path == 'LuaMenu/widgets/chobby/headers/exports.lua')
                return {}
              end,
              RAW_FIRST = 1,
              HasArchive = function(name)
                assert(name == 'controlled-game-download')
                return true
              end,
              ScanAllDirs = function() error('unexpected archive scan') end
            }
            LUA_DIRNAME = 'LuaMenu/'
            widget = {}
        ''')
        self.lua.execute((ROOT / 'inputs/luamenu/utils.lua').read_bytes())
        game_config = self.lua.execute(b'local externalFuncAndData = {}\n' + PATH_BLOCK +
                                       b'\nreturn externalFuncAndData\n')
        self.selected_path = game_config[b'SaveLobbyVersionGZPath'].decode()
        glob.game_config = game_config
        self.lua.execute(b'''
            WG = {
              Chobby = {Configuration = {gameConfig = game_config}},
              Delay = function(fn, delay)
                assert(delay == 1 and delayed == nil)
                delayed = fn
              end
            }
        ''')
        self.lua.execute((ROOT / 'inputs/luamenu/widgets/api_download_handler.lua').read_bytes())

    def checked_path(self, relative):
        relative = relative.decode('utf-8')
        path = (self.directory / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(self.directory):
            raise AssertionError('Path escaped this test case')
        if not relative.startswith('rapid/'):
            raise AssertionError('Unexpected path outside rapid')
        return str(path).encode()

    def read_file(self, relative):
        path = Path(self.checked_path(relative).decode())
        data = path.read_bytes() if path.is_file() else None
        self.record['vfs_reads'].append({'path':relative.decode(), 'found':data is not None,
                                         'sha256':sha(data) if data is not None else None})
        return data

    def initialize(self):
        self.lua.execute(b'''
            widget:Initialize()
            assert(type(delayed) == 'function')
            local fn = delayed
            delayed = nil
            fn()
        ''')

    def complete(self, route):
        self.lua.execute(b"WG.DownloadHandler.QueueDownload('controlled-game-download', 'game', 1)")
        if route == 'wrapper':
            self.lua.execute(b"WG.DownloadWrapperInterface.DownloadFinished('controlled-game-download', 'RAPID', true, false)")
        else:
            assert route == 'engine'
            self.lua.execute(b'''
                widget:DownloadQueued(123, 'controlled-game-download', 'game')
                widget:DownloadFinished(123)
            ''')
        assert self.lua.eval(b'#(WG.DownloadHandler.GetDownloadQueue())') == 0


def snapshot(directory):
    result = {}
    for path in sorted(directory.glob('rapid/**/*')):
        if path.is_file():
            data = path.read_bytes()
            rows = gzip.decompress(data).splitlines()
            result[str(path.relative_to(directory))] = {
                'sha256':sha(data), 'bytes':len(data),
                'current_tag':[row.decode() for row in rows if row.startswith(b'byar-chobby:test,')]
            }
    return result


def scenario(output, name, order, route='wrapper', repeat=False, fresh_during=False):
    directory = output / name
    directory.mkdir()
    # Explicit custom order uses a real fixture under that domain; no default
    # domain is silently substituted in the configuration under test.
    domain = order.split(';')[0] if order else OFFICIAL_ORDER.split(';')[0]
    target = directory / 'rapid' / domain / 'byar-chobby/versions.gz'
    target.parent.mkdir(parents=True)
    target.write_bytes(ORIGINAL)
    cache = target.with_name(target.name + '_cache.gz')
    record = {'name':name, 'input_order':order, 'completion_route':route,
              'passed':False, 'lua_log':[], 'vfs_reads':[], 'stages':{}}
    try:
        vm = Chobby(directory, order, record)
        record['selected_path'] = vm.selected_path
        vm.initialize()
        record['stages']['initialized'] = snapshot(directory)
        if order:
            assert vm.selected_path == str(target.relative_to(directory))
            assert cache.read_bytes() == ORIGINAL
        else:
            assert vm.selected_path == 'rapid/repos.springrts.com/byar-chobby/versions.gz'
            assert not cache.exists()
            assert any('Failed to load versions.gz' in line for line in record['lua_log'])
        target.write_bytes(CHANGED)
        record['stages']['controlled_update'] = snapshot(directory)
        if repeat:
            vm.initialize()
            assert cache.read_bytes() == ORIGINAL
            assert any('already cached' in line for line in record['lua_log'])
            record['stages']['same_instance_reinitialized'] = snapshot(directory)
        if fresh_during:
            vm = Chobby(directory, order, record)
            vm.initialize()
            assert cache.read_bytes() == CHANGED
            record['stages']['fresh_instance_during_update'] = snapshot(directory)
        vm.complete(route)
        record['stages']['completed'] = snapshot(directory)
        expected = CHANGED if not order or fresh_during else ORIGINAL
        assert target.read_bytes() == expected
        if fresh_during:
            record['outcome'] = 'Existing limitation: a new Lua instance caches the currently changed list; this does not provide recovery across interruption/restart.'
        elif not order:
            record['outcome'] = 'Original defect reproduced: no backup; changed lobby tag remains after completion.'
        else:
            record['outcome'] = 'Original list and installed lobby tag restored byte-for-byte by unchanged Chobby code.'
            # A new initialization after a completed update is a separate state
            # from a restart while the changed list has not yet been restored.
            vm = Chobby(directory, order, record)
            vm.initialize()
            assert target.read_bytes() == ORIGINAL and cache.read_bytes() == ORIGINAL
            record['stages']['fresh_instance_after_completion'] = snapshot(directory)
        record['passed'] = True
    except Exception as exc:
        record['error'] = repr(exc)
        record['stages']['failure'] = snapshot(directory)
    finally:
        save(directory / 'result.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.label):
        parser.error('Use a simple unused result label')
    output = ROOT / 'results' / args.label
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    rows = [
        scenario(output, 'original-missing-setting', None),
        scenario(output, 'original-explicit-empty', ''),
        scenario(output, 'official-wrapper-reinitialize', OFFICIAL_ORDER, repeat=True),
        scenario(output, 'official-engine-completion', OFFICIAL_ORDER, route='engine'),
        scenario(output, 'explicit-custom-order', 'custom.example;repos-cdn.beyondallreason.dev'),
        scenario(output, 'fresh-instance-during-update-limit', OFFICIAL_ORDER, fresh_during=True),
    ]
    result = {'passed':all(r['passed'] for r in rows), 'scenarios':len(rows),
              'elapsed_seconds':time.monotonic()-start, 'runtime':runtime_info(),
              'evidence_kind':'New execution of the portable adaptation; not a replay of private results',
              'probe_sha256':sha(Path(__file__).read_bytes()),
              'sources_sha256':sha((ROOT / 'sources.json').read_bytes()),
              'path_block_lines':[148,154], 'path_block_sha256':sha(PATH_BLOCK),
              'official_order_from_included_config':OFFICIAL_ORDER,
              'original_fixture_sha256':sha(ORIGINAL), 'changed_fixture_sha256':sha(CHANGED),
              'scope':'Real extracted Chobby backup/restore functions and native Lua file writes; engine VFS and configuration inputs controlled. No product seeding implementation, game, network, signals, or child processes.',
              'results':rows}
    save(output / 'results.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
