#!/usr/bin/env python3
"""Read-only, rate-spaced comparison using the shelf's actual API request code."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import ssl
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import getproxies
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shelf

CASES = [
    ('single', ['1512.03547v2']),
    ('two-paper batch', ['1512.03547v2', '1809.00533v6']),
    ('six-paper batch', ['quant-ph/0501052v1', '1512.03547v2',
                         '1809.00533v6', '2308.15440v2',
                         '2412.16795v1', '2502.03337v1']),
]
HEADERS = ('Content-Type', 'Cache-Control', 'Via', 'Date', 'X-Served-By',
           'X-Cache', 'Retry-After')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('baseline', 'order'), default='baseline',
                        help='Order suite requests the same batches reversed, then repeats the known baseline pair')
    parser.add_argument('--output', type=Path, required=True, help='New JSON report path; existing files are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Report already exists; choose a new output path.')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=shelf.ROOT,
                            capture_output=True, text=True)
    report = {'utc': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'python': platform.python_version(),
              'openssl': ssl.OPENSSL_VERSION, 'commit': commit.stdout.strip(),
              # Record presence only: proxy URLs can contain credentials.
              'proxy_configured': {k: bool(v) for k, v in getproxies().items() if k != 'no'},
              'cases': []}
    report['suite'] = args.suite
    cases = CASES if args.suite == 'baseline' else [
        ('reversed two-paper batch', list(reversed(CASES[1][1]))),
        ('reversed six-paper batch', list(reversed(CASES[2][1]))),
        ('original two-paper control', CASES[1][1]),
    ]
    original_urlopen = shelf.urlopen
    for i, (label, ids) in enumerate(cases):
        if i:
            time.sleep(3.2)
        result = {'label': label, 'ids': ids, 'utc': datetime.now(timezone.utc).isoformat()}

        def observed_urlopen(request, **kwargs):
            result['url'] = request.full_url
            try:
                response = original_urlopen(request, **kwargs)
            except HTTPError as exc:
                result['headers'] = {h: exc.headers.get(h) for h in HEADERS}
                raise
            result['http_status'] = response.status
            result['headers'] = {h: response.headers.get(h) for h in HEADERS}
            return response

        started = time.monotonic()
        try:
            with patch.object(shelf, 'urlopen', observed_urlopen):
                records = shelf.fetch_metadata(ids)
            result.update(outcome='success', returned_ids=sorted(records),
                          missing_ids=sorted(set(ids) - set(records)))
        except HTTPError as exc:
            # Omit response bodies; a network gateway could include personal data.
            result.update(outcome='http_error', http_status=exc.code,
                          body_empty=not bool(exc.read(1)))
        except Exception as exc:
            result.update(outcome='transport_error', error_type=type(exc).__name__)
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        report['cases'].append(result)
        print(label + ': ' + json.dumps(result), flush=True)
        # Stop after an explicit access denial or rate-limit response.
        if result.get('http_status') in (403, 429):
            report['stopped_early'] = 'Access denied or rate limited; no further probes.'
            break
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print('Report:', args.output)


if __name__ == '__main__':
    main()
