#!/usr/bin/env python3
"""Publish one transparent, decorative activity record per calendar day."""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def git(repo, *args, check=True):
    return subprocess.run(['git', '-C', str(repo), *args], check=check,
                          capture_output=True, text=True, timeout=90)


def next_record(previous, today):
    last = previous.get('date')
    if last == today:
        return previous
    if last and last > today:
        raise ValueError('Refusing to move the activity date backwards')
    return {'date': today, 'days_recorded': int(previous.get('days_recorded', 0)) + 1,
            'kind': 'automated decorative activity'}


def main():
    repo = Path(os.environ.get('GARDEN_REPO_DIR', '/var/lib/activity-garden/repository'))
    remote = os.environ['GARDEN_REMOTE']
    author_name = os.environ['GARDEN_AUTHOR_NAME']
    author_email = os.environ['GARDEN_AUTHOR_EMAIL']
    today = datetime.now(ZoneInfo(os.environ.get('GARDEN_TIMEZONE', 'Europe/Paris'))).date().isoformat()
    if not (repo / '.git').is_dir():
        repo.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--single-branch', '--branch', 'main', remote, str(repo)],
                       check=True, capture_output=True, text=True, timeout=90)
    if git(repo, 'remote', 'get-url', 'origin').stdout.strip() != remote:
        raise ValueError('Unexpected origin; refusing to push')
    if git(repo, 'branch', '--show-current').stdout.strip() != 'main':
        raise ValueError('Expected the main branch')
    git(repo, 'config', 'user.name', author_name)
    git(repo, 'config', 'user.email', author_email)
    changed = git(repo, 'status', '--porcelain', '--untracked-files=all').stdout.splitlines()
    if any(line[3:] != 'activity.json' for line in changed):
        raise ValueError('Unexpected local changes; refusing to commit')
    git(repo, 'fetch', 'origin', 'main')
    git(repo, 'merge', '--ff-only', 'origin/main')
    path = repo / 'activity.json'
    previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    current = next_record(previous, today)
    if current != previous:
        temporary = repo / '.activity.json.tmp'
        temporary.write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    git(repo, 'add', '--', 'activity.json')
    status = git(repo, 'diff', '--cached', '--quiet', check=False)
    if status.returncode == 1:
        git(repo, 'commit', '-m', f'chore: daily decorative activity {today}')
    elif status.returncode != 0:
        raise RuntimeError('Could not inspect staged changes')
    # A retry pushes any commit left behind by an earlier connection failure.
    git(repo, 'push', 'origin', 'HEAD:main')
    print(f'Activity record up to date for {today}.')


if __name__ == '__main__':
    main()
