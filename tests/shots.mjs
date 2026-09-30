// Screenshots of the command bar hints and the lesson card, for eyeballing changes.
//   node tests/shots.mjs [outdir]
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
const out = process.argv[2] || ".";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || "/usr/bin/chromium", headless: true });
const page = await (await browser.newContext({ viewport: { width: 1280, height: 820 } })).newPage();
await page.goto(pathToFileURL(resolve(import.meta.dirname, "../src/tallgrass.html")).href);
await page.waitForFunction(() => typeof state !== "undefined" && state.map);
await page.click("#map", { position: { x: 5, y: 5 } });
await page.screenshot({ path: `${out}/launch.png` });
await page.keyboard.press("Enter"); await page.waitForTimeout(100);
await page.screenshot({ path: `${out}/hints-empty.png` });
await page.keyboard.type("co"); await page.waitForTimeout(100);
await page.screenshot({ path: `${out}/hints-co.png` });
await page.keyboard.type("nnect "); await page.waitForTimeout(100);
await page.screenshot({ path: `${out}/hints-connect.png` });
await page.keyboard.press("Escape");
await page.keyboard.press("Enter"); await page.keyboard.type("tutorial"); await page.keyboard.press("Enter"); await page.waitForTimeout(150);
await page.screenshot({ path: `${out}/lesson-1.png` });
await browser.close();
