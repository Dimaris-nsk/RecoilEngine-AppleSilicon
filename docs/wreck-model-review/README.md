# Restore the missing corfast/corhack wreck model

The saved original run removed `corfast_dead` and `corhack_dead` because their shared `Units/corfast_dead.s3o` was missing. The proposed change restores that existing BAR model without changing its bytes, unit definitions or balance. The [original excerpt](original-excerpt.log) contains the two removal warnings.

The source is [historical BAR commit 165bb063](https://github.com/beyond-all-reason/Beyond-All-Reason/blob/165bb063ed5221ff630abab85cb297a74a6f65ae/objects3d/Units/corfast_dead.s3o), blob `645778f5c54241d08b3969a1db0ca388effb890c`, 65,892 bytes. Why it was removed in [PR 5881](https://github.com/beyond-all-reason/Beyond-All-Reason/pull/5881) remains unknown; maintainer review is requested.

## Actual game check

One completed local run used macOS engine v0.15.1 and BAR `test-31251-0ceadc7` on All That Smolders v1.2. A private game package retained all 18,469 existing entries and added only the historical model. The game observer recorded its exact SHA-512, archive identity and absence of a raw-file override. This tests the model in that pinned game, not the entire current fork distribution.

| Stage | Recorded result | Native screenshot |
| --- | --- | --- |
| Both deaths | Native death events produced both textured corpses, with metal 126 and 756. | [Both wrecks, frame 24300](both-wrecks.png) |
| Resurrection | A cornecro builder targeted the corhack corpse. After observed progress, the game created corhack 12042 and removed its corpse at frame 37099. | [Resurrected unit, frame 37529](resurrected.png) |
| Heap | With only the corfast corpse beyond the unchanged 157 rocks, one native `ReduceWrecks` invocation damaged it into `corfast_heap`, metal 52. | [Heap, frame 39526](heap.png) |
| Reclaim | The builder targeted that heap; the matching destruction event was followed by its absence, an idle builder and interval metal income/excess. | [Reclaimed, frame 41038](reclaimed.png) |

The final snapshot contains the same 157 baseline rocks and the restored corhack. The engine then exited normally with code 0 after 1,527.278425 seconds; the lifetime channel closed and its process group was empty, without emergency termination.

[Results and source hashes](results.json) retain the relevant definitions, commands, events, selected snapshots and separate root Codex visual-review record. [Fixed log excerpts](fixed-excerpt.log) quote original numbered ranges. The four PNGs are unchanged native framebuffer images, personally inspected by the operating and independent Codex agents. The observer's raw `manual_review_pending` flag is preserved in the projection: observer delivery alone is not visual acceptance, and these agent reviews do not substitute for human artwork/gameplay review.

## Boundaries and remaining diagnostics

The original failure is supported by the saved definition-removal log and source; no original death screenshot was taken. The fixed test covers corhack resurrection and corfast heap/reclaim, not every possible path for both units. Intermediate fractional `reclaim_left` was not captured. Storage was full, so the evidence does not claim exactly 52 net metal credited.

The test used `Sound=0`. The `xplomed2` warning follows the NullSound lookup path even though the real sound file and alias exist; audio with `Sound=1` was not tested. The log also retains selector/fonts, geometry-shader and content/driver warnings, deprecated settings and command-completion translation messages. Recorded draw gaps reached 3,355 ms, and the last logged dropped-present counter was 524,288; that counter is not an exact total of all dropped presentations. This model-specific result does not establish general rendering performance or stability improvements. This is a model-specific result, not a clean-log or complete regression claim. Multiplayer and cross-platform synchronization were not tested.

Only selected state, verbatim excerpts and four in-game images are included. Full raw logs, local paths, run tokens and desktop captures remain private. [Manifest](manifest.json) identifies every public file and its provenance. OpenAI Codex prepared this change and evidence; the restored model is unchanged historical BAR artwork. Human review is requested through the PR.
