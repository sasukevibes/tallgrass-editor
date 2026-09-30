// Linked maps: connections, doors both ways, O/B, play travel, world check, world export, rename.
const r = {};
// section 4 ran :pack classic, so this launch should start there
r.launchPack = state.pack; r.launchGrass = state.map.layers.ground.every(row => row.every(k => k === "grass")) && state.brush === "grass";
const edgeRow = (L, y, open) => { for (let x = 0; x < state.map.w; x++) state.map.layers.objects[y][x] = open.includes(x) ? null : L; };
// north map: 20 wide, gap in its bottom row of trees at x 10-11
await command("new 20x10"); edgeRow("tree", 9, [10, 11]); await command("w north-a");
// interior with a door
await command("new 10x8"); state.map.attrs[7][5] = "warp"; await command("w hut-a");
// south map: gap in its top row at x 4-5, so the paths line up at offset -6
await command("new 20x14"); edgeRow("tree", 0, [4, 5]);
r.connect = await command("connect north north-a");
r.autoOffset = state.map.links[0]?.offset;
moveTo(4, 0); await tap("BracketRight", "]"); r.nudged = state.map.links[0].offset;
await tap("BracketLeft", "["); r.back = state.map.links[0].offset;
moveTo(9, 9); r.warp = await command("warp! hut-a");
r.save = await command("w south-a");
const n = await host.readMap("north-a"), h = await host.readMap("hut-a"), me = await host.readMap("south-a");
r.northLinks = n.connections; r.hutWarps = h.warps; r.ownLinks = me.connections; r.ownWarp = me.warps["9,9"];

// O through the edge and the door, B back
moveTo(4, 0); await followLink(); r.overEdge = [state.name, state.cx, state.cy];
await goBack(); r.backFromEdge = [state.name, state.cx, state.cy];
moveTo(9, 9); await followLink(); r.throughDoor = [state.name, state.cx, state.cy];
await goBack(); r.backFromDoor = [state.name];

// play: walk north across the seam, then back south and in through the door
moveTo(4, 1); startPlay();
// The hidden test window throttles timers, so finish each step by hand.
const walk = async (code, k) => { key(code, k); key(code, k, "keyup"); updatePlay(performance.now() + 1000); await sleep(30); };
await until(() => WORLD.has("north-a"));
await walk("KeyW", "w"); await walk("KeyW", "w");
r.playNorth = [state.play.name, state.play.x, state.play.y];
await walk("KeyS", "s"); await walk("KeyS", "s");
r.playSouth = [state.play.name, state.play.x, state.play.y];
state.play.x = state.play.fx = 9; state.play.y = state.play.fy = 10; // stand under the door
await walk("KeyW", "w"); await until(() => state.play.name === "hut-a", 3000);
r.playDoor = [state.play.name, state.play.x, state.play.y];
await tap("Escape", "Escape");
r.stopMsg = document.querySelector("#msg").textContent; r.editing = state.name;

// world: layout and problems
state.map.warps["1,1"] = "nowhere 2,2"; state.map.attrs[1][1] = "warp";
const W = await checkWorld();
r.pos = Object.fromEntries(W.pos); r.problems = W.problems; r.warpCount = W.warps.length; r.linkCount = W.links.length;
await command("world"); r.worldOpen = !document.querySelector("#world").hidden; r.worldNames = WV.names;
await tap("Tab", "Tab"); r.worldSel = WV.names[WV.sel]; key("Escape", "Escape"); r.worldClosed = document.querySelector("#world").hidden;
delete state.map.warps["1,1"]; state.map.attrs[1][1] = "auto";
await command("w");

r.exportMsg = await command("export world " + window.TALLGRASS_TEST_EXPORT_DIR);
r.renameMsg = await command("rename south-b");
r.afterRename = { north: (await host.readMap("north-a")).connections, hut: (await host.readMap("hut-a")).warps, list: await host.listMaps() };
return JSON.stringify(r);
