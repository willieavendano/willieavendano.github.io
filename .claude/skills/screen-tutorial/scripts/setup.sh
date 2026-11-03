#!/usr/bin/env bash
# setup.sh — idempotent per-machine check/setup for the screen-tutorial skill.
#
# Usage:
#   bash .claude/skills/screen-tutorial/scripts/setup.sh [--install]
#
# Without --install this script only reports. With --install it downloads and
# installs OpenScreen from the latest GitHub release when the app is missing.
#
# Written for macOS's default Bash 3.2: no GNU timeout, no associative arrays,
# and no "${arr[@]}" on empty arrays under set -u.

set -euo pipefail

INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --install)
      INSTALL=1
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: setup.sh [--install]

  --install   Download and install OpenScreen from the latest GitHub release
              if /Applications/Openscreen.app is missing. Without this flag the
              script only reports status.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: setup.sh [--install]" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
OS_APP="/Applications/Openscreen.app"
OS_BIN="$OS_APP/Contents/MacOS/Openscreen"
MCP_FILE="$REPO_ROOT/.mcp.json"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/screen-tutorial-setup.XXXXXX")"
TABLE_FILE="$WORK_DIR/table.txt"
WATCHDOG_PID=""
CMD_PID=""

cleanup() {
  if [ -n "${CMD_PID:-}" ]; then
    kill "$CMD_PID" 2>/dev/null || true
  fi
  if [ -n "${WATCHDOG_PID:-}" ]; then
    kill "$WATCHDOG_PID" 2>/dev/null || true
  fi
  if [ -n "${WORK_DIR:-}" ]; then
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup EXIT INT TERM

# Run a command with a portable timeout. The command's stdout goes to $2 and
# stderr to $3. Returns 124 on timeout. Uses a watchdog background job because
# macOS's Bash 3.2 has no `timeout` command.
run_cmd_timeout() {
  local secs="$1"
  local out_file="$2"
  local err_file="$3"
  shift 3
  local pid watchdog flag rc
  : > "$out_file"
  : > "$err_file"
  flag="$WORK_DIR/timeout.$$.$RANDOM"
  rm -f "$flag"
  "$@" >"$out_file" 2>"$err_file" &
  pid=$!
  CMD_PID="$pid"
  (
    sleep "$secs"
    : > "$flag"
    kill "$pid" 2>/dev/null || true
  ) &
  watchdog=$!
  WATCHDOG_PID="$watchdog"
  rc=0
  wait "$pid" 2>/dev/null || rc=$?
  if [ -f "$flag" ]; then
    kill "$watchdog" 2>/dev/null || true
    wait "$watchdog" 2>/dev/null || true
    CMD_PID=""
    WATCHDOG_PID=""
    rm -f "$flag"
    return 124
  fi
  kill "$watchdog" 2>/dev/null || true
  wait "$watchdog" 2>/dev/null || true
  CMD_PID=""
  WATCHDOG_PID=""
  rm -f "$flag"
  return "$rc"
}

add_row() {
  printf "%-30s | %-26s | %s\n" "$1" "$2" "$3" >> "$TABLE_FILE"
}

tool_present() {
  command -v "$1" >/dev/null 2>&1
}

install_openscreen() {
  local arch json url dmg mnt app_src
  arch="$(uname -m)"
  json="$WORK_DIR/release.json"
  echo "OpenScreen.app is missing; fetching the latest release metadata..."
  if ! curl -fsSL --connect-timeout 20 --retry 2 \
      -H 'Accept: application/vnd.github+json' \
      -H 'User-Agent: screen-tutorial-setup' \
      "https://api.github.com/repos/getopenscreen/openscreen/releases/latest" \
      -o "$json"; then
    echo "ERROR: could not fetch release metadata from GitHub." >&2
    return 1
  fi
  url="$(python3 - "$arch" "$json" <<'PY'
import json, sys
arch = sys.argv[1].lower()
path = sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
dmgs = []
for asset in data.get("assets") or []:
    name = (asset.get("name") or "").lower()
    url = asset.get("browser_download_url") or ""
    if name.endswith(".dmg") and url:
        dmgs.append((name, url))
if not dmgs:
    sys.exit(10)
def pick(patterns):
    for pattern in patterns:
        for name, url in dmgs:
            if pattern in name:
                return url
    return ""
if arch in ("arm64", "aarch64"):
    url = (pick(["apple-silicon", "arm64", "aarch64"])
           or pick(["universal"])
           or pick(["intel", "x64", "x86_64"]))
else:
    url = (pick(["intel", "x64", "x86_64"])
           or pick(["universal"])
           or pick(["apple-silicon", "arm64"]))
if not url:
    url = dmgs[0][1]
print(url)
PY
)" || return 1
  if [ -z "$url" ]; then
    echo "ERROR: no macOS .dmg asset found in the latest release." >&2
    return 1
  fi
  echo "Downloading: $url"
  dmg="$WORK_DIR/openscreen.dmg"
  if ! curl -fL --connect-timeout 20 --retry 2 -o "$dmg" "$url"; then
    echo "ERROR: download failed." >&2
    return 1
  fi
  mnt="$WORK_DIR/mnt"
  mkdir -p "$mnt"
  if ! hdiutil attach "$dmg" -nobrowse -quiet -mountpoint "$mnt"; then
    echo "ERROR: could not mount the downloaded DMG." >&2
    return 1
  fi
  app_src="$(find "$mnt" -maxdepth 2 -name '*.app' -type d -print 2>/dev/null | head -n 1 || true)"
  if [ -z "$app_src" ]; then
    echo "ERROR: no .app found inside the DMG." >&2
    hdiutil detach "$mnt" -quiet 2>/dev/null || true
    return 1
  fi
  if [ -e "$OS_APP" ]; then
    rm -rf "$OS_APP" 2>/dev/null || true
  fi
  if ! ditto "$app_src" "$OS_APP"; then
    echo "ERROR: could not copy Openscreen.app to /Applications." >&2
    hdiutil detach "$mnt" -quiet 2>/dev/null || true
    return 1
  fi
  hdiutil detach "$mnt" -quiet 2>/dev/null \
    || hdiutil detach "$mnt" -force -quiet 2>/dev/null \
    || true
  VERSION="$(defaults read "$OS_APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || true)"
  if [ -z "$VERSION" ]; then
    VERSION="$(defaults read "$OS_APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || true)"
  fi
  [ -n "$VERSION" ] || VERSION="unknown"
  echo "Installed OpenScreen $VERSION at $OS_APP"
  return 0
}

