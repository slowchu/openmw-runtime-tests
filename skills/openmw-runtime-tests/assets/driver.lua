-- The runner stages this script; keep it out of distributed game mods.
local core = require('openmw.core')
local context = '__CONTEXT__'
local world = context == 'global' and require('openmw.world') or nil
local self = context ~= 'global' and require('openmw.self') or nil
local runId = '__RUN_ID__'
local case, started, finished, settled = nil, false, false, 0
local acknowledged = false
local actorEvent = 'OMW_TEST_ACTOR_' .. runId

local function mark(event, detail)
    if context == 'actor' then
        core.sendGlobalEvent(actorEvent, {actorId = self.id, event = event, detail = detail})
    else
        print('OMW_TEST|' .. runId .. '|' .. event .. '|' .. (detail or ''))
    end
end

local function cleanup()
    if case and case.cleanup then case.cleanup() end
end

local function frame(dt)
    if not started then
        -- Updates can run before the new game's starting cell is assigned.
        local object = world and world.players[1] or self
        if not object or not object.cell then return end
        if context == 'actor' and not self:isActive() then return end
        started = true
        mark('BEGIN', 'CONTEXT=' .. context .. '|API_REVISION=' .. tostring(core.API_REVISION))
    end
    -- A global-to-local acknowledgement proves the spawned script is reachable.
    if context == 'actor' and not acknowledged then return end
    if not case then
        case = require('scripts.omw_runtime_test.case')
        assert(type(case) == 'table' and type(case.step) == 'function', 'probe must return a table with step()')
        assert(case.cleanup == nil or type(case.cleanup) == 'function', 'cleanup must be a function')
    end
    if finished then
        settled = settled + 1
        if settled == 3 then
            if context == 'actor' then
                mark('DONE') -- Global host removes the actor before reporting success.
            else
                mark('PASS')
                mark('COMPLETE')
                core.quit()
            end
        end
    elseif case.step(dt) == true then
        cleanup()
        finished = true
    end
end

local stopped = false
local function update(dt)
    if stopped then return end
    local ok, err = pcall(frame, dt)
    if not ok then
        stopped = true
        mark('FAIL', tostring(err))
        local cleaned, cleanupError = pcall(cleanup)
        if not cleaned then mark('FAIL', 'cleanup: ' .. tostring(cleanupError)) end
        if context ~= 'actor' then core.quit() end
    elseif finished and settled == 3 then
        stopped = true
    end
end

return {
    engineHandlers = {[context == 'player' and 'onFrame' or 'onUpdate'] = update},
    eventHandlers = context == 'actor' and {[actorEvent .. '_ACK'] = function(data)
        if data.actorId == self.id then acknowledged = true end
    end} or {},
}
