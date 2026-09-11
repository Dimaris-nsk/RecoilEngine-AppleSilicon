# Chobby rapid repository order: review evidence

The macOS launcher omits `RapidTagResolutionOrder`. In the pinned Chobby,
an empty value selects `rapid/repos.springrts.com/byar-chobby/versions.gz`,
while the saved BAR list is under `repos-cdn.beyondallreason.dev`. Chobby then
skips its lobby-version backup. A controlled list update confirms that the
new lobby tag remains after download completion.

The [15-line patch](candidate.patch) seeds
`repos-cdn.beyondallreason.dev;repos.beyondallreason.dev` after bundled defaults
are merged, only when the complete key is absent. This is the order in both
included official Linux/Windows launch configurations. Existing values,
including custom and empty values, are preserved for this invocation. A read
or append failure stops through the launcher's existing `fail_dialog`.
[Product explanation](PR-DRAFT.en.md).

## Sources

- Launcher base: [Vandomas/RecoilEngine-AppleSilicon, 562fe461](https://github.com/Vandomas/RecoilEngine-AppleSilicon/blob/562fe461f8b045f863089815edac7f2d6559e178/packaging/launcher.sh).
  [Original](original/packaging/launcher.sh) and [candidate](candidate/packaging/launcher.sh)
  differ only by that added block. Neither complete script is executed by these tests.
- Chobby: `test-4630-26b5200`, package `4e10d9c250bab70be5b47d706f535c4d`.
  The included public `versions.gz` reports commit
  `26b5200b6a3e38dd02355f3e11cbddf99e9f7b72` in
  [BYAR-Chobby](https://github.com/beyond-all-reason/BYAR-Chobby).
  Five extracted Lua/config files match the included SDP's MD5 entries and
  their recorded SHA-256 values; this is package verification, not a separate
  comparison with Git checkout bytes.
- [sources.json](sources.json) records source references and content hashes.
  The historical warning fixture contains only two relevant lines; its private
  full log is not included. No game account or personal profile is included.

## Repeat the offline checks

Use a normal, non-root Unix account, writable copy of this directory, Python
3.9+ with assertions enabled, an already installed `lupa.lua51`, and `/bin/bash`.
The recorded execution used Python 3.12.14, Lupa 2.6 and Lua 5.1 on macOS.
Select that Python environment before running; no private runtime path is
embedded in the scripts and no dependencies are installed by them.

```sh
python3 -B probe.py --label review-cause
python3 -B test_seed.py --label review-seed
```

Use unused labels. Results and temporary profiles remain under `results/` in
that copy. The seed test changes permissions only on files it creates, restores
them afterward, and runs only the extracted added shell block. It substitutes
a message recorder for `fail_dialog`. It does not run the full launcher,
engine, UI, downloads, network requests or process signals.

## Recorded portable execution

A fresh consumer copy was used once for each command. These are new executions
of the included portable scripts, distinct from the earlier private checks;
[adaptation.json](adaptation.json) records both sets of source hashes.

- [Cause results](recorded/portable-cause/results.json): six expected outcomes,
  exit 0. Empty/absent settings reproduce the missing backup. Official/custom
  orders restore the original gzip bytes and installed lobby tag through both
  completion routes. Reinitialization in the same Lua instance is covered.
- [Seed results](recorded/portable-seed/results.json): 12 configuration cases,
  13 exact-block invocations and three Lua integrations, exit 0; `bash -n`
  also passes. Missing key/newline, comments, similar prefixes, repeated start,
  custom/empty/duplicate entries and real temporary-file read/write failures
  are covered. The actual newly seeded value restores the original list;
  intentionally preserved empty still reproduces the missing protection.
- [Execution record](recorded/execution.json) records commands, counts, exits
  and raw-output hashes. [manifest.json](manifest.json) maps all included files
  to their sources and hashes. In the seed result and three selected stderr
  files, only the exact private consumer root was replaced by `<EVIDENCE_ROOT>`.
  Raw and public hashes are both recorded. Embedded `stderr_sha256` fields
  retain the original raw hashes and therefore do not hash the redacted text.

## Native BAR validation

[Completed native comparison](live/README.md): the original configuration skips the
backup and retains the controlled unavailable lobby tag. With the exact seeded
configuration, genuine Chobby restores the original gzip bytes, recognizes the
installed tag, runs a short BAR game and returns to the same menu. Both runs exit
normally with code 0. Four unchanged native PNG, source-indexed log excerpts and a
compact result projection are included. The root Codex agent also inspected separate
physical captures at each checkpoint.

The local adapter supplies a controlled incoming list and completion callback;
no network transfer is claimed. Remaining game/driver warnings are classified in
[live/results.json](live/results.json), not hidden or reported as fixed by this patch.

## Limits

The portable Lua probe supplies controlled Spring/VFS inputs and simulates
completion; the separate native run uses the actual engine and Chobby handler
with controlled transport. Neither performs a network download. The portable seed
integration uses a configuration-value adapter; the separate native run reads the
resulting setting through the real engine. The
ordinary configuration file is expected to exist after earlier launcher setup;
other configuration sources and an explicit `--config` path are outside scope.

A new Lua instance during an unfinished update caches the changed list; this
patch does not provide recovery after interruption. The engine can remove an
explicit empty value when `StoreDefaultSettings=false`, so preserving its bytes
here does not preserve that intention across all full launches. No crash,
historical EPERM cause, or broader release-readiness claim is made.

The native check covers direct startup and same-process game-to-menu return, not
the complete Finder/launcher update path, account login or public multiplayer.

OpenAI Codex authored the patch, adaptation, checks and explanation and performed
the visual inspection. Agent review is not human review; human review is requested
through the PR. The account owner is not represented as having independently
reviewed or tested the code.