VERSION=""
INSTALLED=0
INSTALL_ATTEMPTED=0
FAIL_OPENSCREEN=0
FAIL_HELP=0
FAIL_SOURCES=0
FAIL_EXCEL=0
FAIL_TOOLS=0

# ---------------------------------------------------------------------------
# OpenScreen app and CLI
# ---------------------------------------------------------------------------
if [ -x "$OS_BIN" ]; then
  INSTALLED=1
  VERSION="$(defaults read "$OS_APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || true)"
  if [ -z "$VERSION" ]; then
    VERSION="$(defaults read "$OS_APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || true)"
  fi
  [ -n "$VERSION" ] || VERSION="unknown"
elif [ "$INSTALL" -eq 1 ]; then
  INSTALL_ATTEMPTED=1
  if install_openscreen; then
    INSTALLED=1
  else
    INSTALLED=0
  fi
fi

if [ "$INSTALLED" -eq 1 ] && [ -x "$OS_BIN" ]; then
  add_row "OpenScreen.app" "$VERSION" "-"
elif [ "$INSTALL_ATTEMPTED" -eq 1 ]; then
  add_row "OpenScreen.app" "install failed" "Download manually: https://github.com/getopenscreen/openscreen/releases"
  FAIL_OPENSCREEN=1
else
  add_row "OpenScreen.app" "missing" "Re-run with --install"
  FAIL_OPENSCREEN=1
fi

HELP_OUT="$WORK_DIR/help.out"
HELP_ERR="$WORK_DIR/help.err"
HELP_RC=0
HELP_OK=0
if [ "$INSTALLED" -eq 1 ] && [ -x "$OS_BIN" ]; then
  run_cmd_timeout 20 "$HELP_OUT" "$HELP_ERR" \
    env -u ELECTRON_RUN_AS_NODE "$OS_BIN" help || HELP_RC=$?
  if [ "$HELP_RC" -eq 124 ]; then
    HELP_OK=0
  elif grep -qi 'usage' "$HELP_OUT" "$HELP_ERR" 2>/dev/null; then
    HELP_OK=1
  fi
