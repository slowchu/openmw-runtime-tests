# OpenMW Runtime Tests

A small agent skill and Python harness for running Lua regression probes inside
the actual OpenMW engine. An agent can write a test, launch an isolated session,
read failures and timings, change the code, and rerun the same test.

The harness supplies configuration, player/global/actor drivers, process launch,
logging and completion checks. OpenMW executes the Lua; there is no AI component
inside the engine and no special connector is required. The runner also works
directly from a terminal without an agent.

**Verified:** Windows, OpenMW 0.51.0 / Lua API 129. Python 3.9+ and your own
Morrowind game data are required. The Python harness has no third-party packages.
Other platforms and versions have not been validated. This is a real graphics
session, launched hidden on Windows, rather than a headless renderer.

## Install the skill

For Codex, ask the skill installer:

```text
$skill-installer Install skills/openmw-runtime-tests
from https://github.com/slowchu/openmw-runtime-tests.
```

Or download/clone this repository and copy `skills/openmw-runtime-tests` into
your agent's skills directory. For a default Codex installation that is
`~/.codex/skills/openmw-runtime-tests`. Start a new agent session to discover the
installed skill. Other agents supporting the Agent Skills format can use the
same folder; consult that agent's installation instructions.

Example request:

```text
Use $openmw-runtime-tests to test my OpenMW UI change in an isolated engine
session. Exercise resizing and element removal, preserve the logs, and report
Lua timings separately from following frame intervals.
```

## Run without an agent

From the repository root, replace the example paths with your installation:

```powershell
python -B skills/openmw-runtime-tests/scripts/run_probe.py `
  --openmw 'C:/Games/OpenMW/openmw.exe' `
  --resources 'C:/Games/OpenMW/resources' `
  --data 'C:/Games/Morrowind/Data Files' `
  --content Morrowind.esm `
  --archive Morrowind.bsa `
  --probe skills/openmw-runtime-tests/assets/ui_lifecycle.lua `
  --start 'Vivec, Arena Pit' `
  --output 'C:/OpenMW-test-runs/ui-001'
```

The bundled example creates a native Lua UI element, updates its size/content
across frames, checks its layout, destroys it, and verifies destruction. It
requires no WandForge, UI Toolkit, SFP or other mod. Add explicitly ordered
`--data` and `--content` arguments to test your own mod and its dependencies.

Choose one context per session:

| Context | CLI arguments | Bundled example |
|---|---|---|
| Player (default) | `--context player` | `assets/ui_lifecycle.lua`: native UI update and destruction |
| Global | `--context global` | `assets/global_lifecycle.lua`: create, place, and remove a world object |
| Actor | `--context actor --actor-record rat` | `assets/actor_stats.lua`: modify and restore a creature/NPC's health |

The asset paths above are under `skills/openmw-runtime-tests/`. Use the same
launch command with the chosen context/probe and a fresh output directory.
For an NPC check, replace `rat` with an NPC record ID such as `fargoth`.
Actor mode creates a new instance; it does not select the existing world actor.
A global host attaches the actor driver, checks messages in both directions,
and verifies the new actor was removed before reporting success.

The Lua probe returns a table with `step(dt)` and optional `cleanup()`. The driver
calls it on each player `onFrame` or global/actor `onUpdate` after the cell is ready. Returning
`true` finishes the probe; assertion failures finish with a failed result.
See [the probe contract and usage guide](skills/openmw-runtime-tests/references/usage.md).

## What counts as a pass

- The current run reports BEGIN, PASS and COMPLETE in order.
- The engine exits successfully before the timeout.
- No failure marker or detected Lua error occurs.

A zero engine exit on its own is insufficient. The runner returns a failing
status for assertion failures, missing completion, crashes or timeouts. Output
contains `result.json`, stdout/stderr, the engine log, isolated configuration,
the staged probe and test-only user storage. Existing output is never replaced.
On timeout, only the harness's own process is stopped.

For a negative control, change `--probe` to
`skills/openmw-runtime-tests/assets/assertion_failure.lua` and use a fresh output
directory. The harness must fail even if OpenMW itself exits with code 0.

## Timing and limits

The example prints Lua update time and subsequent callback intervals separately.
Queued UI/rendering work is not included in the Lua callback time. Frame
intervals include other engine work and are not isolated UI/GPU render timings.
The small example demonstrates instrumentation; it is not a performance benchmark.

Automated layout checks do not confirm rendered pixels or real mouse interaction.
Visual acceptance remains a separate check. The harness supports player, global,
and actor probes in fresh test sessions. MENU, LOAD, and local scripts on
non-actor objects are not bundled. Tests spanning several contexts can use
supporting scripts and the mod's events/interfaces; there is no automatic
multi-context test suite. It does not attach a debugger, automate arbitrary game
input, or certify save compatibility.

Run the harness's regression tests without OpenMW:

```powershell
python -B skills/openmw-runtime-tests/scripts/test_run_probe.py
```

See [validation evidence](skills/openmw-runtime-tests/references/validation.md)
for the tested scope. No game files, third-party mods or machine-specific logs
are distributed. Code is available under the [MIT license](LICENSE).
