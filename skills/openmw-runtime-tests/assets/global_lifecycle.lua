---@omw-context global
-- Real global-only world operations; wait for queued placement/removal.
local world = require('openmw.world')
local util = require('openmw.util')
local object, placed, removing = nil, false, false

local function cleanup()
    if object and object:isValid() and object.count > 0 then object:remove() end
end

return {
    cleanup = cleanup,
    step = function()
        local player = world.players[1]
        assert(player and player.cell, 'global probe cannot see the player cell')
        if not object then
            object = world.createObject('gold_001', 3)
            object:teleport(player.cell, player.position + util.vector3(64, 0, 0))
        elseif not placed then
            if not object.cell then return end
            assert(object.cell.id == player.cell.id and object.count == 3, 'spawned object mismatch')
            assert(object.recordId == 'gold_001', 'wrong record instantiated')
            print('OMW_TEST_INFO|global_object_placed|' .. object.id)
            placed = true
            cleanup()
            removing = true
        elseif removing and (not object:isValid() or object.count == 0) then
            print('OMW_TEST_INFO|global_object_removed')
            return true
        end
    end,
}