fi
if [ "$HELP_OK" -eq 1 ]; then
  add_row "OpenScreen CLI (help)" "ok" "-"
else
  if [ "$INSTALLED" -ne 1 ]; then
    add_row "OpenScreen CLI (help)" "skipped" "Install OpenScreen first"
  elif [ "$HELP_RC" -eq 124 ]; then
    add_row "OpenScreen CLI (help)" "timeout" "Run '... help' manually; reinstall if it persists"
  else
    add_row "OpenScreen CLI (help)" "failed" "Reinstall OpenScreen"
  fi
  FAIL_HELP=1
fi

SRC_OUT="$WORK_DIR/sources.out"
SRC_ERR="$WORK_DIR/sources.err"
SRC_RC=0
SRC_PARSE_OUT=""
SRC_PARSE_RC=0
SRC_STATUS="unknown"
if [ "$INSTALLED" -eq 1 ] && [ -x "$OS_BIN" ]; then
  run_cmd_timeout 45 "$SRC_OUT" "$SRC_ERR" \
    env -u ELECTRON_RUN_AS_NODE "$OS_BIN" sources --json || SRC_RC=$?
else
  SRC_RC=127
fi
if [ "$INSTALLED" -ne 1 ]; then
  SRC_STATUS="skipped"
elif [ "$SRC_RC" -eq 124 ]; then
  SRC_STATUS="timeout"
elif [ -s "$SRC_OUT" ]; then
  SRC_PARSE_OUT="$(python3 - "$SRC_OUT" <<'PY'
import json, sys
path = sys.argv[1]
try:
    text = open(path, "r", encoding="utf-8", errors="replace").read().strip()
except Exception as exc:
    print("ERROR reading sources output: %s" % exc)
    sys.exit(4)
if not text:
    print("ERROR empty sources output")
    sys.exit(4)
events = []
try:
    obj = json.loads(text)
    if isinstance(obj, dict):
        events = [obj]
    elif isinstance(obj, list):
        events = [e for e in obj if isinstance(e, dict)]
except Exception:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            events.append(obj)
done = None
for event in events:
    if event.get("event") == "done":
        done = event
        break
if done is None:
    print("ERROR no done event")
    sys.exit(4)
if done.get("success") is False:
    print("ERROR done success=false")
    sys.exit(4)
sources = done.get("sources") or {}
displays = sources.get("displays") or []
windows = sources.get("windows") or []
print("DISPLAYS=%d WINDOWS=%d" % (len(displays), len(windows)))
if len(displays) == 0:
    sys.exit(2)
if len(windows) == 0:
    sys.exit(3)
sys.exit(0)
PY
)" || SRC_PARSE_RC=$?
  case "$SRC_PARSE_RC" in
    0) SRC_STATUS="granted" ;;
    2) SRC_STATUS="not granted (no display)" ;;
    3) SRC_STATUS="not granted (no windows)" ;;
    4) SRC_STATUS="error" ;;
    *) SRC_STATUS="error" ;;
  esac
else
  SRC_STATUS="error"
fi

if [ "$SRC_STATUS" = "granted" ]; then
  add_row "Screen Recording (sources)" "granted" "-"
elif [ "$SRC_STATUS" = "skipped" ]; then
  add_row "Screen Recording (sources)" "skipped" "Install OpenScreen first"
  FAIL_SOURCES=1
elif [ "$SRC_STATUS" = "timeout" ]; then
  add_row "Screen Recording (sources)" "timeout" "Re-run sources; check OpenScreen"
  FAIL_SOURCES=1
elif [ "$SRC_STATUS" = "not granted (no display)" ] || [ "$SRC_STATUS" = "not granted (no windows)" ]; then
  add_row "Screen Recording (sources)" "$SRC_STATUS" "Grant to host app in System Settings -> Privacy & Security -> Screen Recording"
  FAIL_SOURCES=1
else
  add_row "Screen Recording (sources)" "error" "Check OpenScreen and Screen Recording permission"
  FAIL_SOURCES=1
fi

if [ "$SRC_STATUS" = "not granted (no windows)" ] || [ "$SRC_STATUS" = "not granted (no display)" ]; then
  echo ""
  echo "Screen Recording permission is missing or not effective."
  echo "Grant it to the HOST app that runs Claude, not to OpenScreen itself:"
  echo "  System Settings -> Privacy & Security -> Screen Recording"
  echo "  Enable Terminal, Ghostty, T3 Code, VS Code, or whichever app runs Claude."
  echo "Then quit and reopen that app and run this check again."
  echo ""
