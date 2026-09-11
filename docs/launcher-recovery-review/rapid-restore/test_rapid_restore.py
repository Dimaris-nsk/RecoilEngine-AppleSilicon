#!/usr/bin/env python3
"""Run only the exact rapid block and outcome branches, never the launcher.

Real private filesystem trees; narrowly failing cp/rm/mv wrappers. The omitted
downloader is a deterministic tree replacement, and the game is only a marker.
No processes are signalled. No network or graphical application is started.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OLD = {"host/repos.gz": b"old repositories\n", "host/versions.gz": b"old versions\n"}
NEW = {"host/repos.gz": b"new repositories\n", "host/versions.gz": b"new versions\n"}
PARTIAL = {"host/repos.gz": b"unfinished update\n"}
READY = "rapid.pre-update.ready"
STAGE = "rapid.pre-update.tmp"
LEGACY = "rapid.pre-update"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(path):
    if not path.exists() and not path.is_symlink():
        return None
    result = {}
    for item in sorted([path, *path.rglob("*")]):
        name = str(item.relative_to(path))
        if item.is_symlink():
            result[name] = {"link": os.readlink(item)}
        elif item.is_file():
            result[name] = {"sha256": sha(item.read_bytes()), "size": item.stat().st_size}
        elif item.is_dir():
            result[name] = {"directory": True}
    return result


def put(path, contents):
    path.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        dst = path / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)


def file_hashes(path):
    return {str(p.relative_to(path)): sha(p.read_bytes()) for p in path.rglob("*") if p.is_file()}


def hashes(contents):
    return {k: sha(v) for k, v in contents.items()}


WRAPPER = r'''#!/usr/bin/env python3
import json, os, pathlib, shutil, subprocess, sys
command = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
profile = pathlib.Path(os.environ['WRITEDIR'])
phase = os.environ['TEST_PHASE']
fault = json.loads(os.environ['TEST_FAULT'])
matches = (fault.get('command') == command and fault.get('phase') == phase
           and args[-len(fault['tail']):] == [str(profile / x) for x in fault['tail']]) if fault else False
entry = {'command': command, 'args': args, 'phase': phase, 'injected': matches}
if matches:
    if fault.get('partial'):
        if command == 'cp':
            src, dst = map(pathlib.Path, args[-2:])
            dst.mkdir(parents=True, exist_ok=True)
            one = sorted(p for p in src.rglob('*') if p.is_file())[0]
            target = dst / one.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(one, target)
        elif command == 'rm':
            target = pathlib.Path(args[-1])
            files = sorted(p for p in target.rglob('*') if p.is_file())
            if files:
                files[0].unlink()
    entry['exit'] = 1
    print('INJECTED ' + command + ': Operation not permitted: ' + args[-1], file=sys.stderr)
else:
    entry['exit'] = subprocess.run(['/bin/' + command, *args]).returncode
with open(os.environ['TEST_OPERATIONS'], 'a') as f:
    f.write(json.dumps(entry) + '\n')
sys.exit(entry['exit'])
'''

PRELUDE = r'''#!/bin/bash
set -uo pipefail
LOG="$WRITEDIR/first-run-download.log"
DONE_SENTINEL="$WRITEDIR/.lobby-installed"
CONTENT_SIG=new-content-signature
HPID=""; FIFODIR=""; FIFO=""
SKIPPED=0; RC=0; ERR_CODE=""; ERR_TEXT=""
FIRST_RUN=0
[ -f "$DONE_SENTINEL" ] || FIRST_RUN=1
: > "$LOG"
fail_dialog() { printf '%s\n' "$1" >> "$TEST_DIALOG"; }
# Builtins as well as PATH tools must not signal anything, even by mistake.
kill() { printf 'FORBIDDEN kill\n' >> "$TEST_BOUNDARIES"; exit 99; }
pkill() { printf 'FORBIDDEN pkill\n' >> "$TEST_BOUNDARIES"; exit 99; }
export TEST_PHASE=startup
'''

FAKE_DOWNLOAD = r'''
printf 'prepare-complete\n' >> "$TEST_BOUNDARIES"
if [ "$TEST_PREPARE_ONLY" = 1 ]; then exit 0; fi
printf 'downloader-called\n' >> "$TEST_BOUNDARIES"
/bin/rm -rf "$WRITEDIR/rapid"
/bin/cp -R "$TEST_DOWNLOAD_TREE" "$WRITEDIR/rapid"
export TEST_PHASE=outcome
case "$TEST_OUTCOME" in
  success) ;;
  skip) SKIPPED=1; RC=1 ;;
  failure) RC=1; ERR_CODE=unknown; ERR_TEXT="TEST download failure" ;;
  *) exit 98 ;;
esac
'''


def extracted(source):
    text = source.read_text()
    cleanup = text[text.index("  cleanup_fifo() {"):text.index("\n\n  # ---- update integrity snapshot")]
    integrity = text[text.index("  # ---- update integrity snapshot"):text.index("  # Run the downloader in the BACKGROUND")]
    start = text.index('  if [ "$SKIPPED" = "1" ]; then', text.index("  # classified failure"))
    outcomes = text[start:text.index("  trap - PIPE", start)]
    script = PRELUDE + cleanup + "\n" + integrity + FAKE_DOWNLOAD + outcomes + '\nprintf "game-allowed\\n" >> "$TEST_BOUNDARIES"\n'
    # Full launcher sections that could start processes must be absent.
    assert "poll_downloader()" not in script and "wrapper-bridge --write-dir" not in script
    assert '"$HERE/spring"' not in script and "osascript" not in script
    return script, {"source_sha256": sha(source.read_bytes()), "integrity_sha256": sha(integrity.encode()),
                    "outcome_sha256": sha(outcomes.encode()), "extracted_sha256": sha(script.encode())}


class Case:
    def __init__(self, suite, name, source, initial=OLD, installed=True):
        self.root = suite / name
        self.root.mkdir()
        self.profile = self.root / "profile"
        self.profile.mkdir()
        if initial is not None:
            put(self.profile / "rapid", initial)
        if installed:
            (self.profile / ".lobby-installed").write_text("old-content-signature\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        wrapper = self.bin / "filesystem-operation"
        wrapper.write_text(WRAPPER)
        wrapper.chmod(0o755)
        for command in ("cp", "rm", "mv"):
            (self.bin / command).symlink_to(wrapper.name)
        self.here = self.root / "MacOS"
        self.here.mkdir()
        dialog = self.here / "error-dialog"
        dialog.write_text('#!/bin/bash\nprintf "%s\\n" "$@" >> "$TEST_DIALOG"\n')
        dialog.chmod(0o755)
        self.script, self.provenance = extracted(source)
        (self.root / "extracted-content.sh").write_text(self.script)
        self.runs = []

    def run(self, outcome="failure", fault=None, prepare_only=False, download=None, fallback=False):
        number = len(self.runs) + 1
        run = self.root / f"run-{number}"
        run.mkdir()
        for path in ("operations.jsonl", "boundaries.txt", "dialog.txt"):
            (run / path).touch()
        data = run / "download-tree"
        put(data, (NEW if outcome == "success" else PARTIAL) if download is None else download)
        if fallback:
            (self.here / "error-dialog").chmod(0o644)
        env = dict(os.environ, PATH=str(self.bin) + ":" + os.environ["PATH"],
                   WRITEDIR=str(self.profile), HERE=str(self.here), TEST_OUTCOME=outcome,
                   TEST_PREPARE_ONLY=str(int(prepare_only)), TEST_DOWNLOAD_TREE=str(data),
                   TEST_FAULT=json.dumps(fault), TEST_OPERATIONS=str(run / "operations.jsonl"),
                   TEST_BOUNDARIES=str(run / "boundaries.txt"), TEST_DIALOG=str(run / "dialog.txt"))
        before = manifest(self.profile)
        p = subprocess.run(["/bin/bash", str(self.root / "extracted-content.sh")], env=env,
                           text=True, capture_output=True)
        (run / "stdout.txt").write_text(p.stdout)
        (run / "stderr.txt").write_text(p.stderr)
        log = (self.profile / "first-run-download.log").read_text()
        (run / "launcher.log").write_text(log)
        result = {"exit": p.returncode, "outcome": outcome, "fault": fault, "prepare_only": prepare_only,
                  "log": log, "dialog": (run / "dialog.txt").read_text(),
                  "boundaries": (run / "boundaries.txt").read_text().splitlines(),
                  "operations": [json.loads(x) for x in (run / "operations.jsonl").read_text().splitlines()],
                  "before": before, "after": manifest(self.profile)}
        (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        self.runs.append(result)
        assert not any(x.startswith("FORBIDDEN") for x in result["boundaries"])
        return result

    def equal(self, name, content):
        assert (self.profile / name).is_dir(), (self.root.name, name)
        assert file_hashes(self.profile / name) == hashes(content), (self.root.name, name)

    def absent(self, name):
        assert not (self.profile / name).exists(), (self.root.name, name)


def fault(command, *tail, phase="startup", partial=False):
    return {"command": command, "tail": list(tail), "phase": phase, "partial": partial}


def stopped(result, *, downloader=False):
    assert result["exit"] == 1, result
    assert "game-allowed" not in result["boundaries"]
    assert ("downloader-called" in result["boundaries"]) == downloader
    assert "rapid metadata restored" not in result["log"]
    assert result["dialog"], result
    if result["fault"]:
        assert "INJECTED" in result["log"] and "INJECTED" in result["dialog"]


def original_cases(suite, source):
    cases = []
    c = Case(suite, "rm-failure-false-success", source)
    cases.append(c)
    put(c.profile / LEGACY, OLD)
    r = c.run(fault=fault("rm", "rapid"), prepare_only=True)
    assert r["exit"] == 0 and "rapid metadata restored" in r["log"]
    assert any(op["command"] == "mv" for op in r["operations"])
    assert (c.profile / "rapid" / LEGACY).is_dir()

    c = Case(suite, "partial-copy-used-as-backup", source)
    cases.append(c)
    r = c.run(fault=fault("cp", "rapid", LEGACY, partial=True))
    assert r["exit"] == 0 and "game-allowed" in r["boundaries"]
    assert file_hashes(c.profile / "rapid") != hashes(OLD)
    assert "rapid metadata restored" in r["log"]

    c = Case(suite, "failed-cleanup-rolls-back-success", source)
    cases.append(c)
    r = c.run("success", fault=fault("rm", LEGACY, phase="outcome"))
    assert r["exit"] == 0 and "game-allowed" in r["boundaries"]
    c.equal("rapid", NEW)
    c.equal(LEGACY, OLD)
    r = c.run(prepare_only=True)
    assert r["exit"] == 0
    c.equal("rapid", OLD)
    return cases


def fixed_cases(suite, source):
    cases = []

    def case(name, initial=OLD, installed=True):
        c = Case(suite, name, source, initial, installed)
        cases.append(c)
        return c

    def retry(c, expected=OLD):
        r = c.run(prepare_only=True)
        assert r["exit"] == 0 and r["boundaries"] == ["prepare-complete"]
        c.equal("rapid", expected)
        c.equal(READY, expected)
        c.absent(STAGE)
        return r

    # Complete snapshots survive either a total or partial restore deletion.
    for partial in (False, True):
        c = case("restore-rm-" + ("partial" if partial else "refused"), initial=NEW)
        put(c.profile / READY, OLD)
        r = c.run(fault=fault("rm", "rapid", partial=partial))
        stopped(r)
        c.equal(READY, OLD)
        if not partial:
            c.equal("rapid", NEW)
        else:
            assert len(file_hashes(c.profile / "rapid")) == 1
        assert not any(x["command"] == "mv" for x in r["operations"])
        retry(c)

    c = case("restore-mv-refused", initial=PARTIAL)
    put(c.profile / READY, OLD)
    r = c.run(fault=fault("mv", READY, "rapid"))
    stopped(r)
    c.equal(READY, OLD)
    c.absent("rapid")
    retry(c)

    for partial in (False, True):
        c = case("snapshot-cp-" + ("partial" if partial else "refused"))
        r = c.run(fault=fault("cp", "rapid", STAGE, partial=partial))
        stopped(r)
        c.equal("rapid", OLD)
        c.absent(READY)
        if partial:
            assert len(file_hashes(c.profile / STAGE)) == 1
        retry(c)

    c = case("snapshot-publish-refused")
    r = c.run(fault=fault("mv", STAGE, READY))
    stopped(r)
    c.equal("rapid", OLD)
    c.equal(STAGE, OLD)
    c.absent(READY)
    retry(c)

    c = case("old-stage-cleanup-refused")
    put(c.profile / STAGE, PARTIAL)
    r = c.run(fault=fault("rm", STAGE))
    stopped(r)
    c.equal("rapid", OLD)
    c.equal(STAGE, PARTIAL)
    c.absent(READY)
    retry(c)

    for installed in (False, True):
        c = case("commit-rename-refused-" + str(installed), installed=installed)
        r = c.run("success", fault=fault("mv", READY, STAGE, phase="outcome"))
        stopped(r, downloader=True)
        c.equal("rapid", NEW)
        c.equal(READY, OLD)
        if installed:
            assert (c.profile / ".lobby-installed").read_text() == "old-content-signature\n"
        else:
            c.absent(".lobby-installed")
        retry(c)

    for partial in (False, True):
        c = case("retired-cleanup-" + ("partial" if partial else "refused"))
        r = c.run("success", fault=fault("rm", STAGE, phase="outcome", partial=partial))
        assert r["exit"] == 0 and "game-allowed" in r["boundaries"]
        assert "obsolete backup cleanup failed: INJECTED" in r["log"]
        assert not r["dialog"]
        c.equal("rapid", NEW)
        c.absent(READY)
        assert (c.profile / ".lobby-installed").read_text() == "new-content-signature\n"
        assert file_hashes(c.profile / STAGE)
        r = retry(c, NEW)
        assert not any(x["command"] == "mv" and x["args"][-2] == str(c.profile / READY)
                       for x in r["operations"]), "retired backup was restored"

    # Every outcome caller must halt when rollback fails, including first run.
    for outcome, installed in (("skip", True), ("failure", True), ("failure", False)):
        name = f"caller-{outcome}-installed-{installed}"
        c = case(name, initial=OLD if installed else None, installed=installed)
        r = c.run(outcome, fault=fault("mv", READY, "rapid", phase="outcome"))
        stopped(r, downloader=True)
        c.equal(READY, OLD if installed else {})
        c.absent("rapid")
        if not installed:
            c.absent(".lobby-installed")
        retry(c, OLD if installed else {})

    # Ordinary first install, successful update, skip, and offline fallback.
    for outcome, installed in (("success", False), ("success", True),
                               ("skip", True), ("failure", True), ("failure", False)):
        c = case(f"normal-{outcome}-installed-{installed}",
                 initial=OLD if installed else None, installed=installed)
        r = c.run(outcome)
        may_play = installed or outcome == "success"
        assert r["exit"] == (0 if may_play else 1)
        assert ("game-allowed" in r["boundaries"]) == may_play
        expected = NEW if outcome == "success" else (OLD if installed else {})
        c.equal("rapid", expected)
        c.absent(READY)
        c.absent(STAGE)
        if outcome == "success":
            assert (c.profile / ".lobby-installed").read_text() == "new-content-signature\n"
        elif not installed:
            c.absent(".lobby-installed")
            assert "TEST download failure" in r["dialog"]
        retry(c, expected)

    # Model interrupted states by making actual files, never sending signals.
    for name, current, ready, stage, expected in (
        ("interrupted-copy", OLD, None, PARTIAL, OLD),
        ("copy-finished-not-published", OLD, None, OLD, OLD),
        ("ready-before-download", OLD, OLD, None, OLD),
        ("interrupted-download", PARTIAL, OLD, None, OLD),
        ("interrupted-restore-after-rm", None, OLD, None, OLD),
        ("interrupted-after-retirement", NEW, None, OLD, NEW),
    ):
        c = case(name, initial=current)
        if ready is not None:
            put(c.profile / READY, ready)
        if stage is not None:
            put(c.profile / STAGE, stage)
        retry(c, expected)

    for label, legacy in (("empty", {}), ("partial", PARTIAL), ("complete-looking", OLD)):
        c = case("legacy-" + label)
        put(c.profile / LEGACY, legacy)
        for _ in range(2):
            r = c.run()
            stopped(r)
            assert "Its completeness is unknown" in r["dialog"]
            assert r["operations"] == []
            c.equal("rapid", OLD)
            c.equal(LEGACY, legacy)
            c.absent(READY)

    c = case("fallback-dialog")
    put(c.profile / READY, OLD)
    r = c.run(fault=fault("rm", "rapid"), fallback=True)
    stopped(r)
    assert "Details:" in r["dialog"]

    c = case("paths with spaces")
    r = c.run("success")
    assert r["exit"] == 0 and "game-allowed" in r["boundaries"]
    c.equal("rapid", NEW)
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("version", choices=("original", "fixed"))
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    source = ROOT / ("original/packaging/launcher.sh" if args.version == "original" else "packaging/launcher.sh")
    suite = ROOT / "results" / args.label
    suite.mkdir(parents=True, exist_ok=False)
    (suite / "test_rapid_restore.py").write_bytes(Path(__file__).read_bytes())
    cases = original_cases(suite, source) if args.version == "original" else fixed_cases(suite, source)
    result = {"passed": True, "version": args.version, "source_sha256": sha(source.read_bytes()),
              "test_sha256": sha(Path(__file__).read_bytes()), "cases": len(cases),
              "runs": sum(len(c.runs) for c in cases),
              "scenarios": [{"name": c.root.name, "provenance": c.provenance, "runs": c.runs} for c in cases]}
    (suite / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "scenarios"}, indent=2))


if __name__ == "__main__":
    main()
