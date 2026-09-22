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

Pending. Please append the results and conclusion after running the test.
