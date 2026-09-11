# Native Chobby comparison

The original configuration reproduced a missing lobby-list backup in real Chobby.
With the candidate setting, the unchanged handler restored the original gzip bytes,
recognized the installed lobby tag, entered a short BAR game and returned to the
same menu. Both runs ended through ordinary Quit with engine exit 0, closed lifetime
channel and no remaining process-group members; emergency termination was not used.

| Check | Original | Fixed |
|---|---|---|
| Selected backup host | repos.springrts.com | repos-cdn.beyondallreason.dev |
| Initial saved cache | absent | 146201 bytes |
| Controlled changed list | 145974 bytes; missing lobby tag | same |
| After native completion callback | changed list remains | original 146201 bytes restored exactly |
| Native tag after completion | controlled-not-downloaded, archive absent | test-4630-26b5200, archive present |
| Game and return | not attempted with missing tag | frame 90 / 539 world draws; return requested at frame 832 |

[Selected results and raw-source hashes](results.json),
[original log excerpt](original/infolog-excerpt.log),
[fixed log excerpt](fixed/infolog-excerpt.log).
The original result's `passed=true` means successful reproduction of the defect.
Log excerpts preserve exact selected lines and identify their one-based positions;
full logs remain private. Images are unchanged native framebuffer captures:

- [Original menu after failed protection](original/menu.png).
- [Fixed menu after exact restore](fixed/restore-complete.png).
- [Actual short BAR game](fixed/game.png).
- [Returned native menu](fixed/returned-menu.png).

The root Codex agent inspected native images and separately captured physical windows
at both original stages and all four fixed stages. Complete menus including Exit/footer
and game terrain, commander and HUD were visible. The framed menu window was
1000×682 points, fully on screen; its content captures are 2000×1300 pixels. The
package-preparation Codex agent also viewed all four published PNG. A screenshot
alone cannot establish gzip restoration; byte hashes and native tag lookup do that.

## What was real and what was controlled

Release v0.15.1 engine `8ab9474`, Chobby `test-4630-26b5200`, BAR
`test-31251-0ceadc7` and All That Smolders v1.2 ran in an isolated profile.
The exact default-merge and 15-line seed blocks generated the configuration before
direct engine startup. This was not the complete Finder/launcher update path.

The genuine Chobby handler created the cache, scheduled the game request, emitted
DownloadStarted and processed its registered completion callback. The local adapter
replaced only Connector.Send transport: while the real queue was active it wrote a
controlled incoming list pointing to an unavailable lobby version, then invoked the
original completion callback. It never wrote the cache or restored the final list.
The callback reported success for this controlled completion; it is not evidence of
a completed network download. The fixed phase then used native Reload to enter the
installed game and Reload with an empty script to return to the same LuaMenu/process.

Offline fixture choices were identical between phases: manual window mode, native
Analytics API retained with empty TCPAllowConnect (native denial before DNS), external
network denied by the OS sandbox, OpenSkill snapshot downloader disabled, Sound=0,
and the precise plugin-manifest resource request cancelled through its registered
callback (`isSuccess=false`, `isAborted=true`). That cancellation drained the queue
without restoring the rapid list. The expected plugin notification is not a plugin
catalogue test. The fixture's VSyncGame value was 1; runtime VSync reports do not
establish that the requested interval was effective.

## Remaining diagnostics

The game log is not clean. It still reports missing corfast/corhack feature models,
`widget_selector.lua` failing on `LuaUI/fonts.lua`, deprecated AdvSky, and other Lua,
map, definition and asset diagnostics. Geometry-shader errors explicitly describe
this driver's rejected stage; some effects confirm a successful NoGS fallback, not
all of them. The fixture's disabled sound produces repeated Starting Track messages
(also visible in the game image). Duplicate-tag, path, font and draw-gap diagnostics
are retained with their limits in `remaining_diagnostics` in [results.json](results.json).
They are not represented as repaired by RapidTagResolutionOrder or as proof of its
causal involvement. This run is neither a general rendering/performance qualification
nor a multiplayer test.

## Exact observer excerpts

These portions show the controlled boundary. Their full deployed files are retained
in the named fixed raw run and identified in results.json; the live adapter and binaries
are not shipped here. The reproducible commands in the [parent README](../README.md)
cover the included portable offline checks.

`LuaMenu/Widgets/dbg_bar_chobby_rapid.lua`, lines 264–285; complete deployed file SHA-256 `449795f7b0ab88664bd83623ad0c05467a0e5e58b9fcefe85fdc305e6c0d46d4`:

```lua
    WG.DownloadHandler.QueueDownload(gameName, 'game', 1)
    event('public-queue-request', gameName)
  elseif state.stage == 'queued' and started and #state.commands == 1 then
    local queue = WG.DownloadHandler.GetDownloadQueue()
    assert(#queue == 1 and queue[1].name == gameName and queue[1].id == started.id and queue[1].active == true, 'Actual queue is not active')
    state.active_queue = {id=queue[1].id,name=queue[1].name,fileType=queue[1].fileType,active=queue[1].active}
    rawWrite(rapidPath, changed) -- Only the simulated incoming list, never cache or restore.
    assert(rawRead(rapidPath) == changed, 'Controlled gzip replacement failed')
    assert(VFS.GetNameFromRapidTag('byar-chobby:test') == changedName and not VFS.HasArchive(changedName), 'Actual tag did not resolve to absent changed name')
    state.during_update = {resolved_name=changedName, archive_present=false, bytes=#changed}
    state.stage = 'mutated'
    event('gzip-mutated-while-active', changedName)
  elseif state.stage == 'mutated' then
    local callbacks = WG.Connector.callbacks.DownloadFinished
    assert(#callbacks == 1, 'Completion callback set changed')
    callbacks[1]({name=gameName, isSuccess=true, isAborted=false})
    local queue = WG.DownloadHandler.GetDownloadQueue()
    assert(#queue == 0 and state.finished_listener, 'Real completion did not drain queue and notify listeners')
    local expected = phase == 'fixed' and original or changed
    local expectedName = phase == 'fixed' and originalName or changedName
    assert(rawRead(rapidPath) == expected, 'Final gzip bytes mismatch')
    assert(VFS.GetNameFromRapidTag('byar-chobby:test') == expectedName, 'Final native tag resolution mismatch')
```

`LuaMenu/Widgets/dbg_bar_chobby_rapid.lua`, lines 296–301; complete deployed file SHA-256 `449795f7b0ab88664bd83623ad0c05467a0e5e58b9fcefe85fdc305e6c0d46d4`:

```lua
  elseif state.stage == 'restore-complete' and not screenshot and advanced('restore-complete') then
    heldAt = nil
    if phase == 'original' then finish(); return end
    state.stage = 'launching-game'
    event('reload-game-request', gameName)
    nativeReload(assert(rawRead('game.txt'))) -- API takes script CONTENT, not a path.
```

`LuaUI/Widgets/dbg_bar_chobby_rapid.lua`, lines 38–41; complete deployed file SHA-256 `5a5373b24d419c181b33f0a3a0da1798f6fcf62e4db24b7c7ed3cf3ea8825ac8`:

```lua
    write('game-return-request.json', string.format('{"token":"%s","frame":%d,"world_draws":%d}', token, Spring.GetGameFrame(), draws))
    returned = true
    Spring.Echo('[chobby-rapid-game] normal reload to menu', Spring.GetGameFrame(), draws)
    Spring.Reload('')
```

No account login, real transfer, full Finder launch, or fresh process during an
unfinished update was tested. OpenAI Codex authored and ran the checks and performed
visual inspection. Human review is requested through the PR.
