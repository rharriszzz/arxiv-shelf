# arXiv Shelf

A local, searchable index of arXiv PDFs in your Downloads folder. See paper titles, all authors, filenames and publication dates; search across those fields and abstracts; sort the library; and click a title or **Open PDF** to read the local PDF.

## Run on this Windows PC (WSL)

Double-click `Start arXiv Shelf.bat` in this folder in Windows Explorer, or run:

```sh
./"Start arXiv Shelf.sh"
```

The launcher uses WSL's installed Python 3.12 and opens **http://127.0.0.1:8765** in your Windows browser. Keep the terminal open while using the shelf; press Ctrl-C to stop. Windows Downloads is detected automatically, including redirected folders. On this PC it is `/mnt/c/Users/rharr/Downloads`. Use `--directory PATH` to select another folder.

**Open PDF** opens Windows Acrobat when installed, otherwise your default Windows PDF application. `--acrobat-app 'C:\path\to\Acrobat.exe'` overrides the executable. Browser preview also works.

This PC has Python 3.12 at `~/.local/bin/python3.12`; the launcher also finds it when Windows starts WSL without loading a shell profile. The project pins `3.12` in `.python-version`. Direct runs on this PC should use `python3.12 shelf.py`. Its system `python3` is 3.10 and returned HTTP 406 on uncached arXiv requests; the same request succeeded with the installed 3.12 runtime. See [the diagnostic results](MAC_API_TEST.md) for evidence and limitations.

For legacy numeric filenames, install the optional extractor inside WSL with `sudo apt install poppler-utils`. Without it, those papers may need their full arXiv ID added to the filename.

For a native Windows checkout, install Python 3.12 and double-click the same `.bat` launcher, or run `py -3.12 shelf.py --open-browser`. No Python packages are required. A native Windows installation of Poppler can provide `pdftotext.exe` on PATH for legacy IDs.

## Run on macOS

Requires Python 3.10 or newer and Adobe Acrobat / Acrobat Reader. No Python packages or build step are needed.

```sh
python3 shelf.py
```

Open **http://127.0.0.1:8765** in your browser. Leave the terminal running; press Control-C to stop. Alternatively, double-click `Start arXiv Shelf.command` in Finder. The launcher opens the browser automatically.

The first scan retrieves titles and authors from arXiv and may take a few minutes. Subsequent scans reuse cached metadata. Click **Rescan folder** after downloading or moving files. Duplicate downloads and different versions remain separate entries so you can open the exact file you want.

For older numeric filenames such as `0410144.pdf`, the app uses `pdftotext` to recover the subject prefix from the first page. Install Poppler if this command isn't already available (`brew install poppler`, or `sudo port install poppler` with MacPorts). Without it, modern filenames still work; ambiguous older files appear under **Needs attention**.

### Options

```sh
python3 shelf.py --directory ~/Documents/Papers --recursive
python3 shelf.py --offline
python3 shelf.py --scan-only
python3 shelf.py --port 8766
python3 shelf.py --acrobat-app "Adobe Acrobat Reader"
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
python3 -m unittest discover -s tests -v
node --check web/app.js
node tests/test_download_ui.js
```

The app uses Python's standard library and plain HTML/CSS/JavaScript. Tests cover filename recognition, legacy ID recovery, metadata parsing, duplicate handling, cached/offline scans, network failures, subfolders, symlink boundaries, and HTTP launch protections.

## One library on your Mac and PC

The portable **catalog/** folder is now stored in this Git repository. It remembers papers even when their PDFs are deleted, moved, or only exist on another computer. Your existing local index is migrated automatically on the first run. Local duplicates stay separate when present; an unavailable paper edition appears once. Different arXiv versions are separate editions and have separate ratings.

Use **Sync with GitHub** before switching computers, and again after opening the shelf on the other computer. Sync commits only catalog changes, pulls the other computer's updates, then pushes your changes. It needs Git and working authentication for `origin` on each computer. It reports authentication/network errors without discarding your local catalog. If you have uncommitted application code changes, commit or stash them in your terminal first. If a pull updates application code, restart the app to load that code.

On the PC, clone this repository (or pull the latest changes in an existing checkout), then run `python shelf.py` or `py shelf.py`. The catalog comes with the repository; `.shelf/` stays local and is not shared. Windows and WSL support Downloads detection, Acrobat opening, and the double-click launcher described above.

Each entry has a **Not rated / 1–5 stars** selector. Ratings save immediately on this computer and travel to the other one at the next GitHub sync. Choose **Rating** in the sort menu, or **Rated papers** in the filter.

Entries say **On this computer** or **Not on this computer**. A missing paper with a known arXiv ID has a **Download PDF** button. It downloads from arXiv into the selected local Downloads folder and rescans so you can open it. Versioned entries request that version; unversioned entries request the current PDF. The row shows connection, transfer, and indexing progress; when the server provides a file size, it shows a percentage, otherwise bytes received. After indexing finishes, the button switches to **Open PDF** and browser preview becomes available. Failures remain visible and the button allows a retry. If the Python PDF request receives HTTP 406, the app makes one spaced retry using `curl` when installed; other HTTP errors are not retried automatically. Existing files are never overwritten. Failed, non-PDF, incomplete, and oversized (over 200 MB) responses are rejected. An unresolved legacy ID needs to be identified before downloading.

Catalog events contain titles, authors, abstracts, arXiv IDs, filenames, and ratings—no PDFs or absolute local paths. Anyone who can read your GitHub repository can read the catalog. Independent updates use unique event files so Git can merge additions from both computers. If the same rating changes on both computers before syncing, the update with the later computer timestamp wins; keep both system clocks accurate. Sync is explicit, not automatic background uploading.

Advanced: `--catalog PATH` selects a different portable catalog directory. The built-in GitHub sync button requires that directory to be inside the app repository. Back up or sync the entire catalog directory, and do not edit/delete individual event files. Other synchronized folders can be used with an external file-sync service, without using the GitHub button.
