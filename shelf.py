#!/usr/bin/env python3
"""A local, dependency-free arXiv PDF shelf (Python 3.10+)."""
import argparse
import hashlib
import json
import os
import tempfile
from catalog import Catalog, paper_key
from sync import git_sync
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
MODERN = r'\d{4}\.\d{4,5}'
LEGACY = r'[a-z][a-z.-]*(?:\.[A-Z]{2})?/\d{7}'
ID_RE = re.compile(rf'arXiv\s*:\s*({MODERN}|{LEGACY})(v\d+)?', re.I)
ATOM = '{http://www.w3.org/2005/Atom}'


def filename_id(name):
    """Return an ID (or ambiguous old number), accepting common download suffixes."""
    if not name.lower().endswith('.pdf'):
        return None
    stem = re.sub(r'\s*\(\d+\)$', '', name[:-4])
    stem = re.sub(r'^arxiv[ _:-]*', '', stem, flags=re.I)
    match = re.fullmatch(rf'({MODERN}|\d{{7}}|[a-z][a-z.-]*[_-]\d{{7}})(v\d+)?', stem, re.I)
    if not match:
        return None
    base, version = match.group(1), match.group(2) or ''
    base = re.sub(r'[_-](\d{7})$', r'/\1', base)
    number = base.rsplit('/', 1)[-1]
    month = int(number[2:4])
    if not 1 <= month <= 12:
        return None
    return base + version.lower()


def first_page(path):
    if not shutil.which('pdftotext'):
        return ''
    try:
        result = subprocess.run(['pdftotext', '-f', '1', '-l', '1', str(path), '-'],
                                capture_output=True, timeout=20)
        return result.stdout.decode('utf-8', errors='replace')
    except (OSError, subprocess.TimeoutExpired):
        return ''


def resolve_legacy(identifier, text):
    number = re.sub(r'v\d+$', '', identifier).rsplit('/', 1)[-1]
    for match in ID_RE.finditer(text):
        if match.group(1).rsplit('/', 1)[-1] == number:
            version = re.search(r'v\d+$', identifier)
            return match.group(1) + (version.group() if version else '')
    return None


def parse_feed(data):
    results = {}
    for entry in ET.fromstring(data).findall(ATOM + 'entry'):
        identifier = entry.findtext(ATOM + 'id', '').split('/abs/')[-1]
        if not re.fullmatch(rf'(?:{MODERN}|{LEGACY})(?:v\d+)?', identifier, re.I):
            continue
        results[identifier] = {
            'title': ' '.join(entry.findtext(ATOM + 'title', '').split()),
            'authors': [' '.join(a.findtext(ATOM + 'name', '').split())
                        for a in entry.findall(ATOM + 'author')],
            'abstract': ' '.join(entry.findtext(ATOM + 'summary', '').split()),
            'published': entry.findtext(ATOM + 'published', '')[:10],
        }
    return results


def fetch_metadata(ids, title=None):
    params = {'search_query': 'ti:"' + title.replace('"', '') + '"', 'max_results': 5} if title else {'id_list': ','.join(ids), 'max_results': len(ids)}
    url = 'https://export.arxiv.org/api/query?' + urlencode(params)
    request = Request(url, headers={'User-Agent': 'arxiv-shelf/1.0 (local personal PDF index)'})
    with urlopen(request, timeout=35) as response:
        return parse_feed(response.read())


