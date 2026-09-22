# Requested Mac test: arXiv HTTP 406

Please run this comparison on the Mac after pulling this commit, and record the
results here. The user requested this handoff on September 22, 2026. Do not assume
that the Mac succeeds just because its catalog already contains metadata.

## Observed on the Windows PC (WSL)

On September 22, 2026, around 19:27–19:29 UTC:

- The unchanged `shelf.fetch_metadata(['1512.03547v2'])` succeeded.
- A two-paper batch (`1512.03547v2`, `1809.00533v6`) returned HTTP 406.
- The six-paper batch below also returned HTTP 406.
- The failing response had an empty body, `cache-control: private, no-store`,
  `Via: 1.1 varnish, 1.1 varnish`, and `X-Cache: MISS, MISS`.
- Using literal commas and slashes instead of percent encoding in the six-paper
  URL also returned 406.
- Earlier single-paper attempts had returned 406 too, so the failure may vary
  over time. A network, edge-filtering, or API issue is suspected, not established.
- Poppler is installed and identifies the legacy PDF correctly. This is separate
  from the metadata HTTP failure.

## Run on the Mac

Run from the repository directory with the shelf stopped to avoid overlapping
API requests. This uses the real application request code, does not alter the
catalog, and spaces requests by more than three seconds.

```sh
python3 - <<'PY'
from datetime import datetime, timezone
import platform
import time
from urllib.error import HTTPError
from shelf import fetch_metadata

cases = [
    ('single', ['1512.03547v2']),
    ('two-paper batch', ['1512.03547v2', '1809.00533v6']),
    ('six-paper batch', ['quant-ph/0501052v1', '1512.03547v2',
                         '1809.00533v6', '2308.15440v2',
                         '2412.16795v1', '2502.03337v1']),
]
print('UTC:', datetime.now(timezone.utc).isoformat())
print('Platform:', platform.platform(), 'Python:', platform.python_version())
for i, (label, ids) in enumerate(cases):
    if i:
        time.sleep(3.2)
    print('\nCASE:', label, ids, flush=True)
    try:
        result = fetch_metadata(ids)
        print('SUCCESS:', len(result), 'records')
        for identifier, metadata in result.items():
            print(identifier, metadata['title'])
    except HTTPError as exc:
        print('HTTP:', exc.code, exc.reason)
        for header in ('Content-Type', 'Cache-Control', 'Via', 'Date',
                       'X-Served-By', 'X-Cache', 'Retry-After'):
            print(header + ':', exc.headers.get(header, '(absent)'))
        print('BODY:', repr(exc.read(4000).decode('utf-8', errors='replace')))
    except Exception as exc:
        print(type(exc).__name__ + ':', str(exc))
PY
```

Record the output, commit tested (`git rev-parse HEAD`), and whether a VPN/proxy
was enabled. Do not publish IP addresses or credentials. If the Mac succeeds,
repeat the comparison on the PC at approximately the same time before attributing
the difference to operating system or network. If batches fail on both, consider
individual lookups with the required delay; that workaround has not been added.

## Official references checked

