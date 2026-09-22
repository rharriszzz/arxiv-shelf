"""Explicit Git synchronization for a catalog inside the app's repository."""
from pathlib import Path
import subprocess


def git_sync(repository, catalog):
    repository, catalog = Path(repository).resolve(), Path(catalog).resolve()
    if not catalog.is_relative_to(repository) or catalog == repository:
        raise ValueError('GitHub sync requires a catalog folder inside this repository.')
    relative = catalog.relative_to(repository).as_posix()
    if relative.startswith('.git/') or relative == '.git':
        raise ValueError('Invalid catalog folder.')

    def git(*args):
        # Disable credential prompts: report an actionable error in the app instead.
        import os
        env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0',
               'GIT_SSH_COMMAND': 'ssh -o BatchMode=yes -o StrictHostKeyChecking=yes'}
        result = subprocess.run(['git', *args], cwd=repository, env=env,
                                capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Git command failed.')
        return result.stdout

    branch = git('symbolic-ref', '--short', 'HEAD').strip()
    # Do not commit, stash, or rebase unrelated work from the application.
    changed = set()
    for args in [('diff', '--name-only', '-z'), ('diff', '--cached', '--name-only', '-z'),
                 ('ls-files', '--others', '--exclude-standard', '-z')]:
        changed.update(filter(None, git(*args).split('\0')))
    if any(not path.startswith(relative + '/') for path in changed):
        raise ValueError('There are uncommitted app changes. Commit or stash them in your terminal before syncing the catalog.')
    if changed:
        git('add', '--', relative)
        git('commit', '--only', '-m', 'Update paper catalog and ratings', '--', relative)
    git('pull', '--rebase', 'origin', branch)
    git('push', 'origin', branch)
    return 'Catalog and ratings synced with GitHub'
