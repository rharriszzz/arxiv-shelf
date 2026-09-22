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
