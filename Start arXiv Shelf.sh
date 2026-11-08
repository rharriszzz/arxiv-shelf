#!/usr/bin/env bash
cd -- "$(dirname -- "$0")" || exit 1
# Finder and Windows-launched WSL may not load a shell profile.
# Verify every candidate, including a previously created project environment.
for python in .venv/bin/python python3.14 "$HOME/.local/bin/python3.14" \
    /opt/homebrew/bin/python3.14 /usr/local/bin/python3.14 \
    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14; do
    if "$python" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 14))' >/dev/null 2>&1; then
        exec "$python" shelf.py --open-browser "$@"
    fi
done
printf '%s\n' 'Python 3.14 is required. Create a Python 3.14 .venv in this folder; see README.md for WSL/macOS installation steps. Leave the system Python unchanged.' >&2
exit 1
