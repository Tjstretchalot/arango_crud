import unittest
import helper
from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    StepBackOffStrategy,
    BasicAuth
)


def create_config():
    return Config(
        cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
        timeout_seconds=10,
        back_off=StepBackOffStrategy(steps=[1]),
        ttl_seconds=None,
        auth=BasicAuth(
            username=helper.TEST_USERNAME,
            password=helper.TEST_PASSWORD
        ),
        disable_database_delete=False,
        disable_collection_delete=False
    )


class Test(unittest.TestCase):
    def test_create_read_delete(self):
        cfg = create_config()
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        self.assertEqual(doc.body, {})
        self.assertFalse(doc.read())
        self.assertEqual(doc.body, {})
        self.assertFalse(doc.read())
        self.assertEqual(doc.body, {})
        self.assertRaises(AssertionError, lambda: doc.read_if_remote_newer())
        self.assertRaises(AssertionError, lambda: doc.compare_and_delete())
        self.assertRaises(AssertionError, lambda: doc.compare_and_swap())
        self.assertFalse(doc.overwrite())
        self.assertFalse(doc.read())
        self.assertTrue(doc.create())
        self.assertEqual(doc.body, {})
        self.assertEqual(doc.body, {})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {})
        self.assertFalse(doc.read_if_remote_newer())
        self.assertEqual(doc.body, {})
        self.assertTrue(doc.compare_and_swap())
        self.assertEqual(doc.body, {})
        doc.body['a'] = 3
        self.assertEqual(doc.body, {'a': 3})
        self.assertTrue(doc.compare_and_swap())
        self.assertEqual(doc.body, {'a': 3})
        self.assertFalse(doc.read_if_remote_newer())
        self.assertEqual(doc.body, {'a': 3})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 3})
        doc.body['b'] = 4
        self.assertEqual(doc.body, {'a': 3, 'b': 4})
        self.assertTrue(doc.overwrite())
        self.assertEqual(doc.body, {'a': 3, 'b': 4})
        self.assertFalse(doc.read_if_remote_newer())
        self.assertEqual(doc.body, {'a': 3, 'b': 4})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 3, 'b': 4})
        self.assertTrue(doc.compare_and_delete())
        self.assertEqual(doc.body, {'a': 3, 'b': 4})
        self.assertFalse(doc.read())
        self.assertRaises(AssertionError, lambda: doc.compare_and_delete())

        self.assertTrue(db.force_delete())

    def test_create(self):
        cfg = create_config()

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        doc.body['a'] = 3
        self.assertTrue(doc.create())
        self.assertRaises(AssertionError, lambda: doc.create())

        doc = coll.document('test_doc')
        doc.body['b'] = 4
        self.assertFalse(doc.create())
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 3})

        self.assertTrue(db.force_delete())

    def test_compare_and_swap(self):
        cfg = create_config()

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        doc.body['a'] = 7
        self.assertTrue(doc.create())
        doc.body['a'] = 6
        self.assertTrue(doc.compare_and_swap())
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 6})

        doc2 = coll.document('test_doc')
        self.assertTrue(doc2.read())
        self.assertEqual(doc2.body, {'a': 6})
        doc2.body['a'] = 13
        self.assertTrue(doc2.compare_and_swap())
        self.assertEqual(doc2.body, {'a': 13})

        doc.body['a'] = 3
        self.assertTrue(doc.overwrite())
        self.assertFalse(doc2.compare_and_swap())
        self.assertEqual(doc2.body, {'a': 13})
        self.assertTrue(doc2.read())
        self.assertEqual(doc2.body, {'a': 3})

        self.assertTrue(db.force_delete())

    def test_overwrite(self):
        cfg = create_config()

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        doc.body['foo'] = 'bar'
        self.assertFalse(doc.overwrite())
        self.assertEqual(doc.body, {'foo': 'bar'})
        self.assertTrue(doc.create())
        self.assertEqual(doc.body, {'foo': 'bar'})
        doc.body['foo'] = 'baz'
        self.assertTrue(doc.overwrite())
        self.assertEqual(doc.body, {'foo': 'baz'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'foo': 'baz'})

        doc2 = coll.document('test_doc')
        doc2.body['bar'] = 'foo'
        self.assertTrue(doc2.overwrite())
        self.assertEqual(doc2.body, {'bar': 'foo'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'bar': 'foo'})

        self.assertTrue(db.force_delete())

    def test_create_or_overwrite(self):
        cfg = create_config()

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        doc.body['a'] = 'b'
        self.assertTrue(doc.create_or_overwrite())
        self.assertEqual(doc.body, {'a': 'b'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 'b'})
        doc.body['b'] = 'c'
        self.assertEqual(doc.body, {'a': 'b', 'b': 'c'})
        self.assertTrue(doc.create_or_overwrite())
        self.assertEqual(doc.body, {'a': 'b', 'b': 'c'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 'b', 'b': 'c'})

        self.assertTrue(db.force_delete())

    def test_compare_and_delete(self):
        cfg = create_config()

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        self.assertRaises(AssertionError, lambda: doc.compare_and_delete())

        doc.body['a'] = 'A'
        self.assertTrue(doc.create())
        self.assertTrue(doc.compare_and_delete())
        self.assertEqual(doc.body, {'a': 'A'})
        self.assertFalse(doc.read())
        self.assertEqual(doc.body, {})
        self.assertRaises(AssertionError, lambda: doc.compare_and_delete())

        doc.body['a'] = 'A'
        self.assertTrue(doc.create())

        doc2 = coll.document('test_doc')
        self.assertRaises(AssertionError, lambda: doc2.compare_and_delete())
        self.assertTrue(doc2.read())
        self.assertEqual(doc2.body, {'a': 'A'})
        doc2.body['b'] = 'B'
        self.assertTrue(doc2.compare_and_swap())
        self.assertEqual(doc2.body, {'a': 'A', 'b': 'B'})

        self.assertFalse(doc.compare_and_delete())
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 'A', 'b': 'B'})
        self.assertTrue(doc.compare_and_delete())
        self.assertFalse(doc.read())
        self.assertFalse(doc2.read())

        self.assertRaises(AssertionError, lambda: doc.compare_and_delete())
        self.assertRaises(AssertionError, lambda: doc2.compare_and_delete())

        self.assertTrue(db.force_delete())

    def test_force_delete(self):
        cfg = create_config()

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        doc = coll.document('test_doc')
        self.assertFalse(doc.force_delete())
        doc.body['a'] = 'z'
        self.assertTrue(doc.create())
        self.assertEqual(doc.body, {'a': 'z'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'a': 'z'})
        self.assertTrue(doc.force_delete())
        self.assertFalse(doc.read())
        self.assertEqual(doc.body, {})
        self.assertFalse(doc.force_delete())
        doc.body['a'] = 'z'
        self.assertEqual(doc.body, {'a': 'z'})
        self.assertTrue(doc.create())

        doc2 = coll.document('test_doc')
        self.assertTrue(doc2.read())
        self.assertEqual(doc2.body, {'a': 'z'})
        doc2.body['z'] = 'y'
        self.assertEqual(doc2.body, {'a': 'z', 'z': 'y'})
        self.assertTrue(doc2.compare_and_swap())
        self.assertEqual(doc2.body, {'a': 'z', 'z': 'y'})

        self.assertTrue(doc.force_delete())
        self.assertFalse(doc2.read())
        self.assertFalse(doc.read())

        self.assertTrue(db.force_delete())


if __name__ == '__main__':
    unittest.main()
