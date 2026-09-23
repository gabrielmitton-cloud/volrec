#!/bin/sh
# Install the volrec daily iMessage check on THIS Mac (OPS-AGENT.md item 7).
# It is a standing change to your Mac, so it is never run for you: run it yourself.
#
#   sh tools/launchd/install.sh        # install, or reinstall after an update
#   sh tools/launchd/install.sh --remove
#
# What it sets up:
#   ~/.volrec-ops         a separate clean clone. The job pulls into THIS, never into
#                         your working copy, so an uncommitted edit of yours can never
#                         turn into a false alarm. Nobody edits it by hand.
#   a launchd job         weekdays 13:30 local time (after even the latest landing seen,
#                         19:45 UTC = 12:45 Pacific): pull, run tools/daily.py, and
#                         text you the one-line verdict through tools/notify.py.
#   ~/Library/Logs/volrec-daily.log   what each run printed.
set -e
LABEL=com.volrec.daily
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
OPS="$HOME/.volrec-ops"
PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
SRC="$(cd "$(dirname "$0")/../.." && pwd)"

if [ "$1" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed the launchd job ($OPS is left in place; delete it by hand if you like)"
  exit 0
fi

[ -f "$HOME/.config/volrec/imessage_handle" ] || {
  echo "No handle yet. Save your iMessage phone number or Apple ID first:"
  echo "  mkdir -p ~/.config/volrec && read -r \"H?Number or Apple ID: \" && printf '%s' \"\$H\" > ~/.config/volrec/imessage_handle && chmod 600 ~/.config/volrec/imessage_handle"
  exit 1; }

if [ -d "$OPS/.git" ]; then git -C "$OPS" pull --quiet --rebase origin main
else git clone --quiet https://github.com/gabrielmitton-cloud/volrec.git "$OPS"; fi
# The FRED cache is gitignored (FRED's terms), so copy it: without it the ops clone
# would discount at r=0 and read H3 slightly differently from your working copy.
[ -f "$SRC/data/fred_cache.json" ] && cp "$SRC/data/fred_cache.json" "$OPS/data/"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/bin/sh</string><string>-c</string>
    <string>cd "$OPS" &amp;&amp; git pull --quiet --rebase origin main; "$PY" tools/daily.py --no-pull --notify</string>
  </array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>13</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>13</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>13</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>13</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>13</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/volrec-daily.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/volrec-daily.log</string>
</dict></plist>
PLIST
plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed: weekdays 13:30 local. Test it now with:  launchctl kickstart gui/$(id -u)/$LABEL"
echo "log: ~/Library/Logs/volrec-daily.log    remove: sh tools/launchd/install.sh --remove"
