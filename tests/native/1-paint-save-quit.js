// Fresh launch is all grass; paint with E E, hold Space + D x4; save with :w; quit with :q.
const r = {};
r.native = host.native;
r.freshAllGrass = state.map.w === 40 && state.map.h === 28 && state.map.layers.ground.every(row => row.every(k => k === "grass"));
r.brushAtStart = state.brush;
await tap("KeyE", "e"); await tap("KeyE", "e");
r.brush = state.brush;
const x0 = state.cx, y0 = state.cy;
key("Space", " ");
for (let i = 0; i < 4; i++) await tap("KeyD", "d");
key("Space", " ", "keyup");
r.painted = [0, 1, 2, 3, 4].map(i => state.map.layers.ground[y0][x0 + i]);
r.qRefusedWhenDirty = (await command("q")).startsWith("Unsaved changes");
r.saveMsg = await command("w keytest");
r.completion = (() => { const c = document.querySelector("#cmd"); openCmd("e key"); c.value = complete(c.value); const v = c.value; closeCmd(); return v; })();
// Leave a result for the runner, then quit through :q like a person would.
console.log("probe1", JSON.stringify(r));
window.__probe1 = r;
setTimeout(() => command("q"), 50);
return JSON.stringify(r);
