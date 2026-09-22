# Later: Windows PC support

Resume this work when running on Richard's Windows PC.

Goal: run arXiv Shelf on Windows with the same searchable, sortable PDF index and one-click opening in Adobe Acrobat Reader.

The Python indexer and browser interface are largely portable already. The main work is Windows-specific launching and setup:

- Detect the actual Windows Downloads folder, including a redirected location, while retaining `--directory` as an override.
- Locate the installed Adobe Acrobat / Acrobat Reader executable and add a Windows implementation of `open_pdf()` in `shelf.py`. Support an explicit executable path and filenames containing spaces or non-ASCII characters. Show a useful error if Reader is missing.
- Add a double-click Windows launcher (for example, `Start arXiv Shelf.bat`) that starts the local server and opens the browser. Check the installed Python launcher on the PC.
- Check whether `pdftotext` is available. Document a Windows Poppler installation option or choose a portable extraction dependency for recovering older arXiv IDs.
- Keep the index cache local to each computer; rebuild it from that computer's PDFs rather than copying cached macOS paths.
- Update README.md with Windows setup and usage instructions.
- Run the automated tests on Windows, accounting for Windows symlink permissions. Verify scanning, cached/offline use, search, sorting, rescanning, browser preview, and opening the correct local PDF in Reader.

Do the Windows-specific implementation and end-to-end verification on the PC, where the installed Reader path, Downloads location, Python setup, and permissions can be checked directly.

## Shared catalog follow-up on the PC

The persistent Git-backed catalog, 1–5 star ratings, missing-file download button, and explicit **Sync with GitHub** button are implemented. The `catalog/` folder is shared in this repository; `.shelf/` is still a local cache. Clone/pull the repository on the PC and configure GitHub authentication there. Verify a round trip: sync on the Mac, see the catalog on the PC, download a missing PDF, add/rate a PC paper, sync there, and sync again on the Mac. Check Windows Git/SSH availability and download behavior along with the remaining Acrobat integration above.
