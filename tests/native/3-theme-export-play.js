// Theme live reload, :export to disk, play mode collision and ledges.
const r = {};
r.panelBefore = cssVar("--panel");
r.modeColorBefore = MODES.normal.color;
window.__themeReady = true; // the runner swaps the theme directory after seeing the marker file
await host.setSession("session", JSON.stringify({ marker: "swap-now" }));
r.panelAfter = await until(() => { const v = cssVar("--panel"); return v !== r.panelBefore ? v : null; }, 8000);
r.modeColorAfter = MODES.normal.color;
r.canvasBg = CANVAS.bg;

await command("gen 30x20 7");
r.exportMsg = await command("export " + window.TALLGRASS_TEST_EXPORT_DIR);
r.exportDialogOpen = !document.querySelector("#export").hidden;
key("Escape", "Escape"); await sleep(50);

// Play mode on a blank map: tree to the right blocks, a ledge below hops down two.
await command("new 12x10");
state.map.layers.objects[5][7] = "tree";
state.map.layers.ground[6][6] = "ledge";
moveTo(6, 5);
// The test window is unmapped, so animation frames may not tick; drive play time ourselves.
setInterval(() => updatePlay(performance.now()), 16);
await tap("KeyP", "p");
r.playing = !!state.play;
const walk = async (code, k) => { key(code, k); key(code, k, "keyup"); await sleep(450); }; // one tap, one step
await walk("KeyD", "d"); r.afterTree = [state.play.x, state.play.y];
await walk("KeyS", "s"); r.afterLedge = [state.play.x, state.play.y];
await walk("KeyW", "w"); r.afterUp = [state.play.x, state.play.y];
await tap("Escape", "Escape");
r.stopped = !state.play;
return JSON.stringify(r);
