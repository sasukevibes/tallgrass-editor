#!/bin/bash
# Native shell tests. Each probe runs inside the real GTK + WebKit window with
# the real host bridge, in throwaway folders (your maps, session and theme are
# never touched). Keys are dispatched inside the page, so nothing is typed into
# other windows on the desktop.
set -uo pipefail
cd "$(dirname "$0")/.."
T=$(mktemp -d -t tallgrass-test.XXXX)
trap 'rm -rf "$T"' EXIT
export TALLGRASS_MAPS_DIR=$T/maps TALLGRASS_STATE_DIR=$T/state TALLGRASS_THEME_DIR=$T/omarchy/theme
mkdir -p "$T/omarchy/theme" "$T/omarchy/next"
fail=0

theme() { # bg fg accent green red magenta yellow cyan mode
  printf 'mode = "%s"\naccent = "%s"\nbackground = "%s"\nforeground = "%s"\ngreen = "%s"\nred = "%s"\nmagenta = "%s"\nyellow = "%s"\ncyan = "%s"\n' \
    "$9" "$3" "$1" "$2" "$4" "$5" "$6" "$7" "$8"
}
theme "#eff1f5" "#4c4f69" "#1e66f5" "#40a02b" "#d20f39" "#ea76cb" "#df8e1d" "#179299" light >"$T/omarchy/theme/colors.toml"

probe() { # file [extra js]
  { echo "${2:-}"; cat tests/native/lib.js "tests/native/$1"; } >"$T/probe.js"
  TALLGRASS_TEST_JS=$T/probe.js timeout "${3:-40}" python3 shell/tallgrass.py
}
check() { # label python-expression-over-r
  if python3 -c "import json,sys; r=json.loads(sys.argv[1]); sys.exit(0 if ($2) else 1)" "$RES" 2>/dev/null; then
    echo "  ok    $1"
  else
    echo "  FAIL  $1"; fail=1
  fi
}

# PNG bytes differ between the engines' encoders; the pixels should not (blended
# edges may round 1 apart).
samepixels() { # a.png b.png tolerance
  python3 -c '
import sys, gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf
a, b = (GdkPixbuf.Pixbuf.new_from_file(p) for p in sys.argv[1:3])
same_size = (a.get_width(), a.get_height()) == (b.get_width(), b.get_height())
sys.exit(0 if same_size and max(abs(x - y) for x, y in zip(a.get_pixels(), b.get_pixels())) <= int(sys.argv[3]) else 1)
' "$@"
}

echo "1. fresh map, paint, :w, :q"
RES=$(TALLGRASS_TEST_NOQUIT=1 probe 1-paint-save-quit.js "" 30); code=$?
echo "     $RES"
check "exits through :q (code $code)" "$code == 0"
check "native bridge in use" "r['native']"
check "new map is all grass, Grass brush" "r['freshAllGrass'] and r['brushAtStart'] == 'grass'"
check "E E selects Tall grass" "r['brush'] == 'tall_grass'"
check "hold Space + D paints 5 cells" "r['painted'] == ['tall_grass']*5"
check ":q refuses with unsaved changes" "r['qRefusedWhenDirty']"
check ":w reports the file path" "'keytest.json' in r['saveMsg']"
check "Tab completes file names" "r['completion'].strip() == 'e keytest'"
[[ -f $T/maps/keytest.json ]] && echo "  ok    keytest.json on disk" || { echo "  FAIL  keytest.json on disk"; fail=1; }
[[ -f $T/state/session.json ]] && echo "  ok    session flushed on quit" || { echo "  FAIL  session flushed on quit"; fail=1; }
python3 - "$T/maps/keytest.json" <<'EOF' && echo "  ok    saved file is tallgrass-map v1" || { echo "  FAIL  saved file format"; exit 1; }
import json, sys
d = json.load(open(sys.argv[1]))
assert d["format"] == "tallgrass-map" and d["version"] == 1 and d["tileSize"] == 16
assert set(d["layers"]) == {"ground", "objects", "overhead"} and d["width"] == 40 and d["height"] == 28
assert set(d) >= {"name", "attributes", "warps", "imports"}
EOF
[[ $? -eq 0 ]] || fail=1

echo "2. relaunch, :ls, :e, :restore"
RES=$(probe 2-reopen.js)
echo "     $RES"
check "relaunch starts on fresh grass" "r['freshAllGrass']"
check ":ls lists keytest" "'keytest' in r['ls']"
check ":e keytest loads the painted row" "r['name'] == 'keytest' and r['row'] == ['tall_grass']*5"
check ":restore brings back the last session" "r['restoredName'] == 'keytest' and 'Restored' in r['restore']"