fi

# ---------------------------------------------------------------------------
# Accessibility (only needed by the sheets driver)
# ---------------------------------------------------------------------------
ACC_OUT="$WORK_DIR/accessibility.out"
ACC_ERR="$WORK_DIR/accessibility.err"
ACC_RC=0
ACC_STATUS="not granted"
run_cmd_timeout 10 "$ACC_OUT" "$ACC_ERR" \
  osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' || ACC_RC=$?
if [ "$ACC_RC" -eq 0 ] && [ -s "$ACC_OUT" ]; then
  ACC_STATUS="granted"
fi
if [ "$ACC_STATUS" = "granted" ]; then
  add_row "Accessibility" "granted" "-"
else
  add_row "Accessibility" "not granted" "Only for sheets driver; excel does not need it. Grant to host app in System Settings -> Privacy & Security -> Accessibility"
fi

# ---------------------------------------------------------------------------
# Microsoft Excel
# ---------------------------------------------------------------------------
EXCEL_APP="/Applications/Microsoft Excel.app"
EXCEL_OUT="$WORK_DIR/excel.out"
EXCEL_ERR="$WORK_DIR/excel.err"
EXCEL_RC=0
EXCEL_STATUS=""
run_cmd_timeout 90 "$EXCEL_OUT" "$EXCEL_ERR" \
  osascript -e 'tell application "Microsoft Excel" to get version' || EXCEL_RC=$?
if [ "$EXCEL_RC" -eq 0 ] && [ -s "$EXCEL_OUT" ]; then
  EXCEL_STATUS="$(tr -d '\r\n' < "$EXCEL_OUT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  add_row "Microsoft Excel" "$EXCEL_STATUS" "-"
else
  if [ -d "$EXCEL_APP" ]; then
    EXCEL_STATUS="installed, no response"
    add_row "Microsoft Excel" "$EXCEL_STATUS" "Open Excel once and allow Automation in System Settings -> Privacy & Security -> Automation"
  else
    EXCEL_STATUS="not installed"
    add_row "Microsoft Excel" "$EXCEL_STATUS" "Install Microsoft Excel for Mac"
  fi
  FAIL_EXCEL=1
fi
if [ "$EXCEL_RC" -eq 124 ]; then
  echo "Note: Excel did not respond within 90 s. If it is installed, open it once and grant Automation permission."
fi

# ---------------------------------------------------------------------------
# Narrator
# ---------------------------------------------------------------------------
KEY_PRESENT=0
if [ -n "${ELEVENLABS_API_KEY:-}" ]; then
  KEY_PRESENT=1
fi
if [ "$KEY_PRESENT" -eq 0 ] && [ -f "$HOME/.hermes/.env" ]; then
  if grep -qE '^[[:space:]]*ELEVENLABS_API_KEY[[:space:]]*=' "$HOME/.hermes/.env"; then
    KEY_PRESENT=1
  fi
fi
if [ "$KEY_PRESENT" -eq 1 ]; then
  add_row "Narrator key (ElevenLabs)" "present" "-"
else
  add_row "Narrator key (ElevenLabs)" "absent" "Add ELEVENLABS_API_KEY to ~/.hermes/.env or export it (the --voice say fallback still works)"
fi

SAY_VOICES="$(say -v '?' 2>/dev/null || true)"
DANIEL_PRESENT=0
case "$SAY_VOICES" in
  *Daniel*) DANIEL_PRESENT=1 ;;
esac
if [ "$DANIEL_PRESENT" -eq 1 ]; then
  add_row "Narrator voice (Daniel)" "present" "-"
else
  add_row "Narrator voice (Daniel)" "missing" "Install Daniel in System Settings -> Accessibility -> Spoken Content -> Manage Voices"
fi

# ---------------------------------------------------------------------------
# MCP configuration
# ---------------------------------------------------------------------------
MCP_STATUS="missing"
MCP_ENTRY=""
MCP_PARSE_RC=0
if [ -f "$MCP_FILE" ]; then
  MCP_STATUS="present"
  MCP_ENTRY="$(python3 - "$MCP_FILE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as exc:
    print("could not parse .mcp.json: %s" % exc)
    sys.exit(1)
