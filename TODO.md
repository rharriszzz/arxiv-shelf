# Verification follow-up

Python 3.14 is selected by all launchers. The Windows-to-WSL launcher, Downloads detection, local PDF opening and preview, catalog display, temporary-copy ratings, and browser controls were verified on this PC. See [the November migration report](docs/PYTHON_MODERNIZATION_2026-11.md) for test results, API evidence, and platform limits.

Remaining checks:

- On the Mac, follow the current README setup, then verify Finder startup, browser opening, catalog/ratings, Acrobat opening, and Control-C shutdown with Python 3.14.
- For optional native Windows use, install Python 3.14 and create a separate native checkout/environment; this PC currently uses WSL Python. Its missing-runtime error was verified.
- Live API/download success remains unverified after the November HTTP 429. Testing stopped on that response; do not run repeated probes or cache-busting requests.
- A real Mac-to-PC GitHub catalog/rating sync round trip remains a manual cross-computer check. The automated suite verifies exchange/merging with temporary Git repositories and preservation of unrelated edits.

The September HTTP 406 experiments, including Poppler/legacy-ID and earlier PC/Mac results, are retained in [MAC_API_TEST.md](MAC_API_TEST.md) as historical evidence. Use README for current installation and testing commands.
