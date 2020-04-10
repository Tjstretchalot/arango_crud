import unittest
import sys

sys.path.append('src')

from arango_crud import Config  # noqa: E402


class Test(unittest.TestCase):
    def test_foo(self):
        self.assertIsNotNone(Config)
        self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
