"""Keep current runtime instructions and launchers on the supported Python."""
import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import shelf
import desktop

ROOT = Path(__file__).resolve().parents[1]


class RuntimePolicyTests(unittest.TestCase):
    def test_pin_and_ci_use_supported_python(self):
        self.assertEqual((ROOT / '.python-version').read_text().strip(), '3.14')
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        self.assertIn("python-version: '3.14'", workflow)
        self.assertIn('actions/setup-python@v7', workflow)
        self.assertIn('python -m unittest discover -s tests -v', workflow)

    def test_current_files_do_not_recommend_older_versions(self):
        # Explicit historical boundaries: never rewrite measured old results.
        historical = {'MAC_API_TEST.md', 'docs/PYTHON_MODERNIZATION_2026-11.md'}
        excluded_dirs = {'.git', '.venv', '.shelf', 'catalog',
                         'tests', '__pycache__', 'node_modules'}
        extensions = {'.py', '.md', '.sh', '.bat', '.command', '.toml', '.ini',
                      '.cfg', '.yml', '.yaml', '.txt', '.html', '.json'}
        obsolete = re.compile(
            r'(?<![\d.])3\.1[0-3](?:\.\d+)?(?!\d)'
            r'|(?i:\bpython(?:-version)?[\s:=\'\"]*)3\.[0-9](?!\d)'
            r'|\b3,\s*1[0-3]\b')
        for directory, subdirs, files in os.walk(ROOT):
            subdirs[:] = [d for d in subdirs if d not in excluded_dirs]
            for filename in files:
                path = Path(directory) / filename
                relative = path.relative_to(ROOT).as_posix()
                if (relative in historical or relative == 'dist/catalog.json' or
                        (relative.startswith('diagnostics/') and path.suffix == '.json')):
                    continue
                if path.suffix not in extensions and filename not in {
                        '.python-version', '.tool-versions', 'Dockerfile', 'Pipfile'}:
                    continue
                with self.subTest(file=relative):
                    self.assertIsNone(obsolete.search(path.read_text(encoding='utf-8')),
                                      f'Obsolete runtime in {relative}')
        readme = (ROOT / 'README.md').read_text()
        self.assertIsNone(re.search(r'(?:^|\n|`)\s*(?:python3?|py)\s+(?!-3\.14\b)', readme),
                          'README commands must use a verified environment or explicit version')

    @patch('shelf.default_directory')
    @patch('shelf.sys.version_info', (3, 0, 0))
    def test_direct_launch_rejects_unsupported_runtime_before_touching_data(self, directory):
        with patch('sys.stderr') as error:
            self.assertEqual(shelf.main(), 1)
        directory.assert_not_called()
        self.assertIn('Python 3.14', ''.join(c.args[0] for c in error.write.call_args_list))


