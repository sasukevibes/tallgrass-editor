// Relaunch: still a fresh grass field, :ls lists the file, :e loads it back, :restore works.
const r = {};
r.freshAllGrass = state.map.layers.ground.every(row => row.every(k => k === "grass"));
r.ls = await command("ls");
r.open = await command("e keytest");
r.name = state.name;
r.row = state.map.layers.ground[14].slice(20, 25);
r.restore = await command("restore");
r.restoredName = state.name;
return JSON.stringify(r);
