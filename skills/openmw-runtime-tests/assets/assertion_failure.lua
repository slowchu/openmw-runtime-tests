-- Negative control: the runner must return failure even when OpenMW exits 0.
return {step = function()
    assert(false, 'intentional assertion failure: negative control')
end}
