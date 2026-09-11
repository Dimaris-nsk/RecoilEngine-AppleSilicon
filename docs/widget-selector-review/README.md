# Widget Selector: native before/after evidence

Removing the unused `include("fonts.lua")` lets Widget Selector initialize in
the tested macOS v0.15.1 client. The original file fails on the missing
`LuaUI/fonts.lua` before creating its instance or WG API. The fixed selector
opens a readable list, filters for BuildETA, clears the query, switches that
widget off and on, closes, and works again after native LuaUI reload.

The one-line patch targets `luaui/Widgets/widget_selector.lua` in
Vandomas/Beyond-All-Reason at `fa05768ed652db1466490f36085dbca646e25341`.
The selector already loads its own fonts with `gl.LoadFont`; its legacy
`fontHandler` is unused. Both complete files previously passed Lua 5.1 syntax
checks; a focused loader-prefix check reproduced the missing-include failure.

## Recorded native results

[Results](results.json) include exact source hashes, selector identity,
BuildETA state, camera positions, LuaUI generation and normal exit. Selected
[original](original-infolog-excerpt.log) and [fixed](fixed-infolog-excerpt.log)
log lines are copied verbatim, with original line numbers and full-log hashes.

| Check | Recorded result |
|---|---|
| Original | Native missing-font error; zero selector instances, no WG API |
| Fixed | One initialized selector from the expected archive; no RAW shadow |
| Search | Full `BuildETA` query finds its row; Escape clears it |
| Toggle | BuildETA active/enabled/instances: true/true/1 → false/false/0 → true/true/1 |
| Reload | Generation 1 → 2; selector and BuildETA each have one active instance |
| Ordinary input | Camera px changes after closing in both generations |
| Exit | Both runs end normally with engine code 0, lifetime EOF, empty group; no emergency termination |

Four unchanged native framebuffer images:

- [Opened list](opened.png).
- [BuildETA search](search.png).
- [BuildETA switched off](toggled.png).
- [Reopened after LuaUI reload](reopened.png).

The root Codex agent personally inspected 11 native and five physical fixed-run
captures; the package-preparation agent also viewed these four PNG. The raw
observer's `visual_review_pending=true` remains an initial flag. The separate
later root review records the visual verdict; an automatic success field alone
does not establish it. Original `passed=true` means the defect was reproduced.

## Scope and limits

These are private component packages based on BAR `test-31251-0ceadc7`, using
the exact fork-original or candidate selector. Their 18,469-entry descriptors
differ only in that file; the other 18,468 entries are identical. The fork's
other selector differences from the packaged game were preserved. This is not
a run of the entire fork distribution or an online match.

Known game/driver warnings remain. LuaUI reload includes a recorded 2,793 ms
draw gap, followed by continued simulation and input; no uninterrupted
performance claim is made. Camera position/distance survives reload, but some
orientation fields and numeric widget ordering change. The check establishes
enabled state and instance restoration, not identical whole-profile bytes or
a broad test of BuildETA's calculations.

Only selected evidence is included: no game profiles, binaries, full raw logs,
account data or desktop captures. Source paths in [manifest.json](manifest.json)
are relative identifiers for retained private originals. PNG bytes are unchanged;
their metadata contains only the DevIL generator and empty Author/Description.
The visible player name is the local `SelectorReview` fixture, not an account login.

OpenAI Codex authored the change and checks and performed agent review. Human
review is requested through the PR. The account owner is not represented as
having independently reviewed or tested the code.
