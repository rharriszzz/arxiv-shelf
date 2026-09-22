import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import shelf

FEED = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/abs/2302.13971v2</id><title>A paper\n title</title>
<author><name>First Author</name></author><author><name>Second Author</name></author>
<published>2023-02-27T00:00:00Z</published><summary>Some abstract.</summary>
</entry></feed>'''

class FilenameTests(unittest.TestCase):
    def test_common_names(self):
        for name, expected in {'2302.13971.pdf':'2302.13971', '0802.0013v2.PDF':'0802.0013v2',
                               '1905.07786 (2).pdf':'1905.07786', 'arXiv_2302.13971v1.pdf':'2302.13971v1',
                               'hep-th_0401056.pdf':'hep-th/0401056', 'gr-qc-0410144v1.pdf':'gr-qc/0410144v1',
                               'math.GT_0306056.pdf':'math.GT/0306056', '0102032.pdf':'0102032'}.items():
            with self.subTest(name=name):
                self.assertEqual(shelf.filename_id(name), expected)

    def test_reject_unrelated(self):
        for name in ['invoice.pdf', 'preprints202004.0203.v1.pdf', '2020.12345.pdf',
                     '33732181864-ticket.pdf', '2302.13971.pdf.part', 'x2302.13971.pdf', '2302.139711.pdf']:
            self.assertIsNone(shelf.filename_id(name), name)

    def test_legacy_matching(self):
        text = 'arXiv:hep-th/0204104v3 plus arXiv:gr-qc/0410144v1'
        self.assertEqual(shelf.resolve_legacy('0410144', text), 'gr-qc/0410144')
        self.assertEqual(shelf.resolve_legacy('0204104v1', text), 'hep-th/0204104v1')
        self.assertIsNone(shelf.resolve_legacy('0102032', text))

    def test_atom(self):
        paper = shelf.parse_feed(FEED)['2302.13971v2']
        self.assertEqual(paper['title'], 'A paper title')
        self.assertEqual(paper['authors'], ['First Author', 'Second Author'])

class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.downloads = self.root / 'Downloads'
        self.downloads.mkdir()
        self.cache = self.root / 'index.json'

    def write_pdf(self, name):
        path = self.downloads / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'%PDF-1.4\nFixture')
        return path

    @patch('shelf.fetch_metadata', return_value=shelf.parse_feed(FEED))
    def test_duplicates_versions_cache_and_removed_files(self, fetch):
        original = self.write_pdf('2302.13971.pdf')
        self.write_pdf('2302.13971 (1).pdf')
        self.write_pdf('unrelated.pdf')
        self.write_pdf('nested/2302.13971.pdf')
        index = shelf.Shelf(self.downloads, self.cache)
        index.scan()
        self.assertEqual(len(index.papers), 2)
        self.assertTrue(all(p['title'] == 'A paper title' for p in index.papers))
        fetch.assert_called_once_with(['2302.13971'])
        original.unlink()
        cached = shelf.Shelf(self.downloads, self.cache, offline=True)
        cached.scan()
        self.assertEqual(len(cached.papers), 1)
        self.assertEqual(cached.papers[0]['status'], 'indexed')
        recursive = shelf.Shelf(self.downloads, self.cache, recursive=True, offline=True)
        recursive.scan()
        self.assertEqual(len(recursive.papers), 2)

    @patch('shelf.fetch_metadata', side_effect=OSError('network unavailable'))
    def test_failure_keeps_candidates_and_retries(self, fetch):
        self.write_pdf('2302.13971.pdf')
        index = shelf.Shelf(self.downloads, self.cache)
        index.scan()
        self.assertEqual(len(index.papers), 1)
        self.assertEqual(index.papers[0]['status'], 'unresolved')
        self.assertIn('network unavailable', index.error)
        self.assertTrue(self.cache.exists())
        index.scan()
        self.assertEqual(fetch.call_count, 2)

    @patch('shelf.time.sleep')
    @patch('shelf.first_page', return_value='A specific thesis title\n\nA dissertation')
    @patch('shelf.fetch_metadata', return_value={'hep-th/0401056v1': {'title':'A specific thesis title', 'authors':['R. Matos']}})
    def test_title_recovery_requires_matching_legacy_number(self, fetch, page, sleep):
        self.write_pdf('0401056.pdf')
        index = shelf.Shelf(self.downloads, self.cache)
        index.scan()
        self.assertEqual(index.papers[0]['arxiv_id'], 'hep-th/0401056')
        self.assertEqual(index.papers[0]['status'], 'indexed')
        fetch.assert_called_once_with([], title='A specific thesis title')
        self.write_pdf('0401057.pdf')
        index.scan()
        other = next(p for p in index.papers if p['filename'] == '0401057.pdf')
        self.assertIsNone(other['arxiv_id'])
        self.assertEqual(other['status'], 'unresolved')

    def test_symlink_outside_folder_is_excluded(self):
        outside = self.root / 'secret.pdf'
        outside.write_bytes(b'%PDF-1.4')
        (self.downloads / '2302.13971.pdf').symlink_to(outside)
        index = shelf.Shelf(self.downloads, self.cache, offline=True)
        index.scan()
        self.assertEqual(index.papers, [])

    @patch('shelf.open_pdf')
    def test_server_csrf_and_open_allowlist(self, opener):
        path = self.write_pdf('2302.13971.pdf')
        index = shelf.Shelf(self.downloads, self.cache, offline=True)
        index.scan()
        server = ThreadingHTTPServer(('127.0.0.1', 0), shelf.make_handler(index, 'secret', 'Adobe Acrobat'))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        key = index.papers[0]['key']
        with urlopen(base + '/api/papers') as response:
            self.assertEqual(len(json.load(response)['papers']), 1)
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(base + '/api/open/' + key, method='POST'))
        self.assertEqual(caught.exception.code, 403)
        with urlopen(Request(base + '/api/open/' + key, method='POST', headers={'X-Shelf-Token':'secret'})) as response:
            self.assertEqual(response.status, 200)
        opener.assert_called_once_with(path.resolve(), 'Adobe Acrobat')
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(base + '/api/open/not-indexed', method='POST', headers={'X-Shelf-Token':'secret'}))
        self.assertEqual(caught.exception.code, 400)
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(base + '/api/papers', headers={'Host':'evil.example'}))
        self.assertEqual(caught.exception.code, 403)

if __name__ == '__main__':
    unittest.main()
