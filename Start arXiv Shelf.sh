#!/usr/bin/env bash
cd -- "$(dirname -- "$0")" || exit 1
# Windows launching WSL may not load the shell profile that adds ~/.local/bin.
if command -v python3.12 >/dev/null 2>&1; then
    exec python3.12 shelf.py --open-browser "$@"
elif [ -x "$HOME/.local/bin/python3.12" ]; then
    exec "$HOME/.local/bin/python3.12" shelf.py --open-browser "$@"
fi
printf '%s\n' 'Python 3.12 is required by this launcher. Install it in WSL and try again.' >&2
exit 1
