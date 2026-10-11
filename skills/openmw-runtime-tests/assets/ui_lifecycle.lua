-- Dependency-free example: real Lua UI creation, reflow and destruction.
local core = require('openmw.core')
local ui = require('openmw.ui')
local util = require('openmw.util')
local self = require('openmw.self')
local root, frame, lastAt = nil, 0, nil

local function children(count)
    local layouts = {}
    for i = 1, count do
        layouts[i] = {type = ui.TYPE.Widget, props = {
            position = util.vector2((i - 1) * 12, 0), size = util.vector2(10, 10)}}
    end
    return ui.content(layouts)
end

local function cleanup()
    if root and root.layout then root:destroy() end
end

return {
    cleanup = cleanup,
    step = function()
        frame = frame + 1
        local now = core.getRealTime()
        if lastAt then
            print(string.format('OMW_TEST_METRIC|onFrame_interval_ms|%.3f', (now - lastAt) * 1000))
        end
        lastAt = now
        if frame == 1 then
            assert(self.cell, 'player did not enter the start cell')
            print('OMW_TEST_INFO|cell|' .. self.cell.name)
            root = ui.create {layer = 'Windows', type = ui.TYPE.Widget,
                props = {position = util.vector2(30, 30), size = util.vector2(240, 80)}, content = children(10)}
        elseif frame == 3 then
            assert(root.layout and #root.layout.content == 10, 'initial content missing')
            local began = core.getRealTime()
            root.layout.props.size = util.vector2(480, 120)
            root.layout.content = children(30)
            root:update()
            print(string.format('OMW_TEST_METRIC|lua_update_ms|%.3f', (core.getRealTime() - began) * 1000))
        elseif frame == 6 then
            assert(root.layout.props.size.x == 480 and #root.layout.content == 30, 'updated layout missing')
            cleanup()
        elseif frame == 8 then
            assert(root.layout == nil, 'destroyed Element still has a layout')
            return true
        end
    end,
}
