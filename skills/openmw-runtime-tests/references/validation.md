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
| Intentional assertion failure | 0 | Fail | Driver caught the assertion and reported FAIL; engine exit 0 did not override the failure |
| Premature core.quit() | 0 | Fail | BEGIN without PASS/COMPLETE was rejected |
| Never-completing probe | 1 after termination | Fail | External 8-second timeout fired; owned process stopped |
| Unhandled onUpdate error in another test-only PLAYER script | 0 | Fail | The UI probe completed, but the engine's Lua error was detected and invalidated the run |

The initial prototype ran its first onFrame before the player's starting cell
was assigned. The final driver explicitly waits for a player cell before loading
the case. The lifecycle example then passed with native UI and no Lua errors.

## Runner regressions

All **13 standalone tests** passed, covering valid completion, missing completion,
failure with exit 0, late engine errors, nonzero exits/timeouts, duplicate or
out-of-order markers, stale run IDs, profile isolation, existing-output refusal,
outputs inside game data, invalid filenames/timeouts, configuration path escaping,
launch failure, and termination of only the owned child process.

Run them with `python -B scripts/test_run_probe.py`. Reproduce the native success
and negative assertion controls using the commands in the usage reference and
a fresh evidence directory for each run.

## Limits

This validates native Lua UI integration, layout lifecycle and failure reporting.
It does not validate the appearance of rendered widgets, physical user input,
other platforms/engine versions, long-duration performance, gameplay behavior,
or public-save compatibility. The example's few timing samples demonstrate
instrumentation only. Full machine logs stay local because they contain private
paths; this summary records outcomes without those paths.
