"""Starting green test uses the wrong producer shape, intentionally."""
import unittest

from app import count_records


class SyncDouble:
    def fetch(self):
        return [{"id": "first"}, {"id": "second"}]


class StartingTests(unittest.IsolatedAsyncioTestCase):
    async def test_synchronous_double_is_green(self):
        self.assertEqual(await count_records(SyncDouble()), 2)
