local REC = {}
local cur = "?"
local noop = function() end
setmetatable(_G, { __index = function(t, k) return noop end })
SetClassProperty = function(c, p, v) table.insert(REC, cur .. "\t" .. tostring(c) .. "\t" .. tostring(p) .. "\t" .. tostring(v)) end
ReadDataFile = function(...) local s = "" for i = 1, table.getn(arg) do s = s .. tostring(arg[i]) .. ";" end table.insert(REC, cur .. "\tREAD\t" .. s .. "\t") end
ScriptCB_IsFileExist = function() return tonumber(arg[4]) end
uf_changeClassProperties = function(classes, props)
	for _, c in ipairs(classes or {}) do for _, p in ipairs(props or {}) do SetClassProperty(c, p.name, p.value) end end
end
print = function() end
local f = assert(loadfile(arg[1]))
f()
for line in io.lines(arg[2]) do
	cur = line
	local ok, e = pcall(ChangeSkin, line)
	if not ok then table.insert(REC, cur .. "\tERROR\t" .. tostring(e) .. "\t") end
end
local out = io.open(arg[3], "w")
for _, r in ipairs(REC) do out:write(r, "\n") end
out:close()
