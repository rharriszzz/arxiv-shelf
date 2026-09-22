import io
import subprocess
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request
from transfer import pdf_response


class TransferTests(unittest.TestCase):
    def request(self):
        return Request('https://arxiv.org/pdf/1410.7698', headers={'User-Agent': 'shelf-test'})

    @patch('transfer.subprocess.Popen')
    @patch('transfer.shutil.which', return_value='/usr/bin/curl')
    @patch('transfer.time.sleep')
    @patch('transfer.urlopen')
    def test_one_spaced_curl_retry_for_406_and_stream_error(self, opener, sleep, which, popen):
        opener.side_effect = HTTPError(self.request().full_url, 406, 'Not Acceptable', {}, io.BytesIO())
        process = Mock()
        process.stdout = io.BytesIO(b'%PDF-1.4 partial')
        process.wait.return_value = 18  # curl reports an incomplete transfer
        process.poll.return_value = 18
        popen.return_value = process
        with self.assertRaisesRegex(ValueError, 'curl exited with 18'):
            with pdf_response(self.request()) as response:
                self.assertEqual(response.read(65536), b'%PDF-1.4 partial')
                response.read(65536)
        sleep.assert_called_once_with(3.2)
        popen.assert_called_once()
        self.assertIn('--fail', popen.call_args.args[0])
        self.assertIn('--max-time', popen.call_args.args[0])
        self.assertTrue(process.stdout.closed)

    @patch('transfer.subprocess.Popen')
    @patch('transfer.urlopen')
    def test_no_retry_for_access_denied_or_rate_limit(self, opener, popen):
        for code in (403, 429, 500):
            opener.side_effect = HTTPError(self.request().full_url, code, 'Error', {}, io.BytesIO())
            with self.assertRaises(HTTPError):
                with pdf_response(self.request()):
                    self.fail('Unexpected response')
        popen.assert_not_called()

    @patch('transfer.subprocess.Popen')
    @patch('transfer.urlopen')
    def test_success_uses_python_only(self, opener, popen):
        opener.return_value = io.BytesIO(b'%PDF-1.4 complete')
        with pdf_response(self.request()) as response:
            self.assertEqual(response.read(65536), b'%PDF-1.4 complete')
        popen.assert_not_called()
