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