echo "3. theme live reload, :export, play mode"
( # swap the theme the way omarchy-theme-set does: build next, rm current, mv next into place
  for _ in $(seq 100); do grep -q swap-now "$T/state/session.json" 2>/dev/null && break; sleep 0.1; done
  theme "#1a1b26" "#c0caf5" "#7aa2f7" "#9ece6a" "#f7768e" "#bb9af7" "#e0af68" "#7dcfff" dark >"$T/omarchy/next/colors.toml"
  rm -rf "$T/omarchy/theme"; mv "$T/omarchy/next" "$T/omarchy/theme"
) &
RES=$(probe 3-theme-export-play.js "window.TALLGRASS_TEST_EXPORT_DIR = '$T/game-assets';")
wait
echo "     $RES"
check "starts with the light theme" "r['panelBefore'] == '#eff1f5'"
check "switches to the new theme live" "r['panelAfter'] == '#1a1b26' and r['modeColorAfter'] == '#7aa2f7'"
check "canvas follows the theme" "r['canvasBg'] != '#090c12'"
check ":export reports the folder" "'game-assets' in r['exportMsg'] and r['exportDialogOpen']"
check "play mode starts" "r['playing']"
check "tree blocks the step" "r['afterTree'] == [6, 5]"
check "ledge hops down two cells" "r['afterLedge'] == [6, 7]"
check "ledge cannot be climbed" "r['afterUp'] == [6, 7]"
check "Esc stops play" "r['stopped']"
python3 - "$T/game-assets" <<'EOF' && echo "  ok    export wrote json, atlas and map png" || { echo "  FAIL  export files"; exit 1; }
import json, struct, sys, pathlib
d = pathlib.Path(sys.argv[1])
j = json.loads((d / "untitled.json").read_text())
assert j["format"] == "tallgrass-map" and j["version"] == 1
for k in ("tileIndices", "collision", "events", "spawn", "tileKeys", "tileset", "layers", "attributes", "warps", "imports"):
    assert k in j, k
def size(p):
    b = p.read_bytes(); assert b[:8] == b"\x89PNG\r\n\x1a\n"; return struct.unpack(">II", b[16:24])
