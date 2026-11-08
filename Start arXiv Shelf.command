#!/bin/zsh
cd -- "${0:A:h}" || exit 1
# Share the explicit Python 3.14 selection and open the actual server URL.
exec /bin/bash './Start arXiv Shelf.sh' "$@"
