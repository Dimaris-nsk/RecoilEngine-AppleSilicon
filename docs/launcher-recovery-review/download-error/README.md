# Content download error classification

The launcher previously treated failure to replace `rapid/<host>/repos.gz`
as a network outage and retried three times. The candidate reports the
filesystem diagnostic after one attempt. Actual CURL DNS/TLS failures remain
network errors; ambiguous or mixed failures retain neutral diagnostics and
normal retries. Optional cache errors do not turn successful downloads into
failures. Only `packaging/download-content.sh` changes.

Base: [Vandomas/RecoilEngine-AppleSilicon, 562fe461](https://github.com/Vandomas/RecoilEngine-AppleSilicon/tree/562fe461f8b045f863089815edac7f2d6559e178).
[manifest.json](manifest.json) records exact inputs, original result hashes
and public-copy hashes. [sources.json](sources.json) provides supporting public
source URLs; its `references/*` entries are a source catalog, not runtime
requirements. [curl-message-check.json](curl-message-check.json) records actual
libcurl strings read without network calls.

## Repeat

On macOS with Python 3 and standard system utilities, keep this layout and
run from its root using unused result labels:

```sh
python3 test_download_errors.py original --label recipient-original
python3 test_download_errors.py fixed --label recipient-fixed
```

The real script uses finite PRD replies and controlled disk preflight/retry
delays. No extra Python packages, PRD binary, game data, GUI, network or process
signals are used. The absent `content_tags` deliberately selects the built-in
list. The [EPERM fixture](fixtures/eperm.log) comes from a saved real log
(SHA256 `d915a3451fb3f2457d58581e03ded2be1d102306fcbda2c1663d6febdf3f5ef3`,
lines 7–14), with only its private profile root replaced by `/test/profile`.

## Recorded results from this portable package

Both runs used the included test, SHA256
`3559a829844365e514128c0a344745293e87b5256834f64d5fa61f4b9547a79c`.
[Original](results/portable-original/results.json): the historical EPERM becomes
`network`, exit 5, three attempts. `passed: true` means the old defect was
reproduced. [Fixed](results/portable-fixed/results.json): all 29 scenarios
passed, including filesystem, DNS/TLS, mixed errors, integrity/CURL23 and
success. The integrity case uses PRD exit 2 and returns `unknown` after three
attempts. The candidate also passed `bash -n` and independent Codex review.

Selected unchanged raw output: original EPERM
[stdout](results/portable-original/historical_eperm/stdout.log) /
[stderr](results/portable-original/historical_eperm/stderr.log), fixed EPERM
[stdout](results/portable-fixed/historical_eperm/stdout.log) /
[stderr](results/portable-fixed/historical_eperm/stderr.log), and integrity
[stdout](results/portable-fixed/sdp_integrity_then_curl23/stdout.log) /
[stderr](results/portable-fixed/sdp_integrity_then_curl23/stderr.log).

Only the two result JSON files have the exact private consumer-package root
replaced with `<EVIDENCE_ROOT>`. They are labelled public derivatives, not
runs at that illustrative path. Code, fixture and selected logs are unchanged;
recorded hashes were not rewritten. Original evidence is retained privately.

## Recorded real error-window check

The original launcher content block passed the controlled historical PRD reply
through each downloader version to the original `error-dialog` binary.
The [original window](ui/original/window.png) showed `network` after three
attempts; the [fixed window](ui/fixed/window.png) showed `filesystem` and the
original `Operation not permitted` detail after one attempt. Both displayed
a populated scrolling session log. The complete UTF-8 accessibility text
matched the corresponding log byte-for-byte:

- Original: [session log](ui/original/session.log), [compact result](ui/original/result.json).
- Fixed: [session log](ui/fixed/session.log), [compact result](ui/fixed/result.json).

One Quit press was attempted in each window. The AX call returned `-25204`
without confirming acceptance; a separate process check confirmed that each
helper had exited, and both parent content blocks returned 1. The helper's
own exit code was not recorded. Compact results retain these distinctions
and the complete accessibility log text, with hashes of the original receipts.

This checks the original content block and real error dialog with a controlled
PRD reply. It does not reproduce Finder/TCC startup, a full launcher run,
network installation or the physical cause of the historical EPERM.
Screenshots and session logs are unchanged. Only the exact private run root
in each recorded process command becomes `<UI_RUN_ROOT>`; original source
hashes remain unchanged. UI harnesses and application binaries are not included.

AI disclosure: OpenAI Codex authored the patch, tests and documentation and
ran the checks, including the visual/accessibility review. Separate Codex
agents reviewed code and results, including the portable runs. Human maintainer
review is pending.
