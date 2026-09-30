// Plain-browser check: the same src/tallgrass.html with no native shell.
// Real Playwright keyboard input into headless Chromium; storage is localStorage
// and :export falls back to downloads.
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const exe = process.env.CHROMIUM || "/usr/bin/chromium";
const url = pathToFileURL(resolve(import.meta.dirname, "../src/tallgrass.html")).href;
let fail = 0;
const ok = (label, cond, extra = "") => { console.log(`  ${cond ? "ok  " : "FAIL"}  ${label}${cond ? "" : "  " + extra}`); if (!cond) fail = 1; };

const browser = await chromium.launch({ executablePath: exe, headless: true });
const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 860 } });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", e => errors.push(e.message));
await page.goto(url);
await page.waitForFunction(() => typeof state !== "undefined" && state.map);
await page.click("#map", { position: { x: 5, y: 5 } }); // focus the page like a person would
await page.evaluate(() => { state.cx = 20; state.cy = 14; }); // the click moved the cursor

const cmd = async line => { await page.keyboard.press("Enter"); await page.keyboard.type(line); await page.keyboard.press("Enter"); await page.waitForTimeout(150); return page.textContent("#msg"); };

console.log("browser: " + url);
ok("uses the browser host", await page.evaluate(() => host.native === false));
ok("new map is all grass", await page.evaluate(() => state.map.w === 40 && state.map.h === 28 && state.map.layers.ground.every(r => r.every(k => k === "grass"))));
await page.keyboard.press("e"); await page.keyboard.press("e");
await page.keyboard.down("Space");
for (let i = 0; i < 4; i++) await page.keyboard.press("d");
await page.keyboard.up("Space");
ok("hold Space + D paints", await page.evaluate(() => state.map.layers.ground[14].slice(20, 25).every(k => k === "tall_grass")));
ok(":w saves in this browser", (await cmd("w webtest")).includes("in this browser"));

await page.reload();
await page.waitForFunction(() => typeof state !== "undefined" && state.map);
await page.click("#map", { position: { x: 5, y: 5 } });
ok("reload starts fresh", await page.evaluate(() => state.map.layers.ground[14][20] === "grass"));
await page.keyboard.press("Enter"); await page.keyboard.type("e web"); await page.keyboard.press("Tab");
ok("Tab completes saved names", (await page.inputValue("#cmd")).trim() === "e webtest");
await page.keyboard.press("Enter"); await page.waitForTimeout(150);
ok(":e webtest loads it", await page.evaluate(() => state.name === "webtest" && state.map.layers.ground[14][22] === "tall_grass"));
ok(":restore works", (await cmd("restore")).includes("Restored"));

const downloads = [];
page.on("download", d => downloads.push(d.suggestedFilename()));
await cmd("gen 30x20 7");
await cmd("export");
await page.waitForTimeout(800);
ok(":export downloads three files", downloads.length === 3 && downloads.some(n => n.endsWith("-tiles.png")), JSON.stringify(downloads));
ok("export dialog shows the loader", (await page.textContent("#exCode")).includes("export async function loadMap"));
await page.keyboard.press("Escape");

await cmd("new 12x10");
await page.evaluate(() => { state.map.layers.objects[5][7] = "tree"; state.map.layers.ground[6][6] = "ledge"; moveTo(6, 5); });
await page.keyboard.press("p");
await page.keyboard.press("d"); await page.waitForTimeout(250);
const t = await page.evaluate(() => [state.play.x, state.play.y]);
await page.keyboard.press("s"); await page.waitForTimeout(450);
const l = await page.evaluate(() => [state.play.x, state.play.y]);
ok("play: tree blocks, ledge hops", JSON.stringify(t) === "[6,5]" && JSON.stringify(l) === "[6,7]", JSON.stringify([t, l]));
await page.keyboard.press("Escape");
ok(":pack lists the Classic pack", (await cmd("pack")).includes("classic (Classic)"));
await cmd("gen 36x24 11");
ok("route generates", await page.evaluate(() => state.map.layers.ground.flat().includes("path")));
await cmd("new 20x10"); await cmd("w br-north");
await cmd("new 20x10"); await cmd("connect north br-north"); await cmd("w br-south");
ok("links sync in browser storage", await page.evaluate(() => JSON.parse(localStorage.getItem("tallgrass.maps"))["br-north"].connections?.[0]?.map === "br-south"));
await cmd("world");
ok(":world opens in the browser", await page.evaluate(() => !document.querySelector("#world").hidden && WV.names.includes("br-north")));
await page.keyboard.press("Escape");
await page.keyboard.press("Enter"); await page.keyboard.type("co");
ok("command hints appear while typing", await page.evaluate(() => !document.querySelector("#cmdHints").hidden && document.querySelector("#cmdHints").textContent.includes("connect")));
await page.keyboard.press("Escape");
await page.click("#tutBtn"); await page.keyboard.press("Enter"); await page.waitForTimeout(100);
ok("Tutorial button starts the lesson, Enter advances it", await page.evaluate(() => !document.querySelector("#coach").hidden && TUT.i === 1));
await page.keyboard.press("Escape"); await page.click("#coachX");
ok("no page errors", errors.length === 0, errors.join("; "));

await browser.close();
console.log(fail ? "\nbrowser: FAILURES" : "\nbrowser: all passed");
process.exit(fail);
