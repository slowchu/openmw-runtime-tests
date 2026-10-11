---@omw-context local
-- Run with --context actor --actor-record rat (or an NPC record).
local self = require('openmw.self')
local types = require('openmw.types')
local health, original, target, restoring = nil, nil, nil, false

local function cleanup()
    if health then health.current = original end
end

return {
    cleanup = cleanup,
    step = function()
        assert(self:isActive() and self.cell, 'actor probe is not active in a cell')
        assert(types.Actor.objectIsInstance(self) and not types.Player.objectIsInstance(self),
            'probe must run on a non-player actor')
        if not health then
            self:enableAI(false)
            health = types.Actor.stats.dynamic.health(self)
            original = health.current
            assert(original > 0, 'test actor has no health')
            target = original * 0.5
            health.current = target
            print('OMW_TEST_INFO|actor_stat_write|' .. self.recordId)
        elseif not restoring then
            if math.abs(health.current - target) > 0.001 then return end
            cleanup()
            restoring = true
        elseif math.abs(health.current - original) < 0.001 then
            print('OMW_TEST_INFO|actor_stat_restored')
            return true
        end
    end,
}
