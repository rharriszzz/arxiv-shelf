import base64
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import desktop


class DesktopTests(unittest.TestCase):
    @patch('desktop.is_wsl', return_value=True)
    @patch('desktop.powershell', return_value='D:\\Papers é\\Downloads')
    @patch('desktop.subprocess.check_output', return_value='/mnt/d/Papers é/Downloads\n')
    def test_redirected_windows_downloads(self, convert, ps, wsl):
        self.assertEqual(desktop.default_directory(), Path('/mnt/d/Papers é/Downloads'))
        convert.assert_called_once_with(['wslpath', '-u', 'D:\\Papers é\\Downloads'], text=True)

    @patch('desktop.is_wsl', return_value=True)
    @patch('desktop.powershell', side_effect=OSError('interop unavailable'))
    def test_detection_failure_is_actionable(self, ps, wsl):
        with self.assertRaisesRegex(ValueError, '--directory'):
            desktop.default_directory()

    @patch('desktop.is_wsl', return_value=True)
    @patch('desktop.subprocess.check_output', return_value="C:\\Downloads\\O'Brien é.pdf\n")
    @patch('desktop.subprocess.run')
    def test_pdf_path_is_data_in_encoded_windows_command(self, run, convert, wsl):
        run.return_value = subprocess.CompletedProcess([], 0, b'', b'')
        desktop.open_pdf(Path("/mnt/c/Downloads/O'Brien é.pdf"), 'Adobe Acrobat')
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand'])
        script = base64.b64decode(command[4]).decode('utf-16le')
        self.assertIn("'C:\\Downloads\\O''Brien é.pdf'", script)
        self.assertIn('Acrobat.exe', script)
        self.assertIn('Start-Process -FilePath $target', script)

    @patch('desktop.subprocess.run')
    def test_windows_failure_is_reported(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, b'', b'No PDF association')
        with self.assertRaisesRegex(ValueError, 'No PDF association'):
            desktop.open_windows('C:\\Downloads\\paper.pdf')
