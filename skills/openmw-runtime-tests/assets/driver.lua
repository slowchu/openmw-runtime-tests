---@omw-context player
-- The runner stages this script; keep it out of distributed game mods.
local core = require('openmw.core')
local self = require('openmw.self')
local runId = '__RUN_ID__'
local case, started, finished, settled = nil, false, false, 0

local function mark(event, detail)
    print('OMW_TEST|' .. runId .. '|' .. event .. '|' .. (detail or ''))
end

local function cleanup()
    if case and case.cleanup then case.cleanup() end
end

local function frame()
    if not started then
        -- onFrame can run before the new game's player enters its start cell.
        if not self.cell then return end
        started = true
        mark('BEGIN', 'API_REVISION=' .. tostring(core.API_REVISION))
        case = require('scripts.omw_runtime_test.case')
        assert(type(case) == 'table' and type(case.step) == 'function', 'probe must return a table with step()')
        assert(case.cleanup == nil or type(case.cleanup) == 'function', 'cleanup must be a function')
    end
    if finished then
        settled = settled + 1
        if settled == 3 then
            mark('PASS')
            mark('COMPLETE')
            core.quit()
        end
    elseif case.step() == true then
        cleanup()
        finished = true
    end
end

local stopped = false
return {engineHandlers = {onFrame = function()
    if stopped then return end
    local ok, err = pcall(frame)
    if not ok then
        stopped = true
        mark('FAIL', tostring(err))
        local cleaned, cleanupError = pcall(cleanup)
        if not cleaned then mark('FAIL', 'cleanup: ' .. tostring(cleanupError)) end
        core.quit()
    elseif finished and settled == 3 then
        stopped = true
    end
end}}
