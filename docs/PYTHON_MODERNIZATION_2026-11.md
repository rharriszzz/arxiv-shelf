# Python modernization — November 7, 2026

## Supported runtime and original dependencies

Python **3.14** is the supported development and execution runtime on Windows,
WSL2, and macOS. Use a project virtual environment or user-managed installation;
leave operating-system interpreters alone. See [current setup instructions](../README.md).

Work resumed from clean `master` at `fb8da95`; a fetch and fast-forward-only pull
confirmed it matched `origin/master`. An existing Python 3.14.4 project `.venv`
was reused. Its base interpreter already existed; this migration did not install,
replace, or remove an OS interpreter.

Reviewed README, all three launchers, `.python-version`, `shelf.py`, `catalog.py`,
`desktop.py`, `sync.py`, `transfer.py`, every existing test, configuration, and
the September API scripts/reports and [Mac/PC investigation](../MAC_API_TEST.md).

Originally the application advertised Python 3.10+, while the PC launchers and
version file selected 3.12. The Mac launcher invoked an unqualified `python3`.
The application uses the standard library; no package dependency requires 3.12.
For example, `Path.is_relative_to` needs Python 3.9 and `time.time_ns` needs 3.7;
these are lower bounds, not reasons to preserve an older supported runtime.
Poppler, Git, Acrobat/default PDF apps, and the optional PDF curl transport are
external desktop tools, independent of a particular Python minor version.

The September PC pin was a runtime/TLS workaround: Python 3.10.12 with OpenSSL
3.0.2 failed on one uncached URL, while Python 3.12.14 with OpenSSL 3.5.8 succeeded.
Python and TLS changed together. Subsequent success under the older interpreter
was a cache hit. That experiment did not establish Python 3.12 as an application
requirement or isolate the source of HTTP 406.

## Changes

- Pin `.python-version` to 3.14 and verify the interpreter before direct app startup.
- Prefer `.venv` in both desktop launcher paths; verify every candidate is exactly
  Python 3.14. Other candidates are explicitly versioned user/installed locations
  or, on Windows, `py -3.14` and a version-checked PATH interpreter. No older
  interpreter fallback remains. Missing-runtime errors link to setup guidance.
- Share the POSIX selection between WSL/Linux and the Finder launcher. Finder
  forwards arguments and uses the application's browser opening after server
  startup, including its selected port, instead of a timed hard-coded URL.
