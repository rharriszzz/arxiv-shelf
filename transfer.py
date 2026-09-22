"""PDF transport with one curl retry for arXiv's HTTP 406 client incompatibility."""
from contextlib import contextmanager
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import urlopen


@contextmanager
def pdf_response(request):
    try:
        response = urlopen(request, timeout=90)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        if code != 406 or not shutil.which('curl'):
            raise
    else:
        with response:
            yield response
        return

    # A single, spaced retry; never retry access denial or rate limiting.
    time.sleep(3.2)
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            ['curl', '--fail', '--silent', '--show-error', '--location',
             '--max-time', '90', '--proto', '=https', '--proto-redir', '=https',
             '--user-agent', request.get_header('User-agent'), request.full_url],
            stdout=subprocess.PIPE, stderr=errors)
        try:
            class Response:
                # Curl validates response length itself. Without a known total,
                # the UI displays bytes received and an indeterminate progress bar.
                headers = {}

                def read(self, size):
                    data = process.stdout.read(size)
                    if not data:
                        status = process.wait(timeout=5)
                        if status:
                            errors.seek(0)
                            detail = errors.read(2000).decode('utf-8', errors='replace').strip()
                            raise ValueError('PDF download failed: ' + (detail or f'curl exited with {status}'))
                    return data

            yield Response()
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
