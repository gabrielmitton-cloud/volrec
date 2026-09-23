#!/usr/bin/env python3
"""Send Gabriel an iMessage from this Mac. Operations only (OPS-AGENT.md, item 7).

No LLM, no service, no cost: it asks macOS Messages to send one message to one
handle (a phone number or Apple ID email), read from a file OUTSIDE the repository:

    ~/.config/volrec/imessage_handle      (one line; chmod 600)

The message text and the handle are passed to AppleScript as ARGUMENTS, never
spliced into the script's source, so nothing in a message can become code.

The first real send makes macOS ask whether the sending program may control
Messages; allow it once. A launchd job counts as a different program, so it can
ask again the first time it fires.

USAGE
-----
  python3 tools/notify.py "text"            # send
  python3 tools/notify.py --dry-run "text"  # show what would be sent, send nothing
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDLE_FILE = Path.home() / ".config" / "volrec" / "imessage_handle"
MAX_LEN = 600                       # a text, not an essay

SCRIPT = [
    "on run argv",
    'tell application "Messages"',
    "set svc to 1st account whose service type = iMessage",
    "send (item 1 of argv) to participant (item 2 of argv) of svc",
    "end tell",
    "end run",
]


def handle():
    if not HANDLE_FILE.exists():
        return None
    p = HANDLE_FILE.resolve()
    if p == ROOT or ROOT in p.parents:
        raise SystemExit("Refusing an iMessage handle stored inside the repository.")
    return HANDLE_FILE.read_text().strip() or None


def send(text, dry=False):
    """(sent, why). Never raises: a failed notification must not fail the check it reports."""
    text = " ".join(str(text).split())[:MAX_LEN]
    h = handle()
    if dry:
        return False, f"dry run, would send to {'the saved handle' if h else 'NO HANDLE SAVED'}: {text}"
    if not h:
        return False, f"no handle saved in {HANDLE_FILE}; nothing sent"
    args = ["osascript"] + sum((["-e", ln] for ln in SCRIPT), []) + [text, h]
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
    except Exception as e:                     # noqa: BLE001 - report, never raise
        return False, f"osascript did not run: {type(e).__name__}"
    if p.returncode != 0:
        return False, f"Messages refused: {p.stderr.strip()[:200]}"
    return True, "sent"


def main():
    dry = "--dry-run" in sys.argv
    words = [a for a in sys.argv[1:] if a != "--dry-run"]
    if not words:
        print(__doc__)
        return 2
    ok, why = send(" ".join(words), dry)
    print(why)
    return 0 if ok or dry else 1


if __name__ == "__main__":
    sys.exit(main())
