import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import update


class ActivityTests(unittest.TestCase):
    def test_same_day_is_idempotent(self):
        record = update.next_record({}, '2026-01-01')
        self.assertEqual(update.next_record(record, '2026-01-01'), record)

    def test_new_day_increments_once(self):
        record = update.next_record({'date': '2026-01-01', 'days_recorded': 3}, '2026-01-02')
        self.assertEqual(record['days_recorded'], 4)
        self.assertEqual(set(record), {'date', 'days_recorded', 'kind'})

    def test_clock_regression_is_rejected(self):
        with self.assertRaises(ValueError):
            update.next_record({'date': '2026-01-02'}, '2026-01-01')

    def test_local_push_and_retry_do_not_duplicate_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin, seed, checkout = root/'origin.git', root/'seed', root/'checkout'
            def run(*args):
                return subprocess.run(['git', *map(str, args)], check=True, capture_output=True, text=True).stdout.strip()
            run('init', '--bare', '--initial-branch=main', origin)
            run('init', '--initial-branch=main', seed)
            run('-C', seed, 'config', 'user.name', 'Offline Fixture')
            run('-C', seed, 'config', 'user.email', 'fixture@example.invalid')
            (seed/'README.md').write_text('Offline test only\n')
            run('-C', seed, 'add', 'README.md')
            run('-C', seed, 'commit', '-m', 'Initialize fixture')
            run('-C', seed, 'remote', 'add', 'origin', origin)
            run('-C', seed, 'push', 'origin', 'main')
            with patch.dict(os.environ, {'GARDEN_REPO_DIR': str(checkout), 'GARDEN_REMOTE': str(origin),
                    'GARDEN_AUTHOR_NAME': 'Offline Fixture', 'GARDEN_AUTHOR_EMAIL': 'fixture@example.invalid'}):
                update.main()
                head = run('--git-dir', origin, 'rev-parse', 'main')
                update.main()
                self.assertEqual(run('--git-dir', origin, 'rev-parse', 'main'), head)
                self.assertEqual(json.loads((checkout/'activity.json').read_text())['days_recorded'], 1)
                (checkout/'unrelated.txt').write_text('must not be committed')
                with self.assertRaises(ValueError): update.main()


if __name__ == '__main__':
    unittest.main()
