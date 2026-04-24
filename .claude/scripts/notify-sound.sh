#!/bin/bash
# Wrapper para notify-sound.bat — invoca el .bat via cmd en Windows
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cmd /c "$(cygpath -w "$SCRIPT_DIR/notify-sound.bat" 2>/dev/null || echo "$SCRIPT_DIR\\notify-sound.bat")" "$1" 2>/dev/null || true
