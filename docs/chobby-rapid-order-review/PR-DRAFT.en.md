# Seed the missing Chobby rapid repository order

When `RapidTagResolutionOrder` is missing, the bundled Chobby selects the old
`repos.springrts.com` path for its lobby-version backup. With the current list
under `repos-cdn.beyondallreason.dev`, that backup is skipped. A controlled list
update then leaves the lobby tag pointing to a version that is not installed.
With the official repository order, the existing Chobby handler restores the
original list and installed lobby tag.

This adds 15 lines to `packaging/launcher.sh`, based on
`562fe461f8b045f863089815edac7f2d6559e178`. After merging bundled defaults,
seed `repos-cdn.beyondallreason.dev;repos.beyondallreason.dev` only when the
complete key is absent. Existing entries, including empty/custom values and
whitespace, remain unchanged. Read or append errors stop through the existing
error helper. No Chobby or engine code is changed.

Validation:

- Six portable Chobby cases, 12 configuration cases with 13 executions of the
  exact shell block, three integrations using the resulting setting, and shell
  syntax validation. All expected outcomes passed.
- In real v0.15.1 Chobby `test-4630-26b5200`, the original configuration reproduced
  the missing cache. The candidate restored the exact original 146201-byte gzip
  and native installed tag after a controlled incoming-list update and completion
  through the genuine handler callback.
- The fixed client entered a real short BAR `test-31251-0ceadc7` game and returned
  to the same menu. Codex agents inspected native and physical window captures;
  both original and fixed runs ended normally with engine exit 0.

[Evidence, screenshots and reproducible offline checks](README.md).
The native test used direct engine startup with configuration produced by the
exact launcher blocks and a local transport adapter. It does not establish a
real network download, complete Finder/launcher update, account login or public
match. Remaining game/driver warnings are documented in the evidence and are
not claimed to be fixed here.

This does not recover an interrupted update in a fresh Lua instance/process.
The engine may remove explicit empty defaults on a later launch. OpenAI Codex
authored the change, tests and explanation and performed the visual checks;
human review is requested through this PR. The account owner is not represented
as having independently reviewed or tested the code.
