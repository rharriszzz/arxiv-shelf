import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from catalog import Catalog, paper_key
from shelf import Shelf
from sync import git_sync


def paper(identifier, title='A paper'):
    return {'key': identifier, 'arxiv_id': identifier, 'title': title, 'authors': ['An Author'],
            'filename': identifier.replace('/', '_') + '.pdf', 'path': '/private/local/path.pdf',
            'abstract': 'An abstract', 'published': '2020-01-01'}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_two_computers_merge_and_rating_clear(self):
        mac, pc = Catalog(self.root / 'mac'), Catalog(self.root / 'pc')
        a, b = paper('2302.13971'), paper('1706.03762')
        mac.remember([a]); pc.remember([b])
        mac.rate(paper_key(a), 4); pc.rate(paper_key(b), 5)
        for source, target in [(mac, pc), (pc, mac)]:
            for event in source.directory.glob('*.json'):
                shutil.copy2(event, target.directory / event.name)
        self.assertEqual(mac.read(), pc.read())
        self.assertEqual(len(pc.read()), 2)
        self.assertEqual(pc.read()[paper_key(a)]['rating'], 4)
        pc.rate(paper_key(a), 0)
        for event in pc.directory.glob('*.json'):
            shutil.copy2(event, mac.directory / event.name)
        self.assertEqual(mac.read()[paper_key(a)]['rating'], 0)
        self.assertNotIn('/private/local', ''.join(p.read_text() for p in mac.directory.glob('*.json')))
        count = len(list(mac.directory.glob('*.json')))
        mac.remember([a])
        self.assertEqual(count, len(list(mac.directory.glob('*.json'))))

    def test_missing_files_survive_rescan_restart_and_other_computer(self):
        downloads = self.root / 'Downloads'; downloads.mkdir()
        path = downloads / '2302.13971.pdf'; path.write_bytes(b'%PDF-1.4 fixture')
        catalog = self.root / 'catalog'
        mac = Shelf(downloads, self.root / 'mac.json', offline=True, catalog=catalog)
        mac.scan()
        key = mac.library()[0]['catalog_key']
        mac.rate(key, 3)
        path.unlink(); mac.scan()
        self.assertEqual(len(mac.library()), 1)
        self.assertFalse(mac.library()[0]['available'])
        pc_downloads = self.root / 'PCDownloads'; pc_downloads.mkdir()
        pc = Shelf(pc_downloads, self.root / 'pc.json', offline=True, catalog=catalog)
        pc.scan()
        self.assertEqual(pc.library()[0]['rating'], 3)
        self.assertFalse(pc.library()[0]['available'])
        (pc_downloads / path.name).write_bytes(b'%PDF-1.4 fixture')
        pc.scan()
        self.assertTrue(pc.library()[0]['available'])
        self.assertEqual(len(pc.library()), 1)

    def test_legacy_cache_migration(self):
        downloads = self.root / 'Downloads'; downloads.mkdir()
        cache = self.root / 'index.json'
        old = paper('2302.13971')
        cache.write_text(json.dumps({'directory':str(downloads), 'recursive':False, 'papers':[old]}))
        index = Shelf(downloads, cache, offline=True)
        self.assertEqual(index.library()[0]['title'], 'A paper')
        self.assertFalse(index.library()[0]['available'])

    def test_rating_validation(self):
        catalog = Catalog(self.root)
        catalog.remember([paper('2302.13971')])
        for value in [-1, 6, True, '5', None]:
            with self.assertRaises(ValueError):
                catalog.rate(paper_key(paper('2302.13971')), value)

    def test_corrupt_event_is_not_silently_discarded(self):
        (self.root / 'broken.json').write_text('{')
        with self.assertRaises(ValueError):
            Catalog(self.root).remember([paper('2302.13971')])


class DownloadTests(unittest.TestCase):
    setUp = CatalogTests.setUp
    def make_index(self):
        downloads = self.root / 'Downloads'; downloads.mkdir()
        index = Shelf(downloads, self.root / 'cache.json')
        index.catalog.remember([paper('hep-th/0401056v1')])
        return index, paper_key(paper('hep-th/0401056v1'))

    @patch('shelf.urlopen')
    def test_pdf_download_no_overwrite(self, fetch):
        index, key = self.make_index()
        existing = index.directory / 'hep-th_0401056v1.pdf'
        existing.write_bytes(b'Existing file stays untouched')
        response = io.BytesIO(b'%PDF-1.4 downloaded fixture')
        response.headers = {'Content-Length':str(len(response.getvalue()))}
        fetch.return_value = response
        with patch.object(index, 'start_scan') as scan:
            index.download(key)
            scan.assert_called_once()
        self.assertEqual(existing.read_bytes(), b'Existing file stays untouched')
        self.assertTrue((index.directory / 'hep-th_0401056v1 (1).pdf').exists())
        self.assertFalse(list(index.directory.glob('*.part')))
        self.assertEqual(fetch.call_args.args[0].full_url, 'https://arxiv.org/pdf/hep-th/0401056v1')

    @patch('shelf.urlopen')
    def test_non_pdf_and_incomplete_downloads_leave_no_pdf(self, fetch):
        index, key = self.make_index()
        for content, size in [(b'<html>Error</html>', 18), (b'%PDF-1.4 cut off', 999)]:
            response = io.BytesIO(content); response.headers = {'Content-Length':str(size)}
            fetch.return_value = response
            with self.assertRaises(ValueError):
                index.download(key)
            self.assertEqual(list(index.directory.iterdir()), [])

    def test_unresolved_and_offline_download_errors(self):
        index, key = self.make_index()
        with self.assertRaises(ValueError):
            index.download('not-a-key')
        index.offline = True
        with self.assertRaises(ValueError):
            index.download(key)


class GitSyncTests(unittest.TestCase):
    def test_two_repositories_exchange_catalog_and_refuse_unrelated_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*args, cwd=root):
                result = subprocess.run(['git', *map(str,args)], cwd=cwd, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout
            git('init', '--bare', '--initial-branch=master', root / 'remote.git')
            git('clone', root / 'remote.git', root / 'mac')
            mac = root / 'mac'
            git('config', 'user.name', 'Shelf Test', cwd=mac)
            git('config', 'user.email', 'shelf@example.invalid', cwd=mac)
            (mac / 'README.md').write_text('Fixture repository')
            git('add', 'README.md', cwd=mac); git('commit', '-m', 'Initial', cwd=mac)
            git('push', '-u', 'origin', 'master', cwd=mac)
            git('clone', root / 'remote.git', root / 'pc')
            pc = root / 'pc'
            git('config', 'user.name', 'Shelf Test', cwd=pc)
            git('config', 'user.email', 'shelf@example.invalid', cwd=pc)
            a, b = Catalog(mac / 'catalog'), Catalog(pc / 'catalog')
            a.remember([paper('2302.13971')]); b.remember([paper('1706.03762')])
            a.rate(paper_key(paper('2302.13971')), 4)
            git_sync(mac, mac / 'catalog')
            git_sync(pc, pc / 'catalog')
            git_sync(mac, mac / 'catalog')
            self.assertEqual(a.read(), b.read())
            self.assertEqual(len(a.read()), 2)
            (mac / 'README.md').write_text('Uncommitted edits')
            with self.assertRaisesRegex(ValueError, 'uncommitted app changes'):
                git_sync(mac, mac / 'catalog')
            self.assertEqual((mac / 'README.md').read_text(), 'Uncommitted edits')
