import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

import theme


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def binary(self):
        old, new = b'headOLDtail', b'headNEWtail'
        key = theme.digest(b'NEW')
        (self.root / 'value.z').write_bytes(zlib.compress(b'NEW'))
        span = {'offset': 4, 'length': 3, 'before': theme.digest(b'OLD'), 'after': key,
                'asset': 'value.z', 'asset_sha256': key, 'mode': 'bytes'}
        spec = {'path': 'test', 'size': len(old), 'spans': [span],
                'outside_sha256': [theme.outside_hash(old, [span])]}
        return old, new, spec

    def test_binary_reapplication_and_unrelated_changes(self):
        old, new, spec = self.binary()
        self.assertEqual(theme.transform_binary(old, spec, self.root), (new, 1))
        self.assertEqual(theme.transform_binary(new, spec, self.root), (new, 0))
        for invalid in (b'headBADtail', b'HEADOLDtail', old + b'!'):
            with self.assertRaises(ValueError):
                theme.transform_binary(invalid, spec, self.root)

    def test_corrupt_asset_rejected_even_if_already_applied(self):
        _, new, spec = self.binary()
        (self.root / 'value.z').write_bytes(zlib.compress(b'BAD'))
        with self.assertRaises(ValueError):
            theme.transform_binary(new, spec, self.root)

    def test_overlaps_and_path_traversal_rejected(self):
        old, _, spec = self.binary()
        with self.assertRaises(ValueError):
            theme.outside_hash(old, spec['spans'] * 2)
        with self.assertRaises(ValueError):
            theme.child(self.root, '../outside')

    def test_fusion_preserves_other_entries_and_is_idempotent(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as archive:
            archive.comment = b'preserve'
            archive.writestr('Fusion.skin', b'CoralRed = { 230, 75, 61 }\r\n')
            archive.writestr('icon', b'unchanged bytes')
        before = b'CoralRed = { 230, 75, 61 }\r\n'
        after = b'CoralRed = { 255, 94, 173 }\r\n'
        spec = {'members': {'icon': theme.digest(b'unchanged bytes')},
                'before_skin': theme.digest(before), 'after_skin': theme.digest(after),
                'edits': [{'name': 'CoralRed', 'before': before.decode().strip(),
                           'after': after.decode().strip()}]}
        output, count = theme.transform_fusion(buf.getvalue(), spec)
        self.assertEqual(count, 1)
        self.assertEqual(theme.transform_fusion(output, spec), (output, 0))
        with zipfile.ZipFile(io.BytesIO(output)) as archive:
            self.assertEqual(archive.read('icon'), b'unchanged bytes')
            self.assertEqual(archive.read('Fusion.skin'), after)
            self.assertEqual(archive.comment, b'preserve')

    def plans(self):
        plans = []
        for name in ('Resolve.exe', 'BMDDavUI.dll'):
            path = self.root / name
            path.write_bytes(b'original')
            plans.append({'relative': name, 'path': path, 'before': theme.digest(b'original'),
                          'after': theme.digest(b'updated'), 'output': b'updated'})
        return plans

    @patch.object(theme, 'ensure_closed')
    def test_transaction_rolls_back_if_second_replace_fails(self, _closed):
        plans = self.plans()
        real_replace = theme.os.replace

        def failing_replace(source, destination):
            if str(source).endswith('.theme-tmp') and Path(destination).name == 'BMDDavUI.dll':
                raise OSError('injected write failure')
            return real_replace(source, destination)

        with patch.object(theme.os, 'replace', side_effect=failing_replace):
            with self.assertRaises(OSError):
                theme.commit(self.root, plans)
        self.assertTrue(all(p['path'].read_bytes() == b'original' for p in plans))
        state = next((self.root / '.blackpink-backups').glob('*/state.json'))
        self.assertEqual(json.loads(state.read_text())['status'], 'rolled_back')
        self.assertFalse((self.root / '.blackpink.lock').exists())

    @patch.object(theme, 'ensure_closed')
    def test_verified_restore_and_changed_target_refusal(self, _closed):
        plans = self.plans()
        state = theme.commit(self.root, plans)
        plans[0]['path'].write_bytes(b'user changed this')
        with self.assertRaises(ValueError):
            theme.plan_restore(self.root, state)
        plans[0]['path'].write_bytes(b'updated')
        restore = theme.plan_restore(self.root, state)
        theme.commit(self.root, restore, 'restore')
        self.assertTrue(all(p['path'].read_bytes() == b'original' for p in plans))
        self.assertEqual(theme.plan_restore(self.root, state), [])


if __name__ == '__main__':
    unittest.main()