class Shelf:
    def __init__(self, directory, cache, recursive=False, offline=False, catalog=None):
        self.directory = directory.resolve()
        self.cache = cache
        self.recursive = recursive
        self.offline = offline
        self.lock = threading.RLock()
        self.catalog = Catalog(catalog or cache.parent / "catalog")
        self.download_lock = threading.Lock()
        self.scanning = False
        self.syncing = False
        self.message = 'Ready to scan'
        self.error = ''
        self.papers = []
        self.metadata = {}
        self.last_scan = ''
        try:
            saved = json.loads(cache.read_text(encoding='utf-8'))
            self.metadata = saved.get('metadata', {})
            if saved.get('directory') == str(self.directory) and saved.get('recursive') == recursive:
                self.papers = saved.get('papers', [])
                self.last_scan = saved.get('last_scan', '')
        except (OSError, ValueError):
            pass
        self.catalog.remember(self.papers)
        for record in self.catalog.read().values():
            if record.get('arxiv_id') and record.get('title'):
                self.metadata.setdefault(record['arxiv_id'], {f: record.get(f, [] if f == 'authors' else '') for f in ('title', 'authors', 'abstract', 'published')})

    def library(self):
        records = self.catalog.read()
        result, available = [], set()
        for local in self.papers:
            try:
                self.find_path(local['key'])
            except ValueError:
                continue
            key = paper_key(local)
            record = records.get(key, {})
            paper = {**local, **{f: record[f] for f in ('title', 'authors', 'abstract', 'published') if record.get(f)},
                     'catalog_key': key, 'rating': record.get('rating', 0), 'available': True}
            result.append(paper)
            available.add(key)
        for key, record in records.items():
            if key in available:
                continue
            result.append({'key': key, 'filename': ', '.join(record.get('filenames', [])),
                           'path': '', 'size': 0, 'mtime': 0, 'valid_pdf': True,
                           'status': 'indexed' if record.get('title') else 'unresolved',
                           'note': '', 'excerpt': '', 'title': '', 'authors': [],
                           'abstract': '', 'published': '', 'arxiv_id': None,
                           **record, 'available': False})
        return result

    def snapshot(self):
        with self.lock:
            return {'papers': self.library(), 'directory': str(self.directory), 'catalog': str(self.catalog.directory),
                    'scanning': self.scanning, 'syncing': self.syncing, 'message': self.message,
                    'error': self.error, 'last_scan': self.last_scan}

    def start_scan(self):
        with self.lock:
            if self.scanning or self.syncing or self.download_lock.locked():
                return False
            self.scanning = True
            self.error = ''
        threading.Thread(target=self.scan, daemon=True).start()
        return True

    def start_sync(self):
        with self.lock:
            if self.scanning or self.syncing or self.download_lock.locked():
                raise ValueError('Wait for the current scan, download, or sync to finish.')
            if self.offline:
                raise ValueError('GitHub sync is disabled in offline mode.')
            self.syncing = True
            self.error = ''
            self.message = 'Syncing catalog and ratings with GitHub'
        def run():
            try:
                self.message = git_sync(ROOT, self.catalog.directory)
            except Exception as exc:
                self.error = 'GitHub sync failed: ' + str(exc)
                self.message = 'Sync incomplete; your local catalog is saved'
            finally:
                self.syncing = False
        threading.Thread(target=run, daemon=True).start()

    def rate(self, key, value):
        with self.lock:
            if self.syncing:
                raise ValueError('Wait for GitHub sync to finish before changing ratings.')
            self.catalog.rate(key, value)

    def save(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        temp = self.cache.with_suffix('.tmp')
        temp.write_text(json.dumps({'directory': str(self.directory), 'recursive': self.recursive,
                                    'papers': self.papers, 'metadata': self.metadata,
                                    'last_scan': self.last_scan}, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.cache)

    def scan(self):
        try:
            if not self.directory.is_dir():
                raise ValueError(f'Directory does not exist: {self.directory}')
            for record in self.catalog.read().values():
                if record.get('arxiv_id') and record.get('title'):
                    self.metadata.setdefault(record['arxiv_id'], {f: record.get(f, [] if f == 'authors' else '') for f in ('title', 'authors', 'abstract', 'published')})
            paths = self.directory.rglob('*') if self.recursive else self.directory.iterdir()
            candidates = sorted(p for p in paths if p.is_file() and filename_id(p.name))
            papers = []
            old = {p['path']: p for p in self.papers}
            for i, path in enumerate(candidates):
                self.message = f'Inspecting PDF {i + 1} of {len(candidates)}'
                # Never follow a symlink to a file outside the selected directory.
                resolved = path.resolve()
                if not resolved.is_relative_to(self.directory):
                    continue
                try:
                    stat = path.stat()
                    with path.open('rb') as handle:
                        valid = b'%PDF-' in handle.read(1024)
                except OSError:
                    continue
                identifier = filename_id(path.name)
                text = ''
                previous = old.get(str(resolved), {})
                if re.fullmatch(r'\d{7}(v\d+)?', identifier) or '/' in identifier:
                    if previous.get('mtime') == stat.st_mtime and previous.get('status') == 'indexed':
                        identifier = previous['arxiv_id']
                    else:
                        text = first_page(path) if valid else ''
                        identifier = resolve_legacy(identifier, text) or (identifier if '/' in identifier and len(identifier.split('/')[0]) < 20 else None)
                paper = {'key': hashlib.sha256(str(resolved).encode()).hexdigest()[:24],
                         'filename': path.name, 'path': str(resolved), 'arxiv_id': identifier,
                         'mtime': stat.st_mtime, 'size': stat.st_size, 'valid_pdf': valid,
                         'title': '', 'authors': [], 'abstract': '', 'published': '',
                         'status': 'pending' if identifier else 'unresolved',
                         'note': '' if identifier else 'Could not recover the legacy subject prefix from the PDF. Verify the full ID and rename the file to include it.',
                         'excerpt': text[:4000]}
                if not valid:
                    paper['note'] = 'This file does not have a PDF header; it may be an incomplete or failed download.'
                papers.append(paper)
            # For unstamped older PDFs, search the opening title block, then require
            # the returned legacy number to match the filename before accepting it.
            if not self.offline:
                for paper in papers:
                    if paper['arxiv_id'] or not paper['excerpt']:
                        continue
                    title = ' '.join(paper['excerpt'].strip().split('\n\n')[0].split())
                    if not 10 <= len(title) <= 300:
                        continue
                    self.message = f'Recovering legacy ID for {paper["filename"]}'
                    try:
                        found = fetch_metadata([], title=title)
                        number = re.search(r'\d{7}', paper['filename']).group()
                        for key, meta in found.items():
                            if re.sub(r'v\d+$', '', key).rsplit('/', 1)[-1] == number:
                                version = re.search(r'v\d+', paper['filename'])
                                identifier = re.sub(r'v\d+$', '', key) + (version.group() if version else '')
                                paper['arxiv_id'] = identifier
                                paper['note'] = ''
                                if not version or key == identifier:
                                    self.metadata[identifier] = meta
                                break
                    except Exception:
                        pass  # The normal lookup below reports network failures.
                    time.sleep(3.1)
            ids = list(dict.fromkeys(p['arxiv_id'] for p in papers if p['arxiv_id'] and p['arxiv_id'] not in self.metadata))
            errors = []
            for offset in range(0, len(ids), 25):
                if self.offline:
                    break
                batch = ids[offset:offset + 25]
                self.message = f'Fetching arXiv metadata: {offset + 1}–{min(offset + 25, len(ids))} of {len(ids)}'
                if offset:
                    time.sleep(3.1)
                try:
                    found = fetch_metadata(batch)
                    for identifier in batch:
                        meta = found.get(identifier)
                        if not meta and not re.search(r'v\d+$', identifier):
                            meta = next((m for key, m in found.items() if re.sub(r'v\d+$', '', key) == identifier), None)
                        if meta:
                            self.metadata[identifier] = meta
                except Exception as exc:
                    errors.append(f'arXiv lookup failed: {exc}')
                    # Keep cached results and avoid hammering a failing service.
                    break
            for p in papers:
                if p['arxiv_id'] in self.metadata:
                    p.update(self.metadata[p['arxiv_id']])
                    p['status'] = 'indexed'
                elif p['arxiv_id']:
                    p['status'] = 'unresolved'
                    p['note'] = p['note'] or 'Metadata unavailable. Rescan with internet access to retry.'
            with self.lock:
                self.catalog.remember(self.papers + papers)
                self.papers = papers
                self.last_scan = time.strftime('%Y-%m-%d %H:%M:%S')
                self.error = '; '.join(errors)
                self.message = f'{len(papers)} local files · {sum(p["status"] == "indexed" for p in papers)} with metadata'
            self.save()
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.scanning = False

    def download(self, key):
        with self.lock:
            if self.syncing or self.scanning:
                raise ValueError('Wait for the current scan or GitHub sync to finish before downloading.')
            if self.offline:
                raise ValueError('Downloads are disabled in offline mode. Restart without --offline.')
            if not self.download_lock.acquire(blocking=False):
                raise ValueError('Another download is running. Please wait for it to finish.')
        temporary = None
        try:
            record = self.catalog.read().get(key)
            identifier = record.get('arxiv_id', '') if record else ''
            if not identifier or not re.fullmatch(rf'(?:{MODERN}|{LEGACY})(?:v\d+)?', identifier, re.I):
                raise ValueError('This paper needs a complete arXiv ID before it can be downloaded.')
            with self.lock:
                for paper in self.library():
                    if paper['catalog_key'] == key and paper['available'] and paper['valid_pdf']:
                        return
            self.directory.mkdir(parents=True, exist_ok=True)
            request = Request('https://arxiv.org/pdf/' + identifier,
                              headers={'User-Agent': 'arxiv-shelf/1.1 (personal PDF library)'})
            with urlopen(request, timeout=90) as response:
                with tempfile.NamedTemporaryFile(dir=self.directory, prefix='.arxiv-', suffix='.part', delete=False) as out:
                    temporary = Path(out.name)
                    total, first = 0, True
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        if first and not chunk.lstrip().startswith(b'%PDF-'):
                            raise ValueError('arXiv returned something other than a PDF. Please try again later.')
                        first = False
                        total += len(chunk)
                        if total > 200 * 1024 * 1024:
                            raise ValueError('Download exceeds the 200 MB limit.')
                        out.write(chunk)
                    length = response.headers.get('Content-Length')
                    if first or (length and total != int(length)):
                        raise ValueError('The download was incomplete. Please try again.')
            # Exclusive creation avoids overwriting existing files, including symlinks.
            stem = identifier.replace('/', '_')
            for n in range(10000):
                destination = self.directory / (stem + (f' ({n})' if n else '') + '.pdf')
                try:
                    with destination.open('xb') as out:
                        try:
                            with temporary.open('rb') as source:
                                shutil.copyfileobj(source, out)
                        except BaseException:
                            out.close()
                            destination.unlink(missing_ok=True)
                            raise
                    break
                except FileExistsError:
                    continue
            else:
                raise ValueError('No unused filename is available for this download.')
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
            self.download_lock.release()
        self.start_scan()

    def find_path(self, key):
        with self.lock:
            paper = next((p for p in self.papers if p['key'] == key), None)
        if not paper:
            raise ValueError('Paper is not in the index.')
        path = Path(paper['path']).resolve()
        if not path.is_relative_to(self.directory) or not path.is_file() or path.suffix.lower() != '.pdf':
            raise ValueError('The PDF was moved or is no longer available. Rescan the folder.')
        return path


def open_pdf(path, app):
    if sys.platform == 'darwin':
        result = subprocess.run(['open', '-a', app, str(path)], capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise ValueError(f'Could not open {app}. Check the installed app name and use --acrobat-app. {result.stderr.strip()}')
    else:
        raise ValueError('Acrobat launching currently supports macOS. Use the PDF preview link on other systems.')


def make_handler(shelf, token, app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status, data, content_type='application/json'):
            if not isinstance(data, bytes):
                data = json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def local_request(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if not self.local_request():
                return self.send(403, {'error': 'Local access only'})
            path = urlparse(self.path).path
            if path == '/api/papers':
                return self.send(200, {**shelf.snapshot(), 'token': token})
            if path.startswith('/pdf/'):
                try:
                    return self.send(200, shelf.find_path(unquote(path[5:])).read_bytes(), 'application/pdf')
                except (OSError, ValueError) as exc:
                    return self.send(404, {'error': str(exc)})
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if path in assets:
                file, mime = assets[path]
                return self.send(200, (ROOT / 'web' / file).read_bytes(), mime)
            self.send(404, {'error': 'Not found'})

        def do_POST(self):
            if not self.local_request() or self.headers.get('X-Shelf-Token') != token:
                return self.send(403, {'error': 'Please reload the shelf and try again.'})
            path = urlparse(self.path).path
            if path == '/api/sync':
                try:
                    shelf.start_sync()
                    return self.send(202, {'ok': True})
                except ValueError as exc:
                    return self.send(400, {'error': str(exc)})
            if path == '/api/scan':
                shelf.start_scan()
                return self.send(202, {'ok': True})
            if path.startswith('/api/rate/'):
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 100:
                        raise ValueError('Invalid rating request.')
                    value = json.loads(self.rfile.read(size))['rating']
                    shelf.rate(path[len('/api/rate/'):], value)
                    return self.send(200, {'ok': True})
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    return self.send(400, {'error': str(exc)})
            if path.startswith('/api/download/'):
                try:
                    shelf.download(path[len('/api/download/'):])
                    return self.send(200, {'ok': True})
                except Exception as exc:
                    return self.send(400, {'error': str(exc)})
            if path.startswith('/api/open/'):
                try:
                    open_pdf(shelf.find_path(path[len('/api/open/'):]), app)
                    return self.send(200, {'ok': True})
                except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                    return self.send(400, {'error': str(exc)})
            self.send(404, {'error': 'Not found'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.home() / 'Downloads')
    parser.add_argument('--cache', type=Path, default=ROOT / '.shelf' / 'index.json')
    parser.add_argument('--catalog', type=Path, default=ROOT / 'catalog', help='Portable catalog folder (default: catalog/ in this Git repository)')
    parser.add_argument('--recursive', action='store_true', help='Include subfolders')
    parser.add_argument('--offline', action='store_true', help='Use cached metadata without contacting arXiv')
    parser.add_argument('--scan-only', action='store_true', help='Update the index and exit')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--acrobat-app', default='Adobe Acrobat')
    args = parser.parse_args()
    shelf = Shelf(args.directory.expanduser(), args.cache.expanduser(), args.recursive, args.offline, args.catalog)
    if args.scan_only:
        shelf.scan()
        print(shelf.message)
        if shelf.error:
            print(shelf.error, file=sys.stderr)
            return 1
        return 0
    # Acrobat DC is the application folder name on some installations.
    app = args.acrobat_app
    if app == 'Adobe Acrobat' and Path('/Applications/Adobe Acrobat DC/Adobe Acrobat.app').exists():
        app = '/Applications/Adobe Acrobat DC/Adobe Acrobat.app'
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(shelf, secrets.token_urlsafe(32), app))
    shelf.start_scan()
    print(f'arXiv Shelf: http://127.0.0.1:{server.server_port}', flush=True)
    print('Press Ctrl-C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
