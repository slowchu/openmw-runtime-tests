# Verified scope

Validated on **2026-10-11** using Windows, OpenMW 0.51.0 (Lua API revision 129),
and Python 3.12. Game inputs were only Morrowind.esm and Morrowind.bsa from an
existing user-owned installation, plus OpenMW's built-in scripts/resources and
the generated probe overlay. No WandForge, UI Toolkit, SFP or other mod was
required. Config, data-local, logs and user storage used dedicated test paths.

## Native engine checks

| Probe | Engine exit | Harness outcome | Evidence |
|---|---:|---|---|
| UI lifecycle | 0 | Pass | Created a real Lua UI Element, changed size/content over frames, destroyed it, verified layout became nil, completed the current run's marker sequence |
| Global object lifecycle | 0 | Pass | Used real GLOBAL-only world APIs to create/place three gold items, observed the placement, removed the object, and observed count zero |
| Creature actor stats (`rat`) | 0 | Pass | CUSTOM driver ran on a newly spawned active creature; global/local event handshake completed, local health write/restoration was observed, host verified removal and absence from active actors |
| NPC actor stats (`fargoth`) | 0 | Pass | Same native lifecycle/stat checks on a newly instantiated NPC, without selecting the existing NPC |
| Intentional assertion failure in player, global, and actor probes | 0 | Fail (3 runs) | Each driver caught the assertion and reported FAIL; engine exit 0 did not override the failure |
| Cleanup failure in global and actor probes | 0 | Fail (2 runs) | Cleanup assertions could not produce a successful result |
| Non-actor record supplied for actor probe | 0 | Fail | Host rejected a gold item as an actor and reported the setup failure |
| Missing actor record | 0 | Fail | World creation failed and host reported FAIL |
| Player-only UI API in global probe | 0 | Fail | Engine context restriction was caught and reported |
| Premature core.quit() in global probe | 0 | Fail | BEGIN without PASS/COMPLETE was rejected |
| Never-completing actor probe | 1 after termination | Fail | External 8-second timeout fired; owned process stopped |
| Unhandled onUpdate error in another test-only PLAYER script | 0 | Fail | The global probe completed, but the engine's Lua error was detected and invalidated the run |

All **15 native scenarios** in the context-extension check matched their
expected success/failure outcomes. Earlier player-only negative controls also
covered premature quit, timeout and an external engine Lua error.

The initial prototype ran its first onFrame before the player's starting cell
was assigned. The final driver explicitly waits for a player cell before loading
the case. The lifecycle example then passed with native UI and no Lua errors.

The first global removal check waited for `isValid()` to become false and timed
out. Native execution showed that removed references retain valid handles; the
final checks observe count zero (or an invalid handle), and the actor host also
verifies absence from `world.activeActors`. Final success scenarios passed with
these actual engine semantics. Failing prototype evidence was retained locally.

## Runner regressions

All **17 standalone tests** passed, covering valid completion, missing completion,
failure with exit 0, late engine errors, nonzero exits/timeouts, duplicate or
out-of-order markers, stale run IDs, profile isolation, existing-output refusal,
outputs inside game data, invalid filenames/timeouts, configuration path escaping,
launch failure, termination of only the owned child process, global/actor
registrations, actor record quoting, required actor records, and refusal of actor
arguments in other contexts.

Run them with `python -B scripts/test_run_probe.py`. Reproduce the native success
and negative assertion controls using the commands in the usage reference and
a fresh evidence directory for each run.

## Limits

This validates native UI/world/actor integration, the supplied lifecycle/stat
checks, bidirectional actor-host events, and failure reporting.
It does not validate the appearance of rendered widgets, physical user input,
other platforms/engine versions, MENU/LOAD/non-actor local probes, long-duration
performance, arbitrary mod gameplay behavior,
or public-save compatibility. The example's few timing samples demonstrate
instrumentation only. Full machine logs stay local because they contain private
paths; this summary records outcomes without those paths.
