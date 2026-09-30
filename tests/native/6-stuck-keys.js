// A held key whose release never arrives (an input method can swallow it) must not trap the editor.
const r = {};
selectBrush("tall_grass"); state.layer = "ground"; moveTo(5, 5);
// Space goes down, its release never arrives
key("Space", " "); r.modeAfterDown = state.mode;
await tap("KeyD", "d"); r.painted = state.map.layers.ground[5][6];
// Enter still opens the command bar
key("Enter", "Enter"); r.cmdOpen = !document.querySelector("#cmdwrap").hidden; r.modeAfterEnter = state.mode; closeCmd();
// stuck again, then a fresh Space press recovers instead of doing nothing
key("Space", " "); key("Space", " "); r.afterSecondPress = [state.mode, holdKey];
key("Space", " ", "keyup"); r.afterRelease = state.mode;
key("Space", " "); key("Enter", "Enter"); r.cmdOpen2 = !document.querySelector("#cmdwrap").hidden; closeCmd();
return JSON.stringify(r);
