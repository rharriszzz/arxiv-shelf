# PC verification follow-up

Windows/WSL Downloads detection, Acrobat opening with a default-app fallback, browser launching, and Windows/WSL launchers are implemented. On this PC, the WSL server was verified with the Windows Downloads folder, six local PDFs, browser assets, PDF preview, and a successful Windows PDF launch. All 22 automated tests pass in WSL.

Remaining checks:

- Poppler is installed and verified in WSL; `0501052v1.pdf` resolves to `quant-ph/0501052v1`.
- Run the Mac comparison requested in [MAC_API_TEST.md](MAC_API_TEST.md) before choosing a metadata-request workaround.
- Verify the native Windows Python path on a machine with native Python installed; this PC uses WSL Python.
- Visually check search, sorting, ratings, and the double-click launcher in the Windows browser.

## Shared catalog follow-up on the PC

The persistent Git-backed catalog, 1–5 star ratings, missing-file download button, and explicit **Sync with GitHub** button are implemented. The `catalog/` folder is shared in this repository; `.shelf/` is still a local cache. Clone/pull the repository on the PC and configure GitHub authentication there. Verify a round trip: sync on the Mac, see the catalog on the PC, download a missing PDF, add/rate a PC paper, sync there, and sync again on the Mac. Check Windows Git/SSH availability and download behavior along with the remaining Acrobat integration above.
