// Sprite packs: the built-in Classic pack, :pack listing, completion and errors.
const r = {};
r.packs = Object.keys(PACKS);
await tap("Enter", "Enter");
const c = document.querySelector("#cmd"); c.value = "pack cl"; c.value = complete(c.value); r.completion = c.value.trim(); closeCmd();
r.listMsg = await command("pack");
r.unknownMsg = await command("pack nope");
r.switchMsg = await command("pack classic");
r.pack = state.pack;
r.sprites = ["down", "up", "left", "right"].map(d => !!PK().sprites[d]);
return JSON.stringify(r);
