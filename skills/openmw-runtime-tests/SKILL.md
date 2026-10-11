---
name: openmw-runtime-tests
description: Run isolated Lua regression probes inside the actual OpenMW engine on Windows, capture pass/fail evidence, and measure Lua callbacks separately from frame intervals. Use when an OpenMW mod needs native runtime validation beyond standalone Lua mocks.
license: MIT
---

# OpenMW Runtime Tests

Use the bundled Python runner to launch an isolated OpenMW session with a
player, global, or actor Lua probe. The agent writes the probe, runs the engine, reads the
results, and iterates within the user's authorized task. No AI runs inside the
engine. Requires a local Windows installation, Python 3.9+, and game data owned
by the user. Verified with OpenMW 0.51.0 / Lua API 129; do not assume other
platforms or versions have been tested.

## Run a probe

1. Read the project's applicable instructions. Identify the executable,
   resources directory, exact permitted data directories, ordered content
   files/BSA archives, and a start cell. Read the user's configuration only to
   identify necessary inputs; the runner never imports the normal profile or
   automatically scans sibling projects. Do not include unrelated mods.
2. Choose `--context player` (default), `global`, or `actor`. Start from
   [UI lifecycle](assets/ui_lifecycle.lua), [global object lifecycle](assets/global_lifecycle.lua),
   or [actor stats](assets/actor_stats.lua) and adapt it to the behavior being checked. Read
   [references/usage.md](references/usage.md) for the module contract and launch
   example. Keep assertions meaningful; a module loading without errors does
   not establish that its behavior works.
3. Run `scripts/run_probe.py` with explicit input paths and a new `--output`
   directory. Data directory order controls overrides. Put a staged candidate
   data directory after installed data when testing an unpublished change.
4. Read `result.json`, `stdout.txt`, `stderr.txt`, and `config/openmw.log`.
   A pass requires the current run's BEGIN, PASS, COMPLETE sequence, successful
   process exit, no timeout, and no detected Lua errors. A zero engine exit
   alone is not success. Preserve failing evidence before a scoped repair.
5. Report what was exercised, engine/API version, result, evidence path, and
   remaining acceptance checks. If fixing a regression, run the same test
   against the old and candidate code when practical.

The runner uses separate configuration, generated probe data and user storage.
It refuses an existing output directory or an output inside supplied game data.
Windows launches are hidden and do not grab input. On timeout it stops only the
process it started. It does not install candidate files into a live mod, change
normal engine configuration, or grant permission to publish/deploy changes.
Keep probe scripts and generated profiles out of distributed game mods.

## Test boundaries

- The bundled driver calls `step(dt)` once per player `onFrame` or global/actor
  `onUpdate`, after the starting cell is ready. Existing no-argument `step()`
  probes still work. Return `true` only when assertions finish; other returns continue the
  test. Optional `cleanup()` runs on completion and failure. The driver waits
  three more frames before reporting success and quitting. It is not a promise
  that all asynchronous work has finished; explicitly wait/assert the result
  your test needs. See the usage reference for dependencies that become ready
  later.
- Select the context required by the code under test; global-only APIs cannot
  be required in a player/actor probe. Each run has one selected probe context.
  Actor runs require `--actor-record <NPC-or-creature-id>`: a global host creates
  a new instance, attaches the CUSTOM driver, verifies a bidirectional event
  handshake, and removes only that instance before reporting success. Probe
  `cleanup()` runs first. MENU, LOAD, non-actor local probes, and arbitrary
  cross-context test orchestration are not bundled; use explicitly supplied
  supporting scripts/events when the current test needs them. See the usage reference.
- Native calls and layout assertions verify engine integration and structure.
  They do not establish that rendered pixels, physical mouse interaction,
  gameplay balance, or save compatibility are correct. Keep the appropriate
  manual acceptance check.
- Measure Lua operations with differences of `core.getRealTime()`. Updates can
  queue work for subsequent frames. Measure those intervals separately and
  describe them as whole-frame intervals, not UI-only or GPU render time.
  `onFrame`'s `dt` is simulation time and can be zero while paused. Record test
  load, graphics settings and sample count; do not promise normal-play FPS from
  a hidden test window.
- A script can fail before the driver catches it. The runner scans the captured
  output and engine log for Lua error messages and rejects missing completion.
  Runtime validation complements static diagnostics and standalone mocks.

## Maintain the harness

Run `python -B scripts/test_run_probe.py` for the runner regressions. Verify
changed launch/lifecycle behavior with the native UI example and
`assets/assertion_failure.lua`; the negative control must return failure even
when the engine exits 0. Read [references/validation.md](references/validation.md)
for the verified scope. Never treat game files or private machine logs as
shareable skill assets.
