#!/usr/bin/env python3
"""Tallgrass native shell for Omarchy.

A thin GTK4 + WebKitGTK 6 window around src/tallgrass.html. The editor stays
in the HTML; this file only gives it real files, native pickers, the Omarchy
theme and a command line.

  tallgrass [map.json]                       open the editor (optionally a map)
  tallgrass --export map.json [--out DIR]    write <name>.json, <name>-tiles.png
                                             and <name>.png without a window
  tallgrass --icon out.png [--size N]        render the Tall grass tile as an icon
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

VERSION = "1.0.0"
APP_ID = "tallgrass"  # Hyprland window class
HOME = Path.home()
HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get("TALLGRASS_SRC", HERE.parent / "src" / "tallgrass.html")).resolve()
STATE_DIR = Path(os.environ.get("TALLGRASS_STATE_DIR", Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state")) / "tallgrass"))
THEME_DIR = Path(os.environ.get("TALLGRASS_THEME_DIR", HOME / ".local/state/omarchy/current/theme"))
SESSION_KEYS = {"session", "previous", "prefs"}


def maps_dir() -> Path:
    if os.environ.get("TALLGRASS_MAPS_DIR"):
        return Path(os.environ["TALLGRASS_MAPS_DIR"]).expanduser()
    docs = HOME / "Documents"
    return docs / "tallgrass" if docs.is_dir() else HOME / "tallgrass"


def pretty(p: Path) -> str:
    """~/-relative path for messages."""
    p = Path(p)
    try:
        return "~/" + str(p.relative_to(HOME)) if p != HOME else "~"
    except ValueError:
        return str(p)


def write_atomic(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def data_url_bytes(url: str) -> bytes:
    head, _, body = url.partition(",")
    if not head.startswith("data:") or ";base64" not in head:
        raise ValueError("expected a base64 data URL")
    return base64.b64decode(body)


def valid_name(name: str) -> str:
    name = (name or "").strip()
    if not name or "/" in name or name.startswith("."):
        raise ValueError(f'"{name}" is not a valid map name')
    return name


# ------------------------------------------------------------------ settings
def load_settings() -> dict:
    try:
        return json.loads((STATE_DIR / "settings.json").read_text())
    except (OSError, ValueError):
        return {}


def save_settings(s: dict):
    write_atomic(STATE_DIR / "settings.json", (json.dumps(s, indent=2) + "\n").encode())


# ------------------------------------------------------------------ theme
def _hex(c):
    c = str(c or "").strip()
    if len(c) == 4 and c.startswith("#"):
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return c.lower() if len(c) == 7 and c.startswith("#") else None


def _mix(a, b, t):
    a, b = int(a[1:], 16), int(b[1:], 16)
    ch = [round(((a >> s) & 255) * (1 - t) + ((b >> s) & 255) * t) for s in (16, 8, 0)]
    return "#%02x%02x%02x" % tuple(ch)


def _lum(c):
    n = int(c[1:], 16)
    return (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255


def system_mono_font():
    try:
        out = subprocess.run(["fc-match", "monospace", "-f", "%{family}"], capture_output=True, text=True, timeout=2).stdout
        return out.split(",")[0].strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def read_theme():
    """Map the current Omarchy theme onto the editor's CSS variables.

    Returns None when colors.toml is missing or unreadable, so the editor keeps
    whatever colors it has (its own defaults on first launch)."""
    font = system_mono_font()
    base = {"vars": {"--mono": f'"{font}", ui-monospace, monospace'}} if font else None
    try:
        raw = tomllib.loads((THEME_DIR / "colors.toml").read_text())
    except (OSError, ValueError):
        return base

    def get(*keys):
        for k in keys:
            v = _hex(raw.get(k))
            if v:
                return v
        return None

    bg, fg = get("background", "bg", "color0"), get("foreground", "fg", "color7")
    if not bg or not fg:
        return base
    mode = str(raw.get("mode") or raw.get("theme_type") or "").lower()
    if mode not in ("light", "dark"):
        mode = "light" if (THEME_DIR / "light.mode").exists() or _lum(bg) > 0.5 else "dark"
    dark = mode == "dark"
    blue = get("blue", "color4") or fg
    accent = get("accent") or blue
    v = {
        "--panel": bg,
        "--ground": get("dark_background", "dark_bg") or _mix(bg, "#000000", 0.25 if dark else 0.05),
        "--canvas": get("darker_background", "darker_bg") or _mix(bg, "#000000", 0.5 if dark else 0.1),
        "--raised": _mix(bg, fg, 0.06),
        "--raised-2": _mix(bg, fg, 0.10),
        "--line": _mix(bg, fg, 0.14),
        "--text": fg,
        "--dim": _mix(fg, bg, 0.35),
        "--faint": _mix(fg, bg, 0.6),
        "--normal": accent,
        "--insert": get("green", "color2") or accent,
        "--erase": get("red", "color1") or accent,
        "--visual": get("magenta", "purple", "color5") or accent,
        "--command": get("yellow", "color3") or accent,
        "--play": get("cyan", "color6") or accent,
    }
    if font:
        v["--mono"] = f'"{font}", ui-monospace, monospace'
    ink_dark, ink_light = (bg, fg) if _lum(bg) < _lum(fg) else (fg, bg)
    return {"vars": v, "scheme": mode, "inks": {"dark": ink_dark, "light": ink_light}}


# ------------------------------------------------------------------ headless fallback
CHROMIUM_SHIM = """<script>
(() => {
  const out = {};
  const reply = v => Promise.resolve(JSON.stringify({ value: v }));
  window.webkit = { messageHandlers: { tallgrass: { postMessage(s) {
    const m = JSON.parse(s);
    if (m.op === "exportFiles") { (out.files ||= []).push({ name: m.name, json: m.json, atlas: m.atlas, map: m.map }); return reply({ where: "" }); }
    if (m.op === "resolveExport") return reply({ dir: (m.dest || {}).dir || "", where: "" });
    if (m.op === "exportText") { (out.texts ||= []).push({ name: m.name, text: m.text }); return reply(true); }
    if (m.op === "jobDone") { out.done = m; const pre = document.createElement("pre"); pre.id = "tallgrass-result"; pre.textContent = btoa(unescape(encodeURIComponent(JSON.stringify(out)))); document.body.appendChild(pre); return reply(null); }
    return reply(null);
  } } } };
})();
</script>"""


def export_with_chromium(job: dict):
    """Run the export job in headless Chromium when there is no display for GTK."""
    exe = next((p for p in ("chromium", "google-chrome-stable", "chrome") if subprocess.run(["which", p], capture_output=True).returncode == 0), None)
    if not exe:
        raise RuntimeError("no display for WebKit and no Chromium for a headless export")
    html = SRC.read_text()
    cfg = "<script>window.TALLGRASS_HOST = " + json.dumps({"mapsDir": "", "job": job}).replace("</", "<\\/") + ";</script>"
    html = html.replace("<script>\n\"use strict\";", CHROMIUM_SHIM + cfg + "<script>\n\"use strict\";", 1)
    with tempfile.TemporaryDirectory(prefix="tallgrass-") as tmp:
        page = Path(tmp) / "job.html"
        page.write_text(html)
        for d in ("packs", "fonts"):  # the page loads these relative to itself
            if (SRC.parent / d).is_dir():
                (Path(tmp) / d).symlink_to(SRC.parent / d)
        dom = subprocess.run([exe, "--headless", "--disable-gpu", "--no-sandbox", f"--user-data-dir={tmp}/profile",
                              "--virtual-time-budget=20000", "--dump-dom", page.as_uri()],
                             capture_output=True, text=True, timeout=120).stdout
    start = dom.find('<pre id="tallgrass-result">')
    if start < 0:
        raise RuntimeError("headless Chromium did not finish the export")
    body = dom[start:].split(">", 1)[1].split("</pre>", 1)[0]
    res = json.loads(base64.b64decode(body).decode())
    done = res.get("done") or {}
    if not done.get("ok"):
        raise RuntimeError(done.get("error") or "export failed")
    return done, res.get("files", []), res.get("texts", [])


def write_export(dest: Path, name: str, json_text: str, atlas: str, map_png: str) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    write_atomic(dest / f"{name}.json", json_text.encode())
    write_atomic(dest / f"{name}-tiles.png", data_url_bytes(atlas))
    write_atomic(dest / f"{name}.png", data_url_bytes(map_png))
    return dest


# ------------------------------------------------------------------ GTK app
def run_gui(open_path=None, job=None):
    # Keys go straight to the editor instead of through an input method (fcitx5
    # on Omarchy), which can swallow the release of a held Space and leave the
    # editor stuck painting. Set GTK_IM_MODULE yourself to override.
    os.environ.setdefault("GTK_IM_MODULE", "gtk-im-context-simple")
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("WebKit", "6.0")
    gi.require_version("JavaScriptCore", "6.0")
    from gi.repository import Gdk, Gio, GLib, Gtk, JavaScriptCore, WebKit

    GLib.set_prgname(APP_ID)  # becomes the Wayland app_id, so Hyprland sees class "tallgrass"
    GLib.set_application_name("Tallgrass")

    class Shell:
        def __init__(self, app):
            self.app, self.job, self.result = app, job, None
            self.result_files, self.result_texts = [], []
            self.closing = False
            self.theme_timer = 0
            self.monitors = []
            self.mdir = maps_dir()
            cfg = {"mapsDir": pretty(self.mdir), "theme": read_theme(), "job": job, "openPath": open_path}

            ucm = WebKit.UserContentManager()
            ucm.register_script_message_handler_with_reply("tallgrass", None)
            ucm.connect("script-message-with-reply-received::tallgrass", self.on_message)
            ucm.add_script(WebKit.UserScript.new(
                "window.TALLGRASS_HOST = " + json.dumps(cfg) + ";",
                WebKit.UserContentInjectedFrames.TOP_FRAME, WebKit.UserScriptInjectionTime.START, None, None))

            self.view = WebKit.WebView(user_content_manager=ucm)
            s = self.view.get_settings()
            s.set_allow_file_access_from_file_urls(True)
            s.set_enable_developer_extras(bool(os.environ.get("TALLGRASS_DEBUG")))
            s.set_enable_back_forward_navigation_gestures(False)
            self.view.connect("decide-policy", self.on_policy)
            self.view.connect("context-menu", self.on_context_menu)
            self.view.connect("load-changed", self.on_load)
            self.view.connect("notify::title", lambda v, _p: self.win.set_title(v.get_title() or "Tallgrass"))

            self.win = Gtk.ApplicationWindow(application=app, title="Tallgrass", default_width=1400, default_height=900)
            self.win.set_child(self.view)
            self.win.connect("close-request", self.on_close)
            self.uri = SRC.as_uri()
            self.view.load_uri(self.uri)
            if not job:
                if not os.environ.get("TALLGRASS_TEST_JS"):  # tests stay unmapped so they never take focus
                    self.win.present()
                    self.view.grab_focus()
                self.watch_theme()

        # ---- plumbing
        def on_policy(self, view, decision, kind):
            if kind == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
                uri = decision.get_navigation_action().get_request().get_uri()
                if uri.split("#")[0] != self.uri:
                    decision.ignore()
                    return True
            return False

        def on_context_menu(self, view, menu, hit):
            return not (os.environ.get("TALLGRASS_DEBUG") or hit.context_is_editable() or hit.context_is_selection())

        def on_load(self, view, event):
            if event == WebKit.LoadEvent.FINISHED and os.environ.get("TALLGRASS_TEST_JS") and not self.job:
                GLib.timeout_add(300, self.run_test_js)

        def run_test_js(self):
            """Dev hook: run a JS file in the page, print its JSON result, quit."""
            body = Path(os.environ["TALLGRASS_TEST_JS"]).read_text()

            def done(view, res):
                try:
                    print(view.call_async_javascript_function_finish(res).to_string(), flush=True)
                except GLib.Error as e:
                    print(json.dumps({"testError": e.message}), flush=True)
                if not os.environ.get("TALLGRASS_TEST_NOQUIT"):  # else the page quits itself (:q)
                    self.closing = True
                    self.app.quit()
            self.view.call_async_javascript_function(body, -1, None, None, None, None, done)
            return False

        def js(self, code):
            self.view.evaluate_javascript(code, -1, None, None, None, None, None)

        def on_close(self, win):
            if self.closing:
                return False
            self.closing = True

            def finish(*_):
                if self.closing is True:
                    self.closing = "done"
                    self.win.destroy()
                return False
            self.view.call_async_javascript_function("return await window.tallgrassFlush()", -1, None, None, None, None, finish)
            GLib.timeout_add(1500, finish)
            return True

        # ---- theme
        def watch_theme(self):
            for m in self.monitors:
                m.cancel()
            self.monitors = []
            for d in (THEME_DIR.parent, THEME_DIR):
                try:
                    m = Gio.File.new_for_path(str(d)).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
                    m.connect("changed", self.on_theme_event)
                    self.monitors.append(m)
                except GLib.Error:
                    pass

        def on_theme_event(self, *_):
            if self.theme_timer:
                GLib.source_remove(self.theme_timer)
            self.theme_timer = GLib.timeout_add(250, self.reload_theme)

        def reload_theme(self):
            self.theme_timer = 0
            theme = read_theme()
            if theme and len(theme.get("vars", {})) > 1:
                self.js(f"window.tallgrassTheme({json.dumps(theme)})")
            self.watch_theme()  # omarchy-theme-set replaces the directory, so watch the new one
            return False

        # ---- bridge
        def on_message(self, ucm, value, reply):
            ctx = value.get_context()

            def answer(val=None, error=None):
                out = {"error": error} if error else {"value": val}
                reply.return_value(JavaScriptCore.Value.new_string(ctx, json.dumps(out)))

            try:
                req = json.loads(value.to_string())
                op = req.pop("op")
                fn = getattr(self, "op_" + op, None)
                if not fn:
                    answer(error=f"unknown host call {op}")
                elif op in ("pick", "exportFiles", "resolveExport"):
                    fn(req, answer)  # async, answers later
                else:
                    answer(fn(**req))
            except Exception as e:  # report to the page, never crash the window
                answer(error=str(e))
            return True

        def map_path(self, name):
            if "/" in name or name.startswith("~"):
                return Path(name).expanduser()
            return self.mdir / f"{valid_name(name)}.json"

        def op_listMaps(self):
            if not self.mdir.is_dir():
                return []
            return sorted(p.stem for p in self.mdir.glob("*.json") if not p.name.startswith("."))

        def op_readMap(self, name):
            p = self.map_path(name)
            if not p.exists():
                if "/" in name or name.startswith("~"):
                    raise FileNotFoundError(f"No file at {pretty(p)}")
                return None
            return json.loads(p.read_text())

        def op_writeMap(self, name, text):
            p = self.map_path(valid_name(name))
            write_atomic(p, text.encode())
            return {"where": f"to {pretty(p)}"}

        def op_removeMap(self, name):
            p = self.map_path(valid_name(name))
            if not p.exists():
                return False
            try:
                Gio.File.new_for_path(str(p)).trash(None)
            except GLib.Error:
                p.unlink()
            return True

        def op_getSession(self, key):
            if key not in SESSION_KEYS:
                raise ValueError("bad session key")
            try:
                return (STATE_DIR / f"{key}.json").read_text()
            except OSError:
                return None

        def op_setSession(self, key, text):
            if key not in SESSION_KEYS:
                raise ValueError("bad session key")
            write_atomic(STATE_DIR / f"{key}.json", text.encode())
            return True

        def op_copy(self, text):
            provider = Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8", GLib.Bytes.new(text.encode()))
            self.win.get_clipboard().set_content(provider)
            return True

        def op_quit(self):
            self.closing = "done"
            GLib.idle_add(self.app.quit)
            return True

        def op_jobDone(self, **r):
            self.result = r
            GLib.idle_add(self.app.quit)
            return True

        def resolve_dest(self, key, dest, done):
            """Find the export folder: picked, given, remembered for `key`, or the default.
            Calls done(folder, remember) or done(None) when the picker is cancelled."""
            dirs = load_settings().get("exportDirs", {})
            if dest.get("pick"):
                dialog = Gtk.FileDialog(title=f"Export {key} to folder", modal=True)
                start = Path(dirs.get(key) or self.mdir)
                if start.is_dir():
                    dialog.set_initial_folder(Gio.File.new_for_path(str(start)))

                def picked(d, res):
                    try:
                        f = d.select_folder_finish(res)
                    except GLib.Error:
                        return done(None, False)
                    done(Path(f.get_path()), True)
                dialog.select_folder(self.win, None, picked)
            elif dest.get("dir"):
                done(Path(dest["dir"]).expanduser().resolve(), True)
            else:
                done(Path(dirs.get(key) or self.mdir / "export"), False)

        def remember_dest(self, key, folder):
            settings = load_settings()
            settings.setdefault("exportDirs", {})[key] = str(folder)
            save_settings(settings)

        def op_resolveExport(self, req, answer):
            key = req.get("key") or "world"

            def done(folder, remember):
                if folder is None:
                    return answer(None)
                if remember and not self.job:
                    self.remember_dest(key, folder)
                answer({"dir": str(folder), "where": pretty(folder)})
            self.resolve_dest(key, req.get("dest") or {}, done)

        def op_exportFiles(self, req, answer):
            name = valid_name(req["name"])

            def done(folder, remember):
                if folder is None:
                    return answer(None)  # cancelled
                try:
                    if self.job:  # headless: hand the files back to main()
                        self.result_files.append(req)
                    else:
                        write_export(folder, name, req["json"], req["atlas"], req["map"])
                        if remember:
                            self.remember_dest(name, folder)
                    answer({"where": pretty(folder)})
                except Exception as e:
                    answer(error=str(e))
            self.resolve_dest(name, req.get("dest") or {}, done)

        def op_exportText(self, dest, name, text):
            name = valid_name(name.removesuffix(".json")) + ".json"
            if self.job:
                self.result_texts.append({"name": name, "text": text})
                return True
            folder = Path((dest or {}).get("dir") or self.mdir / "export").expanduser()
            folder.mkdir(parents=True, exist_ok=True)
            write_atomic(folder / name, text.encode())
            return True

        def op_pick(self, req, answer):
            kind = req.get("kind")
            flt = Gtk.FileFilter()
            if kind == "tileset":
                flt.set_name("Tileset images")
                for m in ("image/png", "image/gif", "image/webp", "image/bmp"):
                    flt.add_mime_type(m)
            else:
                flt.set_name("Tallgrass maps")
                flt.add_suffix("json")
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(flt)
            dialog = Gtk.FileDialog(title="Import a tileset" if kind == "tileset" else "Load a map", modal=True, filters=filters)
            if kind != "tileset" and self.mdir.is_dir():
                dialog.set_initial_folder(Gio.File.new_for_path(str(self.mdir)))

            def picked(d, res):
                try:
                    f = d.open_finish(res)
                except GLib.Error:
                    return answer(None)
                try:
                    p = Path(f.get_path())
                    if kind == "tileset":
                        ext = p.suffix.lower().lstrip(".") or "png"
                        mime = {"jpg": "jpeg", "svg": "svg+xml"}.get(ext, ext)
                        answer({"name": p.name, "dataURL": f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()})
                    else:
                        answer({"name": p.name, "text": p.read_text()})
                except Exception as e:
                    answer(error=str(e))
            dialog.open(self.win, None, picked)

    app = Gtk.Application(flags=Gio.ApplicationFlags.NON_UNIQUE)
    holder = {}
    app.connect("activate", lambda a: holder.setdefault("shell", Shell(a)))
    app.run([sys.argv[0]])
    return holder.get("shell")


def has_display():
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


# ------------------------------------------------------------------ CLI
def run_job(job):
    if has_display():
        shell = run_gui(job=job)
        done = shell.result or {}
        if not done.get("ok"):
            raise RuntimeError(done.get("error") or "export did not finish")
        return done, shell.result_files, shell.result_texts
    return export_with_chromium(job)


def cli_export(path: Path, out: Path, name=None):
    data = json.loads(path.read_text())
    if data.get("format") != "tallgrass-map":
        raise ValueError(f"{path} is not a Tallgrass map")
    done, files, _ = run_job({"type": "export", "map": data, "name": name, "dest": {"dir": str(out)}})
    final, f = done["name"], files[0]
    if (out / f"{final}.json").resolve() == path.resolve():
        raise ValueError(f"export would overwrite the input {path}, pass --out to write somewhere else")
    write_export(out, final, f["json"], f["atlas"], f["map"])
    for suffix in (".json", "-tiles.png", ".png"):
        print(out / f"{final}{suffix}")


def cli_export_world(folder: Path, out: Path):
    """Export every map in `folder` plus world.json. Map names are file names."""
    maps = {}
    for p in sorted(folder.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        if d.get("format") == "tallgrass-map":
            maps[p.stem] = d
    if not maps:
        raise ValueError(f"no Tallgrass maps in {folder}")
    if out.resolve() == folder.resolve():
        raise ValueError("export would overwrite the maps themselves, pass --out to write somewhere else")
    done, files, texts = run_job({"type": "world", "maps": maps, "dest": {"dir": str(out)}})
    for f in files:
        write_export(out, f["name"], f["json"], f["atlas"], f["map"])
        print(out / f"{f['name']}.json")
    for t in texts:
        write_atomic(out / t["name"], t["text"].encode())
        print(out / t["name"])
    for problem in done.get("problems", []):
        print(f"tallgrass: warning: {problem}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tallgrass", description="Keyboard-first tile map editor.")
    ap.add_argument("file", nargs="?", help="map JSON to open")
    ap.add_argument("--export", metavar="MAP", help="export MAP without opening a window")
    ap.add_argument("--export-world", metavar="DIR", nargs="?", const="", help="export every map in DIR (default: your maps folder) plus world.json")
    ap.add_argument("--out", metavar="DIR", default=".", help="folder for --export (default: current folder)")
    ap.add_argument("--name", help="override the map name used for exported file names")
    ap.add_argument("--icon", metavar="PNG", help=argparse.SUPPRESS)
    ap.add_argument("--size", type=int, default=256, help=argparse.SUPPRESS)
    ap.add_argument("--version", action="version", version=f"tallgrass {VERSION}")
    a = ap.parse_args(argv)
    try:
        if a.export_world is not None:
            cli_export_world(Path(a.export_world).expanduser() if a.export_world else maps_dir(), Path(a.out).expanduser())
        elif a.export:
            cli_export(Path(a.export).expanduser(), Path(a.out).expanduser(), a.name)
        elif a.icon:
            shell = run_gui(job={"type": "icon", "size": a.size})
            r = shell.result or {}
            if not r.get("ok"):
                raise RuntimeError(r.get("error") or "icon render failed")
            write_atomic(Path(a.icon), data_url_bytes(r["png"]))
        else:
            path = None
            if a.file:
                p = Path(a.file).expanduser().resolve()
                if not p.is_file():
                    raise FileNotFoundError(f"no such file: {a.file}")
                path = str(p)
            run_gui(open_path=path)
    except Exception as e:
        print(f"tallgrass: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