@unittest.skipIf(sys.platform == 'win32', 'POSIX launcher; Windows batch tested separately')
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='shelf launcher ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('Start arXiv Shelf.sh', 'Start arXiv Shelf.command'):
            shutil.copy2(ROOT / name, self.root / name)
        (self.root / 'shelf.py').write_text(
            'import json, sys; print(json.dumps([list(sys.version_info[:2]), sys.argv[1:]]))')
        self.environment = {**os.environ, 'HOME': str(self.root), 'PATH': '/usr/bin:/bin'}

    def run_launcher(self, name='Start arXiv Shelf.sh', *args, shell='/bin/bash'):
        return subprocess.run([shell, str(self.root / name), *args], cwd='/',
                              env=self.environment, capture_output=True, text=True, timeout=15)

    def test_project_environment_selected_without_profile_and_arguments_preserved(self):
        import json
        environment = self.root / '.venv/bin'
        environment.mkdir(parents=True)
        (environment / 'python').symlink_to(sys.executable)
        result = self.run_launcher('Start arXiv Shelf.sh', '--directory', 'Papers with spaces', '--port', '9876')
        self.assertEqual(result.returncode, 0, result.stderr)
        version, arguments = json.loads(result.stdout)
        self.assertEqual(version, [3, 14])
        self.assertEqual(arguments, ['--open-browser', '--directory', 'Papers with spaces', '--port', '9876'])
        if shutil.which('zsh'):
            result = self.run_launcher('Start arXiv Shelf.command', '--port', '9877', shell=shutil.which('zsh'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('9877', result.stdout)

    def test_wrong_environment_is_skipped_for_user_managed_python(self):
        environment = self.root / '.venv/bin'
        environment.mkdir(parents=True)
        wrong = environment / 'python'
        wrong.write_text('#!/bin/sh\nexit 1\n')
        wrong.chmod(0o755)
        local = self.root / '.local/bin'
        local.mkdir(parents=True)
        (local / 'python3.14').symlink_to(sys.executable)
        # Hide installed candidates to exercise the user-managed location.
        commands = self.root / 'commands'
        commands.mkdir()
        (commands / 'dirname').symlink_to(shutil.which('dirname'))
        self.environment['PATH'] = str(commands)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[3, 14]', result.stdout)

    def test_no_supported_interpreter_reports_installation_help(self):
        # Put a rejecting candidate at every location; independent of the host.
        script = self.root / 'Start arXiv Shelf.sh'
        source = script.read_text()
        source = source.replace('/opt/homebrew/bin/python3.14', '/nonexistent/shelf-python')
        source = source.replace('/usr/local/bin/python3.14', '/nonexistent/shelf-python')
        source = source.replace('/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14',
                                '/nonexistent/shelf-python')
        script.write_text(source)
        # dirname is the only external utility needed before interpreter selection.
        commands = self.root / 'commands'
        commands.mkdir()
        (commands / 'dirname').symlink_to(shutil.which('dirname'))
        self.environment['PATH'] = str(commands)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 1)
        self.assertIn('Python 3.14 is required', result.stderr)
        self.assertIn('README.md', result.stderr)


class BatchLauncherTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix='shelf batch ')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in ('shelf.py', 'catalog.py', 'desktop.py', 'sync.py', 'transfer.py',
                     'Start arXiv Shelf.bat', 'Start arXiv Shelf.sh'):
            shutil.copy2(ROOT / name, root / name)
        downloads = root / 'Downloads with spaces'
        downloads.mkdir()
        (downloads / '2302.13971.pdf').write_bytes(b'%PDF-1.4 fixture')
        return root, ['--offline', '--scan-only', '--directory', str(downloads),
                      '--cache', str(root / 'cache.json'), '--catalog', str(root / 'catalog')]

    @unittest.skipUnless(desktop.is_wsl() and shutil.which('powershell.exe') and shutil.which('wsl.exe'),
                         'Requires Windows/WSL interop')
    def test_windows_batch_hands_wsl_unc_checkout_to_correct_distribution(self):
        root, arguments = self.fixture()
        environment = root / '.venv/bin'
        environment.mkdir(parents=True)
        (environment / 'python').symlink_to(sys.executable)
        launcher = subprocess.check_output(['wslpath', '-w', str(root / 'Start arXiv Shelf.bat')], text=True).strip()
        script = '& ' + desktop.ps_literal(launcher) + ' ' + ' '.join(desktop.ps_literal(a) for a in arguments)
        encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                                cwd='/mnt/c', input=b'\n', capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertIn(b'1 local files', result.stdout)
        self.assertTrue((root / 'cache.json').exists())

    @unittest.skipUnless(sys.platform == 'win32', 'Requires native Windows Python')
    def test_native_windows_batch_selects_project_environment(self):
        root, arguments = self.fixture()
        subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(root / '.venv')],
                       check=True, capture_output=True, timeout=30)
        command = subprocess.list2cmdline([str(root / 'Start arXiv Shelf.bat'), *arguments])
        result = subprocess.run(command, shell=True, input=b'\n', capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertIn(b'1 local files', result.stdout)
        self.assertTrue((root / 'cache.json').exists())


if __name__ == '__main__':
    unittest.main()