assert size(d / "untitled.png") == (30 * 16, 20 * 16), size(d / "untitled.png")
w, h = size(d / "untitled-tiles.png"); assert w == 256 and h == -(-len(j["tileKeys"]) // 16) * 16
EOF
[[ $? -eq 0 ]] || fail=1
python3 -c "import json;d=json.load(open('$T/state/settings.json'));assert d['exportDirs']['untitled'].endswith('game-assets')" \
  && echo "  ok    export folder remembered" || { echo "  FAIL  export folder remembered"; fail=1; }

echo "4. sprite packs"
RES=$(probe 4-packs.js)
echo "     $RES"
check "Classic is the built-in pack" "r['packs'] == ['classic'] and r['pack'] == 'classic'"
check "Tab completes pack names" "r['completion'] == 'pack classic'"
check ":pack lists the installed packs" "'classic (Classic)' in r['listMsg']"
check ":pack refuses an unknown pack" "'No pack called nope' in r['unknownMsg']"
check "player has a sprite for each direction" "r['sprites'] == [True] * 4"

echo "5. linked maps"
RES=$(probe 5-world.js "window.TALLGRASS_TEST_EXPORT_DIR = '$T/world-out';" 60)
echo "     $RES"
check "launch starts in the last pack you switched to" "r['launchPack'] == 'classic' and r['launchGrass']"
check ":connect lines up the paths" "r['autoOffset'] == -6"
check "[ and ] slide the connection" "r['nudged'] == -5 and r['back'] == -6"
check ":w writes the other side of the edge" "r['northLinks'] == [{'dir': 'south', 'map': 'south-a', 'offset': 6}] and r['ownLinks'][0]['offset'] == -6"
check ":warp! lands on the door and :w writes the way back" "r['ownWarp'] == 'hut-a 5,7' and r['hutWarps'] == {'5,7': 'south-a 9,9'}"
check "O crosses the edge, B comes back" "r['overEdge'] == ['north-a', 10, 9] and r['backFromEdge'] == ['south-a', 4, 0]"
check "O goes through the door, B comes back" "r['throughDoor'] == ['hut-a', 5, 7] and r['backFromDoor'] == ['south-a']"
check "play walks across the seam" "r['playNorth'] == ['north-a', 10, 9]"
check "play walks back into the first map" "r['playSouth'] == ['south-a', 4, 1]"
check "play goes through the door" "r['playDoor'] == ['hut-a', 5, 7]"
check "Esc returns to the map being edited" "r['editing'] == 'south-a' and 'hut-a' in r['stopMsg']"
check "world layout puts north above south" "r['pos']['north-a'][1] + 10 == r['pos']['south-a'][1] and r['pos']['south-a'][0] - r['pos']['north-a'][0] == 6"
check "world check finds the broken door, only that" "r['problems'] == ['south-a 1,1: door leads to nowhere, which doesn\\'t exist']"
check ":world opens, Tab picks, Esc closes" "r['worldOpen'] and r['worldSel'] == 'hut-a' and r['worldClosed']"
check ":rename fixes links in the other maps" "r['afterRename']['north'][0]['map'] == 'south-b' and r['afterRename']['hut'] == {'5,7': 'south-b 9,9'} and 'south-a' not in r['afterRename']['list']"
python3 - "$T/world-out" <<'EOF2' && echo "  ok    :export world writes every map and world.json" || { echo "  FAIL  :export world files"; exit 1; }
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
w = json.loads((d / "world.json").read_text())
assert w["format"] == "tallgrass-world" and w["version"] == 1
assert {"hut-a", "north-a", "south-a"} <= {m["name"] for m in w["maps"]}  # earlier sections' maps are here too
assert all((d / m["file"]).is_file() and (d / m["tiles"]).is_file() and (d / m["image"]).is_file() for m in w["maps"])
assert w["connections"] == [{"from": "north-a", "dir": "south", "to": "south-a", "offset": 6}], w["connections"]
assert {("south-a", "hut-a"), ("hut-a", "south-a")} <= {(x["from"], x["to"]) for x in w["warps"]}
e = json.loads((d / "south-a.json").read_text())
door = [ev for ev in e["events"] if ev["type"] == "warp" and ev["x"] == 9][0]
assert door["map"] == "hut-a" and door["toX"] == 5 and door["toY"] == 7, door
assert e["connections"][0]["map"] == "north-a"
EOF2
[[ $? -eq 0 ]] || fail=1
mkdir -p "$T/cli-world"
python3 shell/tallgrass.py --export-world "$T/maps" --out "$T/cli-world" >/dev/null 2>&1 &&
  python3 -c "import json;w=json.load(open('$T/cli-world/world.json'));assert len(w['maps'])>=3 and w['connections'][0]['to'] in ('south-b','north-a')" &&
  echo "  ok    tallgrass --export-world" || { echo "  FAIL  tallgrass --export-world"; fail=1; }

echo "6. a lost key release"
RES=$(probe 6-stuck-keys.js)
echo "     $RES"
check "painting still works while Space is down" "r['modeAfterDown'] == 'insert' and r['painted'] == 'tall_grass'"
check "Enter opens the command bar mid-stroke" "r['cmdOpen'] and r['modeAfterEnter'] == 'normal' and r['cmdOpen2']"
check "pressing Space again recovers a lost release" "r['afterSecondPress'] == ['insert', 'Space'] and r['afterRelease'] == 'normal'"

echo "7. command bar hints and lesson"
RES=$(probe 7-tutorial.js "" 60)
echo "     $RES"
check "hints list matching commands while typing" "r['hintsShown'] and r['hintsCo'] and r['hintsHidden']"
check "hints show what Tab can fill in" "r['hintsDirs']"
check ":tutorial starts the lesson card" "r['started']"
check "each step advances when you do it" "r['steps'] == list(range(11)) and r['completed'] == 'gen ' and r['history'] == 'w tutorial-practice'"
check "the lesson saves and removes its practice map" "r['practiceSaved'] and r['practiceGone']"
check "your map comes back after the lesson" "r['final'] and r['mapBack']"
check "the last card closes with the next key" "r['cardClosedByKey']"
check "quitting half way brings your map back" "r['quitMapBack']"
check "the lesson is remembered as seen" "r['seen']"

echo "8. tallgrass --export (WebKit, then no-display Chromium fallback)"
mkdir -p "$T/out1" "$T/out2"
python3 shell/tallgrass.py --export "$T/maps/keytest.json" --out "$T/out1" >/dev/null &&
  [[ -s $T/out1/keytest.json && -s $T/out1/keytest-tiles.png && -s $T/out1/keytest.png ]] &&
  echo "  ok    WebKit headless export" || { echo "  FAIL  WebKit headless export"; fail=1; }
env -u WAYLAND_DISPLAY -u DISPLAY python3 shell/tallgrass.py --export "$T/maps/keytest.json" --out "$T/out2" >/dev/null &&
  [[ -s $T/out2/keytest.json && -s $T/out2/keytest-tiles.png && -s $T/out2/keytest.png ]] &&
  echo "  ok    Chromium fallback export" || { echo "  FAIL  Chromium fallback export"; fail=1; }
cmp -s "$T/out1/keytest.json" "$T/out2/keytest.json" && echo "  ok    both engines write the same JSON" || { echo "  FAIL  engines disagree on JSON"; fail=1; }
samepixels "$T/out1/keytest-tiles.png" "$T/out2/keytest-tiles.png" 0 && samepixels "$T/out1/keytest.png" "$T/out2/keytest.png" 1 &&
  echo "  ok    both engines draw the same pixels" || { echo "  FAIL  engines disagree on pixels"; fail=1; }
python3 shell/tallgrass.py --export "$T/maps/keytest.json" --out "$T/maps" 2>/dev/null &&
  { echo "  FAIL  refuses to overwrite its input"; fail=1; } || echo "  ok    refuses to overwrite its input"

echo
[[ $fail -eq 0 ]] && echo "native: all passed" || echo "native: FAILURES"
exit $fail
