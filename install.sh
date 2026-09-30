#!/bin/bash
# Install Tallgrass as an Omarchy app: launcher entry, icon and `tallgrass` command.
# Safe to re-run; it replaces the installed copy with this checkout.
set -euo pipefail
cd "$(dirname "$0")"

APP_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/tallgrass"
BIN="$HOME/.local/bin/tallgrass"
DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/tallgrass.desktop"
ICON_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
DEPS=(python python-gobject gtk4 webkitgtk-6.0)

echo "Tallgrass installer"

# 1. Dependencies (all from the official repos; usually already on Omarchy)
missing=()
for p in "${DEPS[@]}"; do pacman -Q "$p" &>/dev/null || missing+=("$p"); done
if ((${#missing[@]})); then
  echo "  installing ${missing[*]}"
  if command -v omarchy-pkg-add &>/dev/null; then omarchy-pkg-add "${missing[@]}"; else sudo pacman -S --needed "${missing[@]}"; fi
fi

# 2. App files. The installed copy is independent of this checkout.
rm -rf "$APP_HOME"
mkdir -p "$APP_HOME"
cp -r src shell "$APP_HOME/"
cp assets/tallgrass.png "$APP_HOME/"
echo "  app files   $APP_HOME"

# 3. Command
mkdir -p "$(dirname "$BIN")"
cat >"$BIN" <<EOF
#!/bin/bash
exec python3 "$APP_HOME/shell/tallgrass.py" "\$@"
EOF
chmod +x "$BIN"
echo "  command     $BIN"

# 4. Icon, where omarchy-webapp-install puts launcher icons
mkdir -p "$ICON_ROOT/256x256/apps"
cp assets/tallgrass.png "$ICON_ROOT/256x256/apps/tallgrass.png"
gtk-update-icon-cache "$ICON_ROOT" &>/dev/null || true
echo "  icon        $ICON_ROOT/256x256/apps/tallgrass.png"

# 5. Launcher entry. StartupWMClass matches the window's Hyprland class.
mkdir -p "$(dirname "$DESKTOP")"
cat >"$DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Tallgrass
GenericName=Tile Map Editor
Comment=Keyboard-first tile map editor for top-down RPG worlds
Exec=$BIN %f
Icon=tallgrass
Terminal=false
Categories=Graphics;2DGraphics;
Keywords=map;tile;tilemap;rpg;pixel;editor;
StartupWMClass=tallgrass
StartupNotify=true
EOF
chmod +x "$DESKTOP"
update-desktop-database "$(dirname "$DESKTOP")" &>/dev/null || true
echo "  launcher    $DESKTOP"

# 6. Maps folder
if [[ -d $HOME/Documents ]]; then MAPS="$HOME/Documents/tallgrass"; else MAPS="$HOME/tallgrass"; fi
mkdir -p "$MAPS"
echo "  maps        $MAPS"

case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "  note: add ~/.local/bin to PATH to run 'tallgrass' from a terminal" ;; esac
echo "Done. Open it from the launcher (SUPER + SPACE, type Tallgrass) or run: tallgrass"
