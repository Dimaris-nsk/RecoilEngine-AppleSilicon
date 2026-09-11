#!/usr/bin/env python3
"""Exercise the real content script with finite PRD replies; no engine or network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
INFO = (
    "[Info] tools/pr-downloader/src/Downloader/CurlWrapper.cpp:32:DumpVersion():"
    "libcurl 8.7.1 SecureTransport (LibreSSL/3.3.6)\n"
    "[Info] tools/pr-downloader/src/Downloader/CurlWrapper.cpp:81:ConfigureCertificates():"
    "CURLOPT_CAINFO is nullptr (can be overriden by PRD_SSL_CERT_FILE env variable)\n"
    "[Info] tools/pr-downloader/src/Downloader/CurlWrapper.cpp:83:ConfigureCertificates():"
    "CURLOPT_CAPATH is nullptr (can be overriden by PRD_SSL_CERT_DIR env variable)\n"
)
FOUND = (
    "[Info] tools/pr-downloader/src/Downloader/Rapid/RapidDownloader.cpp:254:ParseFD():"
    "Found 3 repos in /test/profile/rapid/host/repos.gz\n"
)


def fs_error(function, message, *, source="FileSystem", line=496):
    return f"[Error] tools/pr-downloader/src/FileSystem/{source}.cpp:{line}:{function}():{message}\n"


def http_error(code, text):
    # HttpDownloader.cpp:566 logs CURLMSG first, then CURLcode, then HTTP status.
    return (
        f"[Error] tools/pr-downloader/src/Downloader/Http/HttpDownloader.cpp:566:"
        f"processMessages():CURL error(1:{code}): {text} 0 (https://content.invalid/repos.gz), aborting\n"
    )


def sdp_error(text):
    return (
        "[Error] tools/pr-downloader/src/Downloader/Rapid/Sdp.cpp:434:downloadStream():"
        f"Curl error: {text}\n"
    )


def cases():
    eperm = (FIXTURES / "eperm.log").read_text()
    write = fs_error("Write", "write error /test/file (0): Permission denied", source="File", line=58)
    enospc = fs_error("Write", "write error /test/file (0): No space left on device", source="File", line=58)
    measure = fs_error("getMBsFree", "Error getting free disk space on /test/profile: Permission denied", line=717)
    insufficient = "[Error] tools/pr-downloader/src/pr-downloader.cpp:305:DownloadStart():Insufficient free disk space (0 MiB) on /test/profile: 4096 MiB needed\n"
    tail = "[Error] tools/pr-downloader/src/main.cpp:187:main():Error occurred while downloading: 5\n"
    optional_open = fs_error("propen", "Couldn't open /test/profile/pool/object: Permission denied", line=56)
    optional_write = fs_error("Write", "write error /test/profile/pool/object.etag (0): Permission denied", source="File", line=58)
    cleanup = fs_error("removeFile", "Couldn't delete file /test/profile/rapid/host/repos.gz.tmp: Operation not permitted")
    # name, raw PRD response, PRD exit, expected script exit/code/attempts.
    return [
        ("historical_eperm", eperm, 1, 9, "filesystem", 1),
        ("eperm_after_repos", FOUND + eperm, 1, 9, "filesystem", 1),
        ("write_denied", INFO + write, 1, 10, "unknown", 3),
        ("open_denied", INFO + fs_error("propen", "Couldn't open /test/file.tmp: Permission denied", line=56), 1, 10, "unknown", 3),
        ("rename_denied", INFO + fs_error("Rename", "Failed to rename /test/file.tmp to /test/file: Operation not permitted", line=664), 1, 10, "unknown", 3),
        ("mkdir_denied", INFO + fs_error("CreateDir", "Error creating directory /test/profile: Permission denied", line=253), 1, 10, "unknown", 3),
        ("explicit_enospc", INFO + enospc, 1, 10, "unknown", 3),
        ("disk_exit", INFO + insufficient + tail, 5, 3, "disk", 1),
        ("disk_measure_failed", INFO + measure + insufficient + tail, 5, 9, "filesystem", 1),
        ("unknown_with_ssl_info", INFO + "[Error] unknown downloader failure\n", 1, 10, "unknown", 3),
        ("bare_curl23", INFO + http_error(23, "Failed writing received data to disk/application"), 1, 10, "unknown", 3),
        ("sdp_integrity_then_curl23", INFO + "[Error] tools/pr-downloader/src/Downloader/Rapid/Sdp.cpp:287:WriteData():File is broken?!: /test/profile/pool/object\n" + sdp_error("Failed writing received data to disk/application") + tail.replace(": 5\n", ": 2\n"), 2, 10, "unknown", 3),
        ("content_unknown", INFO + FOUND + "[Error] unknown downloader failure\n", 1, 7, "content", 3),
        ("http_dns", INFO + http_error(6, "Couldn't resolve host name"), 1, 5, "network", 3),
        ("http_tls", INFO + http_error(60, "SSL peer certificate or SSH remote key was not OK"), 1, 5, "network", 3),
        ("http_tls_handshake", INFO + http_error(35, "SSL connect error"), 1, 5, "network", 3),
        ("sdp_dns", INFO + sdp_error("Couldn't resolve host name"), 1, 5, "network", 3),
        ("sdp_tls", INFO + sdp_error("SSL peer certificate or SSH remote key was not OK"), 1, 5, "network", 3),
        ("search_dns", INFO + "[Error] tools/pr-downloader/src/Downloader/Http/HttpDownloader.cpp:97:DownloadUrl():Error in curl Couldn't resolve host name (Could not resolve host: content.invalid)\n" + "[Error] tools/pr-downloader/src/Downloader/Http/HttpDownloader.cpp:220:search():Error downloading https://content.invalid/find \n", 1, 5, "network", 3),
        ("optional_open_then_dns", INFO + optional_open + http_error(6, "Couldn't resolve host name"), 1, 10, "unknown", 3),
        ("optional_write_then_dns", INFO + optional_write + http_error(6, "Couldn't resolve host name"), 1, 10, "unknown", 3),
        ("dns_then_cleanup_failure", INFO + http_error(6, "Couldn't resolve host name") + cleanup, 1, 10, "unknown", 3),
        ("optional_open_then_unknown", INFO + optional_open + "[Error] unknown downloader failure\n", 1, 10, "unknown", 3),
        ("optional_write_then_unknown", INFO + optional_write + "[Error] unknown downloader failure\n", 1, 10, "unknown", 3),
        ("repos_install_and_dns", eperm + http_error(6, "Couldn't resolve host name"), 1, 10, "unknown", 3),
        ("repos_rename_denied", INFO + fs_error("Rename", "Failed to rename /test/profile/rapid/host/repos.gz.tmp to /test/profile/rapid/host/repos.gz: Operation not permitted", line=664), 1, 9, "filesystem", 1),
        ("success_with_optional_write_error", INFO + optional_write + FOUND + "[Info] Download complete!\n", 0, 0, None, 1),
        ("tag_missing", INFO + FOUND + "[Error] Failed to find 'byar:test' for download\n", 1, 6, "tag", 1),
        ("success", INFO + FOUND + "[Info] tools/pr-downloader/src/main.cpp:185:main():Download complete!\n", 0, 0, None, 1),
    ]


def executable(path, text):
    path.write_text(text)
    path.chmod(0o700)


def run_case(script, out, case):
    name, response, prd_exit, want_exit, want_code, want_attempts = case
    run = out / name
    run.mkdir()
    (run / "profile").mkdir()
    (run / "tmp").mkdir()
    (run / "bin").mkdir()
    (run / "prd-response.log").write_text(response)
    executable(run / "prd", '#!/bin/bash\nprintf "call\\n" >> "$CASE_DIR/attempts.log"\n/bin/cat "$CASE_DIR/prd-response.log"\nexit "$PRD_EXIT"\n')
    executable(run / "bin/sleep", '#!/bin/bash\nprintf "%s\\n" "$*" >> "$CASE_DIR/sleeps.log"\n')
    # Make the existing disk preflight independent of host free space. No PRD network call exists.
    executable(run / "bin/df", '#!/bin/bash\nprintf "Filesystem 1024-blocks Used Available Capacity Mounted\\nfixture 16000000 1000 12000000 1%% /fixture\\n"\n')
    env = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME") if k in os.environ}
    env.update(PATH=str(run / "bin") + ":/usr/bin:/bin:/usr/sbin:/sbin", TMPDIR=str(run / "tmp"),
               PRD=str(run / "prd"), CASE_DIR=str(run), PRD_EXIT=str(prd_exit), LC_ALL="C")
    command = ["/bin/bash", str(script), "--writedir", str(run / "profile")]
    started = time.monotonic()
    # These finite stubs and three-attempt script finish normally. No timeout/signal cleanup.
    result = subprocess.run(command, env=env, cwd=run, capture_output=True)
    (run / "stdout.log").write_bytes(result.stdout)
    (run / "stderr.log").write_bytes(result.stderr)
    stdout, stderr = result.stdout.decode(), result.stderr.decode()
    attempts = (run / "attempts.log").read_text().splitlines()
    errors = [line for line in stdout.splitlines() if line.startswith("@E:")]
    code = errors[-1].split()[0][3:] if errors else None
    sleeps = (run / "sleeps.log").read_text().splitlines() if (run / "sleeps.log").exists() else []
    diagnostic_lines = [line for line in response.splitlines() if line and "[Progress]" not in line]
    assertions = {
        "exit": result.returncode == want_exit,
        "error_code": code == want_code,
        "attempts": len(attempts) == want_attempts,
        "full_diagnostics_preserved": all(line in stderr for line in diagnostic_lines),
        "one_error_or_success": len(errors) == (0 if want_code is None else 1),
        "completion_only_on_success": ("@DONE" in stdout) == (want_exit == 0),
        "backoff": sleeps == (["5", "10"] if want_attempts == 3 else []),
        "temporary_capture_removed": not list((run / "tmp").iterdir()),
    }
    if name == "disk_measure_failed":
        assertions["no_false_disk_full"] = "ran out of space" not in stdout
    if want_code == "filesystem":
        assertions["message_keeps_primary_reason"] = any(
            line.split("():", 1)[-1] in errors[-1]
            for line in diagnostic_lines if ":" in line and "[Error]" in line and "src/FileSystem/" in line
        )
    if want_code in ("unknown", "content"):
        assertions["no_invented_connection_cause"] = all(
            term not in "\n".join(errors).lower()
            for term in ("internet", "connection dropped", "no connection", "file failed verification")
        )
    return dict(name=name, command=command, prd_exit=prd_exit, exit=result.returncode,
                error=errors, attempts=len(attempts), sleeps=sleeps,
                seconds=time.monotonic()-started, assertions=assertions,
                passed=all(assertions.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("original", "fixed"))
    parser.add_argument("--case", action="append", help="Run only these named cases")
    parser.add_argument("--label", help="New results subdirectory; previous runs are never replaced")
    args = parser.parse_args()
    script = ROOT / ("original/packaging/download-content.sh" if args.phase == "original" else "packaging/download-content.sh")
    label = args.label or args.phase
    if not label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in label):
        parser.error("label must contain only lowercase letters, digits, '-' or '_'")
    out = ROOT / "results" / label
    out.mkdir(parents=True, exist_ok=False)
    tests = cases()
    if args.phase == "original":
        # Prove the historical wrong behavior before changing product bytes.
        name, response, prd_exit, *_ = tests[0]
        tests = [(name, response, prd_exit, 5, "network", 3)]
    if args.case:
        if not set(args.case) <= {case[0] for case in tests}:
            parser.error("unknown case name")
        tests = [case for case in tests if case[0] in args.case]
    rows = [run_case(script, out, case) for case in tests]
    result = dict(phase=args.phase, script=str(script), sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                  test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  passed=all(row["passed"] for row in rows), scenarios=rows)
    (out / "results.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