- Fix Windows-to-WSL handoff bugs found by running the actual batch file: replace
  the failing `findstr` UNC-prefix test, extract the distribution from the correct
  path component, and pass its name without surrounding quotation marks (which
  this PC's WSL distribution parser treated literally). Preserve the app's exit
  status through the terminal pause.
- Replace current installation/development commands with Python 3.14 setup and
  project-environment commands; remove the personal Downloads path from README.
  Mark September handoffs as historical without altering their measured results.
- Ignore `.venv/`. Keep catalog events, local cache data, PDF files, the separately
  hosted browser edition, and hosting configuration unchanged.
- Stop legacy-title recovery after an HTTP error, report it, and skip remaining
  title/ID lookups in that scan. Previously this path silently continued after
  denial or throttling. Close HTTP-error response resources in scans and probes.
- Handle browser-cancelled HTTP responses quietly. Browser navigation during the
  smoke test exposed broken-pipe tracebacks; expected disconnects now leave the
  server running, while other I/O failures are still reported.
- Add [CI](../.github/workflows/tests.yml) on every push and pull request using
  Python 3.14 on Linux, Windows, and macOS, with `actions/setup-python@v7` and
  `actions/checkout@v7`. A separate Node job runs browser JavaScript checks.
  [Upstream setup-python releases](https://github.com/actions/setup-python/releases)
  were checked before selecting the maintained action major.
- Add policy tests scanning current instructions, launchers, source, and runtime
  configuration for older version selections. Check the version pin and CI
  runtime. Exclude September diagnostics and this historical migration report.

## Tests performed

Local runtime: CPython **3.14.4**, OpenSSL **3.5.5**, WSL2. Tests use temporary
fixtures and a local bare Git remote; they make no live arXiv requests and publish
no catalog data. Playwright was installed only into the ignored local environment
for an additional browser smoke test; the app and standard-library test suite
do not require it.

- Baseline: all 28 existing Python unit tests and both JavaScript tests passed.
- Final standard-library suite: **40 tests, 39 passed, one native Windows-only
  test skipped on WSL**. The actual Windows-to-WSL batch integration test passed,
  including paths with spaces and a project environment. POSIX launcher tests
  cover restricted PATH, arguments/port, a rejected environment, user-managed
  discovery, and actionable failure when 3.14 is absent.
- Existing coverage passed for PDF filenames and legacy/modern IDs, versions,
  Atom metadata, cache/offline scans, duplicate PDFs, symlink boundaries, catalog
  merging and aliases, rating save/clear, local PDF opening, downloads and progress,
  failed/incomplete transfers, and Git synchronization without touching unrelated
  edits. Added deterministic timestamp/ID event ordering and separate edition
  ratings, plus HTTP 403/429/406 legacy-recovery stop regressions.
- Local HTTP server tests passed for session-token/Host protections and opening
  only indexed files, plus cancelled headers/body writes. Error responses are
  explicitly closed in the tests.
- `node --check web/app.js` and `node tests/test_download_ui.js`: passed, including
  progress, successful indexing/button transition, and visible failure/retry.
- Shell syntax and `git diff --check`: passed.
- The first hosted CI run passed Linux, native Windows (including batch startup),
  and JavaScript checks. It exposed an existing Windows PDF test that mocked WSL
  without setting the platform, so macOS correctly entered its own opening branch.
  The fixture now explicitly models Linux/WSL, and a separate test covers the
  macOS opening command and missing-application error. These are mocked desktop
  command checks, not interactive native Mac verification.

## Actual PC and platform verification

The real Windows `.bat` was invoked through Windows PowerShell against the WSL
checkout, rather than substituting the shell launcher. It selected the project's
Python 3.14 environment, detected Windows Downloads automatically, and started
the loopback server at a test port. The desktop browser command succeeded and a
Windows browser window titled arXiv Shelf was detected.

Used disposable copies of the existing catalog and cache, offline after the API
throttle described below. The real library displayed **234 entries**, including
**eight local PDFs** and **226 unavailable editions**. Existing rating values
matched the source catalog. No source entry had a nonzero rating, so a temporary
four-star rating was saved, checked on disk and after browser reload, and cleared
only in the disposable copy.

Headless Chromium against that running server verified search, filtering,
sorting, empty results, rating controls, local PDF preview with real PDF bytes,
and a successful **Open PDF** request through the actual Windows desktop/Acrobat
integration. This checks that Windows accepted the opening command; it does not
independently inspect Acrobat's rendered document. Unavailable entries offered
download rather than local preview; clicking download offline produced the
expected error and re-enabled the button, without an external request. The
browser test recorded no JavaScript errors or external requests.

SIGINT (the signal delivered by Ctrl-C) closed the server port without a
traceback. Hashes and the complete file list confirmed the original catalog and
local cache were unchanged; no events were added or removed. No personal PDF
was downloaded, moved, edited, or deleted.

Native Windows: no suitable Python 3.14 installation or Python launcher was
found. Running the batch file from a native temporary folder correctly displayed
Python 3.14 installation guidance and exited with status 1. Full native Windows
app execution on this PC is therefore unverified; CI includes a native batch
startup test with a Python 3.14 project environment.

macOS: the Finder script and shared selection were inspected for compatibility
with macOS's shell and explicit framework/Homebrew/user locations. **No native
macOS/Finder/Acrobat test was performed in this PC session.** CI tests Python on
macOS and exercises the Finder wrapper when zsh is available, but cannot establish
interactive Finder or Acrobat behavior on the user's Mac.

The static browser edition in `dist/` and `.openai/hosting.json` were not changed
or redeployed.

## HTTP 406 investigation

One live call was made with the existing `diagnostics/arxiv_probe.py` baseline
suite, using Python 3.14.4 and the unchanged application's urllib request code:

| UTC | Request | Result | Cache | Retry-After |
| --- | --- | --- | --- | --- |
| 2026-11-08 01:03:58 (Nov 7 locally) | Original single-ID diagnostic URL | HTTP 429 | MISS, MISS, MISS | absent |

The probe stopped immediately, before its other two cases. No live curl, other
interpreter, network-switch, PDF-download, or repeat API tests followed. This
respects the stop-on-throttling requirement and
[arXiv API terms](https://info.arxiv.org/help/api/tou.html). The sanitized report is
[pc-python314-2026-11-07.json](../diagnostics/pc-python314-2026-11-07.json).
It records the base commit, exact public diagnostic URL, runtime/TLS, UTC,
selected headers, and proxy presence only; it contains no credentials, personal
paths, response body, or catalog contents. No proxy environment configuration
was reported. VPN/transparent-network conditions were not independently verified.

**HTTP 406 was not observed; resolution is unproven because HTTP 429 prevented
a useful comparison.** A nonempty HTML throttle response on a cache miss differs
from September's empty 406 responses. Its headers alone cannot identify which
service or intermediary generated it or establish a Python defect.

September evidence distinguishes several variables without proving a cause:

- Interpreter/TLS: changed together in the successful 3.12 comparison.
- HTTP client: WSL curl succeeded on a miss after urllib failed on the same URL;
  both then used the same OpenSSL release, but request/TLS handling could differ.
- Cache/timing: later urllib calls succeeded on hits; Mac calls also succeeded
  on misses, so misses were not universally broken.
- Network/service: geography, routes, transparent proxies, changing edge behavior,
  and transient service conditions were not controlled sufficiently.

No metadata transport fallback, header alteration, cache-busting parameter, or
automatic retry was added. The pre-existing PDF-only single curl retry after
406 remains bounded and tested; it never retries 403 or 429 and does not select
another Python runtime. Its docstring no longer asserts an established cause.
The only arXiv request-handling correction is stopping the previously continuing
legacy lookup path on HTTP failure.

## Remaining manual work and installed interpreters

- This PC's WSL checkout is ready to use with its existing 3.14 project environment.
  The verification server has been stopped. Fresh live metadata/download success
  remains unverified after the throttle; do not run repeated probes to force it.
- For native Windows use, install Python 3.14 and create a separate Windows `.venv`
  in a native checkout, following README. This is optional for the WSL workflow.
- On the Mac, pull the changes, install user-managed Python 3.14, create/recreate
  `.venv`, and verify Finder startup, browser opening, existing catalog/ratings,
  Acrobat opening, and clean Control-C shutdown. Keep catalog/cache files.
- A user-managed Python **3.12.14** installation still exists and another project's
  environment uses it. It is no longer selected by arXiv Shelf. No installation
  was deleted or altered; review dependent projects before deciding to remove it.
  The current WSL system Python already resolves to 3.14; the historical system
  Python 3.10 observation is not a description of this session's machine state.
