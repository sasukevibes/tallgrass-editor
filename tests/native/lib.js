// Shared helpers, prepended to each native probe. Probes run inside the page
// through TALLGRASS_TEST_JS and return a JSON string.
const sleep = ms => new Promise(r => setTimeout(r, ms));
const key = (code, k = "", type = "keydown", extra = {}) =>
  window.dispatchEvent(new KeyboardEvent(type, { code, key: k, bubbles: true, cancelable: true, ...extra }));
const tap = async (code, k, extra) => { key(code, k, "keydown", extra); key(code, k, "keyup", extra); await sleep(20); };
async function command(line) {
  // Open the bar the way a person does (Enter), type, and press Enter in the input.
  await tap("Enter", "Enter");
  const c = document.querySelector("#cmd");
  c.value = line;
  c.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true, cancelable: true }));
  await lastCommand; await sleep(20);
  return document.querySelector("#msg").textContent;
}
async function until(fn, ms = 5000) { const t = Date.now(); while (Date.now() - t < ms) { const v = await fn(); if (v) return v; await sleep(50); } return null; }
const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
