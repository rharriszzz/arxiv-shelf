"""Portable, append-only catalog. Sync its directory using a file-sync service or Git."""
import hashlib
import json
from pathlib import Path
import threading
import time
import uuid

FIELDS = ('arxiv_id', 'title', 'authors', 'abstract', 'published')


def paper_key(paper):
    identity = paper.get('arxiv_id') or 'unresolved:' + paper['key']
    return hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]


class Catalog:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.lock = threading.RLock()

    def read(self):
        """Re-read to pick up changes delivered by sync; never overwrite remote events."""
        with self.lock:
            papers, ratings = {}, {}
            events = []
            for path in self.directory.glob('*.json'):
                try:
                    event = json.loads(path.read_text(encoding='utf-8'))
                    if event.get('schema') != 1:
                        raise ValueError('unsupported schema')
                    events.append(event)
                except (OSError, ValueError) as exc:
                    raise ValueError(f'Cannot read catalog event {path.name}: {exc}') from exc
            for event in sorted(events, key=lambda e: (e['time'], e['id'])):
                for key, paper in event.get('papers', {}).items():
                    old = papers.get(key, {})
                    names = sorted(set(old.get('filenames', []) + paper.get('filenames', [])))
                    papers[key] = {**old, **paper, 'filenames': names}
                ratings.update(event.get('ratings', {}))
            for key, paper in papers.items():
                paper['catalog_key'] = key
                paper['rating'] = ratings.get(key, 0)
            return papers

    def _append(self, **changes):
        self.directory.mkdir(parents=True, exist_ok=True)
        identity = uuid.uuid4().hex
        event = {'schema': 1, 'time': time.time_ns(), 'id': identity, **changes}
        temp = self.directory / (identity + '.tmp')
        target = self.directory / (identity + '.json')
        try:
            temp.write_text(json.dumps(event, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)

    def remember(self, local_papers):
        with self.lock:
            existing = self.read()
            changes = {}
            for paper in local_papers:
                key = paper_key(paper)
                old = changes.get(key, existing.get(key, {}))
                record = {field: paper.get(field) for field in FIELDS}
                # An offline/missing-metadata scan must not erase known metadata.
                record = {field: value for field, value in record.items() if value}
                record['filenames'] = sorted(set(old.get('filenames', []) + [paper['filename']]))
                merged = {**{f: old[f] for f in (*FIELDS, 'filenames') if f in old}, **record}
                if merged != {f: old[f] for f in (*FIELDS, 'filenames') if f in old}:
                    changes[key] = merged
            if changes:
                self._append(papers=changes)

    def rate(self, key, value):
        if type(value) is not int or not 0 <= value <= 5:
            raise ValueError('Choose a rating from 1 to 5, or 0 to clear it.')
        with self.lock:
            if key not in self.read():
                raise ValueError('Paper is not in the catalog. Rescan and try again.')
            self._append(ratings={key: value})
