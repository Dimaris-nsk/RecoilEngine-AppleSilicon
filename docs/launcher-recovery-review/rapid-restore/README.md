# Rapid metadata backup and restore

The original launcher continued after a failed removal of `rapid` and logged
successful restoration. It could use a partial copy or undo an accepted
update after failed cleanup. The candidate publishes a ready backup only
after copying succeeds, stops on restore failures, and retires an accepted
backup before cleanup. A legacy backup of unknown completeness and current
metadata are preserved for inspection. Only `packaging/launcher.sh` changes.

Base: [Vandomas/RecoilEngine-AppleSilicon, 562fe461](https://github.com/Vandomas/RecoilEngine-AppleSilicon/blob/562fe461f8b045f863089815edac7f2d6559e178/packaging/launcher.sh).
[manifest.json](manifest.json) identifies all inputs, original results and
public copies. The full launcher files are inputs for exact block extraction
and review; **do not execute those full scripts**.

## Repeat

Use macOS with Python 3 and standard system utilities. Keep this layout and
run from its root using unused result labels:

```sh
python3 test_rapid_restore.py original --label recipient-original
python3 test_rapid_restore.py fixed --label recipient-fixed
```

The test extracts the real backup functions and outcome branches, uses actual
file trees and narrow `cp`/`rm`/`mv` failure injections, and records file hashes
and subsequent-launch results. Downloads, dialogs and the game boundary are
finite fixtures. Interrupted states are created as files. No extra Python
packages, PRD, game data, GUI, network or process signals are used.

## Recorded results from this portable package

Both runs used the included test, SHA256
`cd38422019dec87bef9c33443c09da8b5e6afc56f50958b12816d3a8e97b87cc`.
[Original](results/portable-original/results.json): three defects reproduced
in four runs. `passed: true` means the wrong behavior was observed; the
[original rm stderr](results/portable-original/rm-failure-false-success/run-1/stderr.txt)
preserves its primary diagnostic. [Fixed](results/portable-fixed/results.json):
30 scenarios / 52 runs passed, covering partial copy/delete/move failures,
every caller, ordinary success and fallback, interrupted states, legacy
backups and paths with spaces. The candidate passed `bash -n`; independent
Codex review found no blocking defect within the single-writer profile scope.

For the file tests, only the two results JSON files and selected stderr have the exact private
consumer-package root replaced with `<EVIDENCE_ROOT>`. These are public
derivatives, not fresh runs at that illustrative path. Code and tests are
unchanged. The manifest records original and public-copy SHA256 values.

**Hashes inside before/after snapshots describe the original files before
redaction.** A log string with `<EVIDENCE_ROOT>` therefore no longer hashes to
its recorded original log-file digest; those digests were not rewritten.
The rapid metadata fixtures contain no private paths, so their hashes remain
directly comparable. Original evidence is retained privately.

## Recorded check with the real helper windows

The exact candidate block (lines 359–598) ran in a fresh profile with a finite
offline download stub and one injected restore `rm` failure. Both helpers were
the unchanged v0.15.1 binaries. Codex reviewed the actual windows: the
[progress window](ui/progress-window.png) appeared and closed without input
after FIFO EOF; the error dialog showed `[filesystem]`, the primary `rm`
diagnostic and the complete session log. Its Accessibility text exactly
matched the original 430-byte log. Both helpers exited 0; the content block
exited 1, with the complete ready backup preserved and no installation marker.

[Review summary](ui/review-summary.json) is an explicit synthesis with source
hashes, not a raw harness result. Supporting records are the
[session log](ui/first-run-download.log),
[error-window Accessibility text](ui/error-window-ax.json),
[progress receipt](ui/progress-window-receipt.json),
[error receipt](ui/error-dialog-receipt.json) and
[Quit attempt](ui/quit-press.json). That single AXPress returned `-25204`
without acknowledging completion; no retry was made. Normal closure is
supported by the subsequent exit-0 receipt and Codex's recorded observation.

The progress PNG is byte-identical. The error PNG contains a private path and
is omitted, without editing. UI text copies replace only the exact private
run root with `<EVIDENCE_ROOT>`; manifest entries record original and public
hashes. The receipt's 430-byte size and log digest describe the original
unredacted log, not its shorter public copy.

This checks the bounded content-block → failure/log/FIFO → real-helper path.
It does not qualify the full launcher, Finder/LaunchServices, TCC, a real
network installation, Skip, or engine/game behavior. The probe adds helper
parents and changes binary paths; its harness and binaries are not included.
It does not establish the historical EPERM cause. Partial deletion can already
have changed the current tree; the complete backup is the recovery source.
Power-loss durability, concurrent writers and a profile lock were not tested.

AI disclosure: OpenAI Codex authored the patch, tests and documentation and
ran the checks. Separate Codex agents reviewed code and results, including
these portable runs. Human maintainer review is pending.