- [API manual, errors](https://info.arxiv.org/help/api/user-manual.html#34-errors):
  no 406-specific explanation found.
- [API terms](https://info.arxiv.org/help/api/tou.html): at most one request every
  three seconds, one connection at a time.
- [Robots guidance](https://info.arxiv.org/help/robots.html): discusses access
  denial using 403, not an explanation of this 406.
- [Operational status](https://status.arxiv.org/): export.arxiv.org was listed as up
  when checked on September 22, 2026.

## Mac results

Tested commit: `0dc8f46aaaa500625e95fe2a0dd096a6bf907e35`.

The shelf server was stopped before running the exact comparison above. These
were live calls through `shelf.fetch_metadata`, not cached catalog reads. Requests
were sequential with the specified 3.2-second pauses. The comparison itself did
not modify the catalog.

Network checks: no HTTP_PROXY, HTTPS_PROXY, ALL_PROXY (or lowercase equivalents)
environment variables were set. `scutil --proxy` reported no enable flags, and
`scutil --nc list` reported zero connected VPN configurations. A third-party VPN
or transparent network proxy has not been independently ruled out; no IP
addresses or credentials were collected in this report.

```text
UTC: 2026-09-22T19:34:16.272259+00:00
Platform: macOS-26.6.2-arm64-arm-64bit Python: 3.12.3

CASE: single ['1512.03547v2']
SUCCESS: 1 records
1512.03547v2 Graph Isomorphism in Quasipolynomial Time

CASE: two-paper batch ['1512.03547v2', '1809.00533v6']
SUCCESS: 2 records
1809.00533v6 A detailed proof of the Chudnovsky formula with means of basic complex analysis -- Ein ausführlicher Beweis der Chudnovsky-Formel mit elementarer Funktionentheorie
1512.03547v2 Graph Isomorphism in Quasipolynomial Time

CASE: six-paper batch ['quant-ph/0501052v1', '1512.03547v2', '1809.00533v6', '2308.15440v2', '2412.16795v1', '2502.03337v1']
SUCCESS: 6 records
1809.00533v6 A detailed proof of the Chudnovsky formula with means of basic complex analysis -- Ein ausführlicher Beweis der Chudnovsky-Formel mit elementarer Funktionentheorie
1512.03547v2 Graph Isomorphism in Quasipolynomial Time
2412.16795v1 Introduction to Black Hole Thermodynamics
quant-ph/0501052v1 Introduction to PT-Symmetric Quantum Theory
2308.15440v2 Detecting single gravitons with quantum sensing
2502.03337v1 Corrections to Kerr-Newman black hole from Noncommutative Einstein-Maxwell equation
```

Conclusion: all three requests succeeded on this Mac at the recorded time. The
PC failures at 19:27–19:29 UTC were not reproduced here at 19:34 UTC. This does
not establish an operating-system difference: timing, networking, and API edge
behavior remain possible explanations.

Next PC action: pull this result and repeat the same comparison, recording UTC
time and outcomes. No individual-lookup fallback or request-code change was
made on the Mac.

## PC follow-up after pulling Mac results

Pulled `8daea1e` on September 22, 2026. No application request changes were made.
The shelf server was not running during these probes. Full reports are saved in
`diagnostics/pc-2026-09-22-repeat.json` and
`diagnostics/pc-2026-09-22-order.json`.

| UTC (2026-09-22) | Request | HTTP | X-Cache |
| --- | --- | --- | --- |
| 19:38:48 | Original single | 200 | MISS, MISS, HIT |
| 19:38:49 | Original two-paper batch | 200 | MISS, MISS, HIT |
| 19:38:52 | Original six-paper batch | 200 | MISS, MISS, HIT |
| 19:39:24 | Same two papers, reverse order | 406 | MISS, MISS |
| 19:39:27 | Same six papers, reverse order | 406 | MISS, MISS |
| 19:39:30 | Original two-paper control | 200 | MISS, MISS, HIT |

Successful results contained every requested edition. Failing responses again
had empty bodies and `Cache-Control: private, no-store`.

This is evidence against a general batch-size problem or complete API recovery.
Success correlates with a cache HIT, while equivalent requests with a different
ordering fail on a MISS. The Mac may have populated shared caches for the original
URLs, but we have not established that. Ordering-sensitive filtering, different
network routes, and upstream/cache behavior remain competing explanations.
The available headers cannot identify which component generated the 406.

## Next tests requested on the Mac

Use the reusable probe (no catalog writes) with the shelf stopped. It uses the
actual `shelf.fetch_metadata` implementation, saves selected response headers on
both success and failure, and waits 3.2 seconds after each completed request.
It makes three requests per suite and stops on 403 or 429. Report files must not
already exist. Proxy presence is recorded without proxy URLs or credentials.
Record VPN status separately; this script does not detect every VPN.

1. **Run the reverse-order suite on the Mac first.** This checks whether the
   exact URLs that just failed on the PC succeed on the Mac:

   ```sh
   python3 diagnostics/arxiv_probe.py --suite order --output diagnostics/mac-order.json
   ```

2. **Record or share the result, then run that same suite on the PC.** Use a new
   filename, such as `diagnostics/pc-after-mac-order.json`. If the reverse-order
   requests change from 406/MISS to 200/HIT after Mac success, that strengthens
   the shared-cache explanation. It does not prove that the Mac caused the
   change; service recovery or other clients can also populate caches.

3. **If an identical URL still differs between machines, compare clients on the
   PC.** Take the exact two-paper URL from the saved report and request it once
   using WSL curl, then Windows `curl.exe`, using the application's user agent:

   ```sh
   curl --max-time 35 -sS -D /tmp/arxiv-wsl-headers.txt -o /tmp/arxiv-wsl-body.xml \
     -A 'arxiv-shelf/1.0 (local personal PDF index)' \
     'https://export.arxiv.org/api/query?id_list=1809.00533v6%2C1512.03547v2&max_results=2'
   ```

   Run the equivalent command in Windows PowerShell with `curl.exe` and Windows
   output paths. Wait at least 3.2 seconds between completed requests. Python
   failure with both curl clients succeeding suggests a client/HTTP/TLS difference;
   WSL clients failing while Windows succeeds suggests a WSL path difference.
   Timing/cache changes still confound a one-off comparison, so retain timestamps
   and headers. Do not change user agent, URL encoding, and client at once.

4. **Only if failures persist, compare network conditions.** Run one suite on each
   machine on the same network with VPN status recorded. If practical, separately
   compare a different network while keeping machine/client unchanged. Stop if
   explicit blocking or rate limiting is returned; do not rotate networks or
   addresses to evade a block. A network-dependent result would support a
   route/egress-related explanation, not establish a Windows defect.

Do not add individual-request fallback yet: earlier singles sometimes failed,
and cache hits could make that workaround look reliable when it is not. Do not
add random query parameters, rapid retries, or cache-busting loops. The fixed
reverse-order suite provides a small, reproducible comparison.

## Mac reverse-order results — September 22, 2026

Ran the requested `order` suite unchanged at commit
`87a42365d595b7121e8a85e645077a444ed1afca` with the shelf stopped. Full machine-readable results, exact URLs,
platform details, and selected headers are in `diagnostics/mac-order.json`.
All requested editions were returned; no IDs were missing.

| UTC (2026-09-22) | Request | HTTP | X-Cache |
| --- | --- | --- | --- |
| 19:43:02 | Reversed two-paper batch | 200 | MISS, MISS, MISS |
| 19:43:06 | Reversed six-paper batch | 200 | MISS, MISS, MISS |
| 19:43:09 | Original two-paper control | 200 | MISS, MISS, HIT |

The probe reported no configured proxies. Separate `scutil --proxy` and
`scutil --nc list` checks both exited successfully: no proxy-enable flags were
reported and zero connected VPN configurations were listed. This does not
independently exclude every third-party VPN or transparent network proxy.

Both exact reverse-order URLs that failed on the PC at 19:39 succeeded on the
Mac at 19:43, including with cache misses. Thus, a cache miss does not universally
cause a 406 response. The outcome remains consistent with several explanations,
including a route/client-dependent upstream response or a change over time.
These observations alone do not identify the source of the 406 or prove that
Mac requests populate a cache subsequently used by the PC.

**Next PC action:** pull this report, stop the shelf, and run:

```sh
python3 diagnostics/arxiv_probe.py --suite order --output diagnostics/pc-after-mac-order.json
```

Compare the exact URLs, timestamps, returned IDs, and cache headers. If the
reversed URLs now return 200/HIT on the PC, that strengthens (but does not prove)
the shared-cache explanation. If identical URLs still fail there, follow the
bounded WSL curl versus Windows curl comparison above. No application request
changes or fallback were added, and the probe made no catalog writes.

## PC results after Mac reverse-order test — September 22, 2026

Pulled `70cff85`. With no shelf server running, the unchanged order suite at
19:45:03–19:45:10 UTC returned 200 for all three requests, all with
`X-Cache: MISS, MISS, HIT` and no missing editions. See
`diagnostics/pc-after-mac-order.json`. This repeats the pattern: PC misses fail,
Mac requests succeed, then PC hits succeed. It strengthens the cache explanation
without establishing causation or a universal recovery.

### Client comparison on this PC

Used one previously untested fixed pair, `2308.15440v2,2412.16795v1`, with
identical URL and application user agent. Both curl clients used HTTP/1.1 to
match urllib's HTTP version. Requests were sequential, spaced by 3.2 seconds
after completion. See `diagnostics/pc-client-comparison.json`.

| UTC | Client | HTTP | X-Cache |
| --- | --- | --- | --- |
| 19:45:53 | WSL Python urllib | 406 | MISS, MISS |
| 19:45:56 | WSL curl 7.81.0 / OpenSSL 3.0.2 | 200 | MISS, MISS, MISS |
| 19:45:59 | Windows curl 8.21.0 / Schannel | 200 | MISS, MISS, HIT |
| 19:46:03 | Same WSL Python urllib again | 200 | MISS, MISS, HIT |

Both Python and WSL curl use OpenSSL 3.0.2 on this PC. The Mac is not necessary
for a successful cache-miss request: WSL curl succeeded. This focuses attention
on client/request/TLS differences and handling of uncached requests, rather
than a blanket WSL or Windows network failure. Windows curl's success was a
cache hit, so it does not establish its behavior on misses.

### Header comparison

Used the reverse of that pair, fixed throughout this comparison. See
`diagnostics/pc-header-comparison.json`.

| UTC | Python request change | HTTP | X-Cache |
| --- | --- | --- | --- |
| 19:46:37 | None (baseline) | 406 | MISS, MISS |
| 19:46:40 | Add `Accept: */*` | 406 | MISS, MISS |
| 19:46:44 | Add `Accept-Encoding: gzip` instead | 406 | MISS, MISS |

Neither individual header change fixes this case. This does not test every
combination or establish TLS as the cause. All failures had empty response
bodies. No application transport or fallback has been changed.

The exact comparison scripts are preserved for reproducibility (output paths
must be new; run from the repository with the shelf stopped):

```sh
python3 diagnostics/client_comparison.py --output diagnostics/pc-clients-repeat.json
python3 diagnostics/header_comparison.py --output diagnostics/pc-headers-repeat.json
```

Run these separately with at least 3.2 seconds between suites. The client script
requires both `curl` and Windows `curl.exe` and is intended for this WSL PC.
Each script stops on 403 or 429. Repeating already successful URLs may only test
cache hits and cannot resolve the remaining cause.

### Next focused investigation

1. Compare Python 3.10 on this PC with a newer Python runtime on the same PC,
   using identical request code, URL, and headers. Record TLS library versions.
   This addresses the runtime difference from the Mac's Python 3.12.3 without
   conflating it with geography or operating system. A cache-hit-only outcome
   is inconclusive.
2. If necessary, compare the HTTP headers actually sent by urllib and curl to a
   local capture server (no external requests). Then test only identified
   differences, keeping HTTP version and user agent fixed. TLS negotiation and
   connection handling remain separate variables.
3. If curl repeatedly succeeds on misses while urllib fails, consider an
   optional, rate-limited curl transport rather than single-paper fallback.
   Validate Atom parsing, timeout/error handling, dependency detection, and the
   existing request protections before adopting it. Do not implement it based
   only on successes served from cache.

We have not proved which arXiv/CDN component issues 406. A support report can
now include the exact URLs, UTC timestamps, client versions, selected response
headers, and the Python-fail / curl-success / Python-hit sequence without IP
addresses or credentials.

## Python 3.12 comparison and PC configuration — September 22, 2026

Found an existing Python 3.12 installation at `~/.local/bin/python3.12` (uv-managed
CPython 3.12.14 with OpenSSL 3.5.8). The system `/usr/bin/python3` is CPython
3.10.12 with OpenSSL 3.0.2. No interpreter installation was needed, and neither
the system interpreter nor the other project's environment was modified.

Used the exact URL from the previously failing header comparison, with unchanged
application request code. The new `runtime` suite makes that one fixed request:

```sh
python3 diagnostics/arxiv_probe.py --suite runtime --output diagnostics/pc-runtime-310-before.json
python3.12 diagnostics/arxiv_probe.py --suite runtime --output diagnostics/pc-runtime-312.json
python3 diagnostics/arxiv_probe.py --suite runtime --output diagnostics/pc-runtime-310-after.json
```

These are the commands already run, not a repeat instruction: the report files
exist. Calls were separated by more than three seconds.

| UTC | Runtime | HTTP | X-Cache |
| --- | --- | --- | --- |
| 19:49:34 | Python 3.10.12 / OpenSSL 3.0.2 | 406 | MISS, MISS |
| 19:49:49 | Python 3.12.14 / OpenSSL 3.5.8 | 200 | MISS, MISS, MISS |
| 19:50:23 | Python 3.10.12 / OpenSSL 3.0.2 again | 200 | MISS, MISS, HIT |

Both successful responses returned the two requested editions. This directly
supports using the existing 3.12 runtime on this PC. It does not isolate Python
version from TLS library/configuration changes, or conclusively identify the
server component rejecting the older runtime's uncached request.

The PC launchers now select Python 3.12 and `.python-version` pins 3.12. The WSL
launcher also checks `~/.local/bin/python3.12` because Windows-launched WSL may
not load the shell profile. This fallback was checked with a restricted PATH.
Native Windows launching selects `py -3.12` or verifies that `python` is 3.12.
No curl fallback or API request-header changes were added to the application.

Validation: all 22 tests pass on Python 3.12; JavaScript and shell syntax checks
pass. A live `python3.12 shelf.py --scan-only` completed successfully with
**6 local files, all 6 with metadata** and no lookup error. This scan persisted
the metadata in the local cache and portable catalog. The scan's successful
URLs may already be cached upstream; the runtime probe above provides the
separate successful cache-miss observation.

## Final Mac verification request

The PC now works with Python 3.12. No further repeated 406 probes are needed
unless the error returns. Please do these compatibility checks after pulling:

1. Confirm which interpreter the Finder launcher actually uses. The existing
   `Start arXiv Shelf.command` still invokes `python3`; `.python-version` alone
   does not make every shell select 3.12. Record its executable, Python version,
   and OpenSSL version. If Finder selects an older interpreter, update the Mac
   launcher to use the installed Python 3.12, using a path appropriate to that
   Mac, and verify launching from Finder.
2. Run the existing unit tests under Python 3.12:

   ```sh
   python3.12 -m unittest discover -s tests -v
   ```

3. Open the shelf with the Mac launcher. Verify the six PC editions now have
   titles/authors from the synced catalog (search by these IDs):
   `quant-ph/0501052v1`, `1512.03547v2`, `1809.00533v6`, `2308.15440v2`,
   `2412.16795v1`, and `2502.03337v1`. Availability should reflect the Mac's own
   PDFs; missing editions should still retain their metadata.
4. Open one existing local PDF in Acrobat and check browser preview. Do not
   download missing papers or change ratings just to perform this check.

Record the tested commit, interpreter details, unit-test outcome, and launcher,
catalog, and PDF-opening results here. No system Python replacement or other
project environment changes are requested. If a lookup fails again, capture one
bounded diagnostic report with the existing probe, rather than running loops.

## Follow-up: one missing-metadata entry after successful PC scan

The catalog still contained an unresolved placeholder for `0501052v1.pdf` as well
as the resolved `quant-ph/0501052v1` entry, *Introduction to PT-Symmetric Quantum
Theory*. The six local PDFs had metadata, but the earlier placeholder remained
as a seventh, unavailable entry for that PC import. This was a catalog identity
migration bug, not another API failure.

The fix records an append-only alias from the exact local file's unresolved key
to its resolved edition key. Catalog replay merges the records and ratings;
stale local caches also display the resolved metadata. Matching is not based on
filename alone, and historical event files are retained.

After the repair, the shared catalog has 234 entries and zero missing titles;
the PC still has six local PDFs with metadata. All 24 tests pass, including
cross-computer alias replay, preservation of later ratings, repeat scans, and
stale-cache display.

Mac check after pulling the fix: restart the shelf server (browser refresh alone
will not load Python code), then confirm the unnamed `0501052v1.pdf` placeholder
is gone and the resolved title remains. Both the code and the new catalog event
must be pulled; older application code does not interpret the alias event.
