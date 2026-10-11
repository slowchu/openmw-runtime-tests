# Running and adapting probes

The runner uses only Python's standard library. Supply your own OpenMW
installation and game files; none are bundled. Paths below are examples to
replace with paths on the user's machine.

## Windows / PowerShell example

From this skill's directory:

```powershell
python -B scripts/run_probe.py `
  --openmw 'C:/Games/OpenMW/openmw.exe' `
  --resources 'C:/Games/OpenMW/resources' `
  --data 'C:/Games/Morrowind/Data Files' `
  --content Morrowind.esm `
  --archive Morrowind.bsa `
  --probe assets/ui_lifecycle.lua `
  --start 'Vivec, Arena Pit' `
  --output 'C:/OpenMW-test-runs/ui-001'
```

Use an absolute output path outside every supplied data/resources directory.
Existing output directories are refused to preserve evidence. The default
timeout is 45 seconds, including engine startup; `--timeout 90` is suitable for
a slower machine or longer test. A missing resource, content file, or invalid
cell cannot be cured by waiting indefinitely: inspect the logs first.

Repeat `--data`, `--content`, and `--archive` in the intended load order. Later
data directories override earlier ones; content order is independently supplied.
For a mod test, add only its required dependencies and a candidate overlay:

```text
--data <game-data> --data <dependency-data> --data <candidate-data>
--content Morrowind.esm --content <dependency.omwscripts> --content <mod.omwscripts>
```

Only the selected probe module is copied automatically. Place any other authored
modules/assets it requires in an explicitly supplied data directory. Reserve
`scripts/omw_runtime_test/` and `omw_runtime_probe.omwscripts` for this harness.
The staged driver is last in its selected context's load order; dependencies may still need
later frames or events before they are ready.

## Choose the native context

Keep the command's installation inputs and replace the probe/context arguments:

```text
--context player --probe assets/ui_lifecycle.lua
--context global --probe assets/global_lifecycle.lua
--context actor --actor-record rat --probe assets/actor_stats.lua
--context actor --actor-record fargoth --probe assets/actor_stats.lua
```

Use a new output directory for each run. `player` is the default, preserving
existing commands. Global and actor probes use `onUpdate`; player probes use
`onFrame`. Both callbacks supply simulation `dt`, which can be zero while paused.
The runner never registers player callbacks in a global or actor script.

Global probes can use `openmw.world` directly. They wait for `world.players[1]`
to have a cell before loading the probe. Actor probes require an NPC/creature
record ID from the supplied content. A GLOBAL host creates a fresh instance,
attaches the CUSTOM probe driver, and places it 128 units from the player.
The actor waits for an active cell and a global-to-local acknowledgement before
loading the probe; completion returns through a run-specific global event.
The host removes only its owned instance, waits three further updates, checks
removal/count and absence from `world.activeActors`, then reports PASS/COMPLETE.
Removed references can still be valid handles; `isValid()` alone is not a
deletion check. Non-actor IDs, missing records and host failures fail the run.

The harness leaves actor AI enabled; the stats example disables it for its own
check. Adapt that choice when testing AI. The harness removes the actor on
reported failure as well. A process timeout ends the isolated session, so it
does not promise that Lua cleanup ran. Normal saves and actors are untouched.

Each run executes one chosen probe context, not a probe in every context at
once. For a test involving other scripts, supply their data/content explicitly
and exercise the mod's events/interfaces. Additional probe event handlers or
engine handlers are not automatically registered from the returned table.
MENU, LOAD and local probes on non-actor objects remain outside this version.

## Lua module contract

The probe is a module, not another engine-handlers table. The driver registers
the selected context's callback, waits for the cell/readiness, and requires the
module. It catches synchronous assertion errors and owns completion/shutdown.

```lua
local phase = 0
return {
    step = function(dt)
        phase = phase + 1
        -- Exercise the code under test and assert observable results.
        -- Return nil/false to wait for later updates; true means finished.
        if phase == 5 then return true end
    end,
    cleanup = function()
        -- Optional: release UI elements or other test resources.
        -- Make this safe to call again if a previous cleanup failed.
    end,
}
```

The UI lifecycle example checks native Lua UI creation, reflow and destruction
across multiple frames, using only the base game and built-in OpenMW UI. Adapt
its assertions to a genuine regression. For a later-ready dependency, check
readiness and return before advancing the test phase. Let the external timeout
bound failures to become ready. Wait for asynchronous results before returning
true; three settling frames alone do not prove arbitrary background work done.

Do not call `core.quit()` from the probe or print success markers yourself. The
driver reports BEGIN/PASS/COMPLETE with a fresh run ID, or FAIL on assertion or
cleanup failure. It quits after completion. Early quitting fails the run.

## Results and timing

The Python process returns 0 only for a passing test, 1 for a runtime failure,
and 2 for invalid arguments/setup. `result.json` records the run ID, command,
context, actor record, probe/runner/staged-script hashes, exit status, timeout,
markers, detected Lua errors and failure
reasons. Raw output and the engine log remain available even after failure.
Do not upload these machine-specific logs without reviewing them.

The example prints `OMW_TEST_METRIC|lua_update_ms|...` around a queued UI update,
and `OMW_TEST_METRIC|onFrame_interval_ms|...` for intervals between callbacks.
The first is Lua time; the second includes other engine work between frames.
Neither is isolated GPU time. Timing labels remain in raw logs so a test can
report its own workload-specific metrics without a mandatory schema.

The profile uses a hidden 1280x960 window, GUI scale 1.0, vsync enabled and no
sound. It is a real graphics session, not headless CI. Run standalone harness
tests without a game using `python -B scripts/test_run_probe.py`.

## Engine references

- [OpenMW 0.51 configuration paths, replacement and profile isolation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/modding/paths.html)
- [OpenMW 0.51 core clock and test shutdown](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html)
- [OpenMW 0.51 player onFrame handler](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/engine_handlers.html)
- [OpenMW 0.51 global world operations](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
- [OpenMW 0.51 local self and actor control](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_self.html)
- [OpenMW Lua UI lifecycle](https://openmw.readthedocs.io/en/stable/reference/lua-scripting/openmw_ui.html)

For another engine version, inspect its own documentation and installed CLI
options before adapting the runner. Revalidate the success and failure cases;
do not claim cross-version support from these reference links.
