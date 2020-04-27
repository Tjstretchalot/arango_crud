"""One pain point is deciding what the test classnames should be. There's no
correct answer here, but it's annoying if it's inconsistent. This test verifies
that every test in the tests/ folder has a 'Test' TestCase"""
import unittest
import os
import importlib


class Test(unittest.TestCase):
    def test_test_setup(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        for curdir, _, files in os.walk(dir_path):
            for f in files:
                if f.startswith('test') and f.endswith('.py'):
                    fullpath = os.path.join(curdir, f)
                    relpath = fullpath[len(dir_path) + len(os.path.sep):-3]
                    mod_nm = '.'.join(relpath.split(os.path.sep))
                    if mod_nm == 'test_test_classnames':
                        continue
                    mod = importlib.import_module(mod_nm)
                    self.assertTrue(hasattr(mod, 'Test'), mod_nm)
                    self.assertIsInstance(mod.Test(), unittest.TestCase)


if __name__ == '__main__':
    unittest.main()
