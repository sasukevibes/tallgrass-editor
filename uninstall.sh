#!/bin/bash
# Remove the Tallgrass launcher entry, icon, command and installed app files.
# Your maps are never touched. --purge also removes the session and settings
# in ~/.local/state/tallgrass.
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/tallgrass"

rm -f "$DATA/applications/tallgrass.desktop" "$HOME/.local/bin/tallgrass" "$DATA/icons/hicolor/256x256/apps/tallgrass.png"
rm -rf "$DATA/tallgrass"
gtk-update-icon-cache "$DATA/icons/hicolor" &>/dev/null || true
update-desktop-database "$DATA/applications" &>/dev/null || true
echo "Removed the Tallgrass launcher entry, icon, command and app files."

if [[ ${1:-} == --purge ]]; then
  rm -rf "$STATE"
  echo "Removed session and settings in $STATE."
else
  echo "Kept the session and settings in $STATE (use --purge to remove them)."
fi
if [[ -d $HOME/Documents/tallgrass ]]; then echo "Your maps are still in ~/Documents/tallgrass."; elif [[ -d $HOME/tallgrass ]]; then echo "Your maps are still in ~/tallgrass."; fi
