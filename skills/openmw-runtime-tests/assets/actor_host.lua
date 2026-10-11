---@omw-context global
-- Owns only the new test actor; existing actors are never selected or removed.
local core = require('openmw.core')
local world = require('openmw.world')
local types = require('openmw.types')
local util = require('openmw.util')
local runId = '__RUN_ID__'
local recordId = __ACTOR_RECORD__
local actorEvent = 'OMW_TEST_ACTOR_' .. runId
local actor, actorId, begun, removing, stopped, settled = nil, nil, false, false, false, 0

local function mark(event, detail)
    print('OMW_TEST|' .. runId .. '|' .. event .. '|' .. (detail or ''))
end

local function removeActor()
    if actor and actor:isValid() and actor.count > 0 then actor:remove() end
end

local function fail(err)
    if not begun then
        begun = true
        mark('BEGIN', 'CONTEXT=actor|API_REVISION=' .. tostring(core.API_REVISION))
    end
    mark('FAIL', tostring(err))
    local ok, cleanupError = pcall(removeActor)
    if not ok then mark('FAIL', 'actor cleanup: ' .. tostring(cleanupError)) end
    stopped = true
    core.quit()
end

local function update()
    if not actor then
        local player = world.players[1]
        if not player or not player.cell then return end
        actor = world.createObject(recordId)
        actorId = actor.id
        assert(types.Actor.objectIsInstance(actor) and not types.Player.objectIsInstance(actor),
            '--actor-record must identify an NPC or creature')
        actor:addScript('scripts/omw_runtime_test/driver.lua')
        actor:teleport(player.cell, player.position + util.vector3(128, 0, 0))
        print('OMW_TEST_INFO|actor_spawned|' .. actorId .. '|' .. recordId)
    elseif removing then
        settled = settled + 1
        if settled == 3 then
            -- Removed references can remain valid; count zero marks deletion.
            assert(not actor:isValid() or actor.count == 0, 'test actor still exists after removal')
            for _, active in ipairs(world.activeActors) do
                assert(active.id ~= actorId, 'test actor is still active after removal')
            end
            print('OMW_TEST_INFO|actor_removed|' .. actorId)
            mark('PASS')
            mark('COMPLETE')
            stopped = true
            core.quit()
        end
    elseif not actor:isValid() or actor.count == 0 then
        error('test actor disappeared before completion')
    end
end

local function receive(data)
    if data.actorId ~= actorId then return end
    if data.event == 'BEGIN' then
        assert(not begun and not removing, 'duplicate actor BEGIN')
        begun = true
        mark('BEGIN', data.detail)
        actor:sendEvent(actorEvent .. '_ACK', {actorId = actorId})
    elseif data.event == 'DONE' then
        assert(begun and not removing, 'unexpected actor completion')
        removeActor()
        removing = true
    elseif data.event == 'FAIL' then
        fail(data.detail)
    else
        error('unexpected actor status: ' .. tostring(data.event))
    end
end

local function guarded(fn, arg)
    if stopped then return end
    local ok, err = pcall(fn, arg)
    if not ok then fail(err) end
end

return {
    engineHandlers = {onUpdate = function() guarded(update) end},
    eventHandlers = {[actorEvent] = function(data) guarded(receive, data) end},
}