servers = data.get("mcpServers", data)
entry = servers.get("openscreen") if isinstance(servers, dict) else None
if entry is None:
    print("no 'openscreen' entry")
    sys.exit(2)
print(json.dumps(entry, indent=2))
PY
)" || MCP_PARSE_RC=$?
  if [ "$MCP_PARSE_RC" -ne 0 ]; then
    MCP_STATUS="present (unreadable)"
  fi
fi
if [ "$MCP_STATUS" = "present" ]; then
  add_row "MCP .mcp.json" "present" "-"
elif [ "$MCP_STATUS" = "present (unreadable)" ]; then
  add_row "MCP .mcp.json" "present (unreadable)" "Check .mcp.json JSON syntax"
else
  add_row "MCP .mcp.json" "missing" "Restore .mcp.json from git"
fi

# ---------------------------------------------------------------------------
# Command-line tools
# ---------------------------------------------------------------------------
PY_STATUS="missing"
PY_OK=0
PY_VER=""
if tool_present python3; then
  PY_OUT="$WORK_DIR/pyver.out"
  PY_ERR="$WORK_DIR/pyver.err"
  PY_RC=0
  run_cmd_timeout 10 "$PY_OUT" "$PY_ERR" \
    python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' || PY_RC=$?
  if [ "$PY_RC" -eq 0 ] && [ -s "$PY_OUT" ]; then
    PY_VER="$(tr -d '\r\n' < "$PY_OUT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    PY_CMP_OUT="$WORK_DIR/pycheck.out"
    PY_CMP_ERR="$WORK_DIR/pycheck.err"
    PY_CMP_RC=0
    run_cmd_timeout 10 "$PY_CMP_OUT" "$PY_CMP_ERR" \
      python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' || PY_CMP_RC=$?
    if [ "$PY_CMP_RC" -eq 0 ]; then
      PY_OK=1
      PY_STATUS="python3 $PY_VER"
    else
      PY_STATUS="python3 ${PY_VER} (<3.9)"
    fi
  fi
fi
if [ "$PY_OK" -eq 1 ]; then
  add_row "python3" "$PY_STATUS" "-"
else
  add_row "python3" "$PY_STATUS" "Install Python 3.9+ (python.org or Homebrew)"
  FAIL_TOOLS=1
fi

for tool in afconvert afinfo afplay sips; do
  if tool_present "$tool"; then
    add_row "$tool" "present" "-"
  else
    add_row "$tool" "missing" "macOS built-in tool; restore it or reinstall the command-line tools"
    FAIL_TOOLS=1
  fi
done

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
echo ""
echo "MCP configuration:"
if [ -f "$MCP_FILE" ]; then
  echo "  File: $MCP_FILE"
  if [ "$MCP_PARSE_RC" -eq 0 ]; then
    echo "  openscreen entry:"
    printf '%s\n' "$MCP_ENTRY" | sed 's/^/    /'
  elif [ "$MCP_PARSE_RC" -eq 2 ]; then
    echo "  .mcp.json exists but has no 'openscreen' entry."
  else
    echo "  .mcp.json exists but could not be parsed:"
    printf '%s\n' "$MCP_ENTRY" | sed 's/^/    /'
  fi
  echo "  Nothing to register per machine. In an interactive Claude session, verify with: claude mcp list"
else
  echo "  $MCP_FILE is missing. Restore it from git."
fi

echo ""
echo "Screen tutorial setup status"
echo "============================"
printf "%-30s | %-26s | %s\n" "Component" "Status" "Fix"
printf '%s\n' "-------------------------------+----------------------------+--------------------------------"
cat "$TABLE_FILE"
if [ "$SRC_STATUS" = "granted" ] && [ -n "$SRC_PARSE_OUT" ]; then
  echo ""
  echo "OpenScreen sources: $SRC_PARSE_OUT"
fi

echo ""
if [ "$FAIL_OPENSCREEN" -eq 0 ] \
   && [ "$FAIL_HELP" -eq 0 ] \
   && [ "$FAIL_SOURCES" -eq 0 ] \
   && [ "$FAIL_EXCEL" -eq 0 ] \
   && [ "$FAIL_TOOLS" -eq 0 ]; then
  echo "Overall: Excel path usable."
  exit 0
else
  echo "Overall: Excel path NOT usable — fix the rows above."
  exit 1
fi
