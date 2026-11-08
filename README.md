# arXiv Shelf

A local, searchable index of arXiv PDFs in your Downloads folder. See paper titles, all authors, filenames and publication dates; search across those fields and abstracts; sort the library; and click a title or **Open PDF** to read the local PDF.

## Install and run (Python 3.14)

Python **3.14** is the supported runtime on Windows, WSL2, and macOS. No Python packages or build step are required. Clone this repository, or run `git pull --ff-only` in your existing clean checkout, then follow the procedure for your platform below. Keep `catalog/` and `.shelf/` when upgrading: they contain your catalog/ratings and local metadata cache.

Launchers prefer the project's `.venv` and verify that the interpreter is Python 3.14 before starting. If an existing `.venv` uses another version, move it aside and create a fresh one using the commands below. Do not replace Ubuntu's or macOS's system interpreter. Do not share a virtual environment between Windows, WSL, and macOS; create one in each checkout.

### Windows PC using WSL2

Install [uv with its user installer](https://docs.astral.sh/uv/getting-started/installation/) inside WSL if needed. In the repository directory, install a user-managed Python and create the environment:

```sh
~/.local/bin/uv python install 3.14
~/.local/bin/uv venv --python 3.14 --managed-python .venv
./"Start arXiv Shelf.sh"
```

For later launches, double-click `Start arXiv Shelf.bat` from the WSL checkout in Windows Explorer, or run the `.sh` launcher. It opens **http://127.0.0.1:8765** in your Windows browser. Keep the terminal open; press Ctrl-C to stop. Windows Downloads is detected automatically, including redirected folders. Use `--directory PATH` to select another folder.

**Open PDF** opens Windows Acrobat when installed, otherwise your default Windows PDF application. `--acrobat-app 'C:\path\to\Acrobat.exe'` overrides the executable. Browser preview also works. For legacy numeric filenames, install the optional extractor inside WSL with `sudo apt install poppler-utils`.

### Native Windows

Install **Python 3.14** from [python.org](https://www.python.org/downloads/windows/), including the Python launcher. In a terminal in your native Windows checkout:

```bat
py -3.14 -m venv .venv
".venv\Scripts\python.exe" --version
"Start arXiv Shelf.bat"
```

For later launches, double-click the `.bat` file. A native Windows installation of Poppler can provide `pdftotext.exe` on PATH for legacy IDs.

### macOS

Install **Python 3.14** using the [python.org macOS installer](https://www.python.org/downloads/macos/). Use Adobe Acrobat / Acrobat Reader for **Open PDF**. In Terminal in the repository directory:

```sh
python3.14 -m venv .venv
./"Start arXiv Shelf.command"
```

For later launches, double-click `Start arXiv Shelf.command` in Finder. It uses the same explicit Python 3.14 selection as the shell launcher and opens the server's actual URL after startup, including when you pass `--port`. Leave the terminal running; press Control-C to stop.

The first scan retrieves titles and authors from arXiv and may take a few minutes. Subsequent scans reuse cached metadata. Click **Rescan folder** after downloading or moving files. Duplicate downloads and different versions remain separate entries so you can open the exact file you want.

For older numeric filenames such as `0410144.pdf`, the app uses `pdftotext` to recover the subject prefix from the first page. Install Poppler if this command isn't already available (`brew install poppler`, or `sudo port install poppler` with MacPorts). Without it, modern filenames still work; ambiguous older files appear under **Needs attention**.

### Options

```sh
.venv/bin/python shelf.py --directory ~/Documents/Papers --recursive
.venv/bin/python shelf.py --offline
.venv/bin/python shelf.py --scan-only
.venv/bin/python shelf.py --port 8766
.venv/bin/python shelf.py --acrobat-app "Adobe Acrobat Reader"
```

- `--directory`: scan another folder (defaults to `~/Downloads`).
- `--recursive`: include subfolders (off by default).
- `--offline`: use cached metadata without network requests.
- `--scan-only`: build/update the cache and exit without starting the browser interface.
- `--cache PATH`: choose another cache file (defaults to `.shelf/index.json`).
- `--acrobat-app`: set the installed macOS application name or path. The default also detects `/Applications/Adobe Acrobat DC/Adobe Acrobat.app`.

## How it works

Filename matching recognizes modern IDs, optional versions, browser duplicate suffixes like ` (1)`, `arXiv_` prefixes, and older numeric or subject-prefixed IDs. It intentionally excludes arbitrary renamed PDFs and unrelated filenames. Matching a filename identifies a candidate, not proof of origin.

Accurate titles, authors, dates and abstracts come from the [arXiv Atom API](https://info.arxiv.org/help/api/user-manual.html), using batches of 25 IDs spaced at least three seconds apart. Versioned filenames request that specific version; unversioned filenames use the current arXiv metadata. PDFs are never uploaded, modified, moved or deleted. Paper identifiers, and occasionally the opening title block for an unresolved legacy PDF, are sent to arXiv.

Metadata and local paths are saved under `.shelf/`, which is ignored by Git. The server listens only on `127.0.0.1`; opening PDFs requires a session token and a file already in the index. PDFs open through macOS `open`, Windows Acrobat (with a default-app fallback), or Linux `xdg-open`. WSL converts local paths before asking Windows to open them. **Browser preview** is also available.

Unavailable metadata stays visible with a **Needs metadata** label and is retried on rescan. For an old PDF without an arXiv stamp, the app also tries a title search using the opening text block and accepts a result only if its legacy number matches the filename. If neither method succeeds, it stays unresolved. Rename it to its full ID, e.g. `hep-th_0401056.pdf`, once you have verified the prefix. A PDF-header check flags obvious failed downloads, but is not a full integrity check: Acrobat may still report damage in a file whose header is valid.

Search uses all typed words, ignoring case. Sorting by author uses the first author. **Needs attention** includes missing metadata and obvious failed downloads. Expand **Paper details** for the abstract, metadata notes, and an arXiv link.

## Development

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check web/app.js
node tests/test_download_ui.js
```

On native Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. Node.js is needed only for JavaScript checks. GitHub Actions runs the complete standard-library suite on Python 3.14 for Linux, Windows, and macOS, plus the JavaScript checks. Runtime policy tests prevent obsolete versions from returning in current launchers, instructions, and configuration; historical diagnostics are excluded.

The app uses Python's standard library and plain HTML/CSS/JavaScript. Tests cover filename recognition, legacy ID recovery, metadata parsing, duplicate handling, cached/offline scans, network failures, subfolders, symlink boundaries, and HTTP launch protections.

## One library on your Mac and PC

The portable **catalog/** folder is now stored in this Git repository. It remembers papers even when their PDFs are deleted, moved, or only exist on another computer. Your existing local index is migrated automatically on the first run. Local duplicates stay separate when present; an unavailable paper edition appears once. Different arXiv versions are separate editions and have separate ratings.

Use **Sync with GitHub** before switching computers, and again after opening the shelf on the other computer. Sync commits only catalog changes, pulls the other computer's updates, then pushes your changes. It needs Git and working authentication for `origin` on each computer. It reports authentication/network errors without discarding your local catalog. If you have uncommitted application code changes, commit or stash them in your terminal first. If a pull updates application code, restart the app to load that code.

On the PC, clone this repository (or pull the latest changes in an existing checkout), then use the launcher for your platform described above. The catalog comes with the repository; `.shelf/` stays local and is not shared. Windows and WSL support Downloads detection, Acrobat opening, and the double-click launcher described above.

Each entry has a **Not rated / 1–5 stars** selector. Ratings save immediately on this computer and travel to the other one at the next GitHub sync. Choose **Rating** in the sort menu, or **Rated papers** in the filter.

Entries say **On this computer** or **Not on this computer**. A missing paper with a known arXiv ID has a **Download PDF** button. It downloads from arXiv into the selected local Downloads folder and rescans so you can open it. Versioned entries request that version; unversioned entries request the current PDF. The row shows connection, transfer, and indexing progress; when the server provides a file size, it shows a percentage, otherwise bytes received. After indexing finishes, the button switches to **Open PDF** and browser preview becomes available. Failures remain visible and the button allows a retry. If the Python PDF request receives HTTP 406, the app makes one spaced retry using `curl` when installed; other HTTP errors are not retried automatically. Existing files are never overwritten. Failed, non-PDF, incomplete, and oversized (over 200 MB) responses are rejected. An unresolved legacy ID needs to be identified before downloading.

Catalog events contain titles, authors, abstracts, arXiv IDs, filenames, and ratings—no PDFs or absolute local paths. Anyone who can read your GitHub repository can read the catalog. Independent updates use unique event files so Git can merge additions from both computers. If the same rating changes on both computers before syncing, the update with the later computer timestamp wins; keep both system clocks accurate. Sync is explicit, not automatic background uploading.

Advanced: `--catalog PATH` selects a different portable catalog directory. The built-in GitHub sync button requires that directory to be inside the app repository. Back up or sync the entire catalog directory, and do not edit/delete individual event files. Other synchronized folders can be used with an external file-sync service, without using the GitHub button.

## Browser edition

The `dist/` folder is a static, owner-private browser edition of the catalog. It supports searching, filtering, sorting, abstracts, local browser ratings, and opening papers on arXiv. It does not access a computer's Downloads folder or host PDF files; the desktop app above keeps its full local workflow. Before publishing an updated catalog snapshot, run `.venv/bin/python scripts/build_web_catalog.py` and commit the resulting `dist/catalog.json` with the rest of the changes. Ratings in the browser are saved in that browser only.

### Public project landing page

[rharriszzz.github.io/arxiv-shelf](https://rharriszzz.github.io/arxiv-shelf/) is a public introduction and doorway to the [OpenAI-hosted browser edition](https://arxiv-shelf-library.rharriszzz.chatgpt.site), which may require permission to access. It includes a real screenshot of the live browser edition and links to the source for cloning, running, and adapting the fuller local application described above.

The landing page is plain HTML/CSS in `docs/`, published by `.github/workflows/pages.yml` through GitHub Actions (Settings → Pages → Source: **GitHub Actions**). Only `docs/` is uploaded; `.openai/hosting.json` continues to deploy the browser application from `dist/`. To preview the landing page independently, run `.venv/bin/python -m http.server 8000 --directory docs`; it does not need the arXiv Shelf server.

## Runtime and API investigation

The supported version is pinned in `.python-version`; a version file alone does not change the interpreter used by a desktop launcher. See [the November migration report](docs/PYTHON_MODERNIZATION_2026-11.md) for verification results and remaining platform checks.

[MAC_API_TEST.md](MAC_API_TEST.md) and the September JSON reports in `diagnostics/` are historical experiments, not current installation instructions. Their results mix interpreter/TLS, HTTP client, network, timing, and cache differences; they do not establish a required older Python runtime. To investigate a new API failure, stop the shelf and run one bounded probe with Python 3.14:

```sh
.venv/bin/python diagnostics/arxiv_probe.py --suite baseline --output /tmp/arxiv-probe.json
```

Use a new report filename (and an appropriate temporary path on Windows). The probe makes at most three sequential requests spaced 3.2 seconds after completion, writes no catalog data, and stops on HTTP 403 or 429. Stop further live API/download testing after an explicit block or throttle. Do not add cache-busting parameters or retry loops. The November probe stopped after its first request returned HTTP 429; it could not establish whether the earlier 406 issue is resolved.
