# arXiv Shelf

A local, searchable index of arXiv PDFs in your Downloads folder. See paper titles, all authors, filenames and publication dates; search across those fields and abstracts; sort the library; and click a title or **Open in Acrobat** to read the local PDF.

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

Metadata and local paths are saved under `.shelf/`, which is ignored by Git. The server listens only on `127.0.0.1`; opening PDFs requires a session token and a file already in the index. Acrobat is launched directly via macOS `open`, so the browser's default PDF viewer does not need to change. **Browser preview** is also available. Acrobat launching is macOS-specific; indexing and browser preview work on other systems if Python is available.

Unavailable metadata stays visible with a **Needs metadata** label and is retried on rescan. For an old PDF without an arXiv stamp, the app also tries a title search using the opening text block and accepts a result only if its legacy number matches the filename. If neither method succeeds, it stays unresolved. Rename it to its full ID, e.g. `hep-th_0401056.pdf`, once you have verified the prefix. A PDF-header check flags obvious failed downloads, but is not a full integrity check: Acrobat may still report damage in a file whose header is valid.

Search uses all typed words, ignoring case. Sorting by author uses the first author. **Needs attention** includes missing metadata and obvious failed downloads. Expand **Paper details** for the abstract, metadata notes, and an arXiv link.

## Development

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
```

The app uses Python's standard library and plain HTML/CSS/JavaScript. Tests cover filename recognition, legacy ID recovery, metadata parsing, duplicate handling, cached/offline scans, network failures, subfolders, symlink boundaries, and HTTP launch protections.
