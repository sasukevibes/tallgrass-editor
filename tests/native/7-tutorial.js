// The command bar lesson from start to finish, plus the live hints.
const r = {}, cmdEl = document.querySelector("#cmd"), inCmd = (k, code = k) => cmdEl.dispatchEvent(new KeyboardEvent("keydown", { key: k, code, bubbles: true, cancelable: true }));
const step = () => TUT.i;
// hints
await tap("Enter", "Enter"); cmdEl.value = "co"; cmdEl.dispatchEvent(new Event("input"));
r.hintsShown = !document.querySelector("#cmdHints").hidden; r.hintsCo = document.querySelector("#cmdHints").textContent.includes("connect north map");
cmdEl.value = "connect "; cmdEl.dispatchEvent(new Event("input")); r.hintsDirs = ["north", "south", "east", "west"].every(d => [...document.querySelectorAll("#cmdHints .opts span")].some(s => s.textContent === d));
inCmd("Escape"); r.hintsHidden = document.querySelector("#cmdHints").hidden;

// a map with work in it, which the lesson must hand back
state.map.layers.ground[3][3] = "tall_grass"; markDirty(); const undoBefore = state.undo.length, nameBefore = state.name;
await command("tutorial"); r.started = TUT.on && !document.querySelector("#coach").hidden; r.steps = [step()];
await tap("Enter", "Enter"); r.steps.push(step());                         // open
inCmd("Escape"); r.steps.push(step());                                       // close
await command("new 20x14"); r.steps.push(step());                            // new
await tap("Enter", "Enter"); cmdEl.value = "ge"; inCmd("Tab"); r.completed = cmdEl.value; r.steps.push(step()); // Tab
cmdEl.value = "gen 20x14"; inCmd("Enter"); await lastCommand; r.steps.push(step()); // gen
await command("w tutorial-practice"); r.steps.push(step());                  // save
await tap("Enter", "Enter"); inCmd("ArrowUp"); r.history = cmdEl.value; inCmd("Escape"); r.steps.push(step()); // history
await command("ls"); r.steps.push(step());                                   // ls
await command("world"); key("Escape", "Escape"); r.steps.push(step());       // world
r.practiceSaved = (await host.listMaps()).includes("tutorial-practice");
await command("rm tutorial-practice"); r.steps.push(step());                 // rm
r.final = TUT.final && document.querySelector("#coachText").textContent.includes("That's the command bar");
r.mapBack = state.map.layers.ground[3][3] === "tall_grass" && state.map.w === 40 && state.name === nameBefore && state.dirty && state.undo.length === undoBefore;
r.practiceGone = !(await host.listMaps()).includes("tutorial-practice");
await tap("KeyD", "d"); r.cardClosedByKey = document.querySelector("#coach").hidden;
// quitting half way also hands the map back
await command("tutorial"); await command("new 10x10"); document.querySelector("#coachX").click();
r.quitMapBack = state.map.w === 40 && state.map.layers.ground[3][3] === "tall_grass" && !TUT.on;
r.seen = JSON.parse(await host.getSession("prefs") || "{}").tutorialSeen === true;
return JSON.stringify(r);
