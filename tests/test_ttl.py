"""Tests using the TTL; arangodb can have long delays on actually applying
TTL indices so this isn't as strong as a test as we'd like"""
import unittest
import helper  # noqa: F401
from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    StepBackOffStrategy,
    BasicAuth
)


class Test(unittest.TestCase):
    def test_collection_default_ttl(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=2,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            ),
            disable_database_delete=False
        )

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        coll.create_or_overwrite_doc('test_doc', {'foo': 3})
        self.assertEqual(coll.read_doc('test_doc'), {'foo': 3})
        self.assertTrue(db.force_delete())

    def test_collection_no_ttl(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=None,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            ),
            disable_database_delete=False
        )
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        coll.create_or_overwrite_doc('test_doc', {'foo': 3})
        self.assertEqual(coll.read_doc('test_doc'), {'foo': 3})

        self.assertTrue(db.force_delete())

    def test_override_ttl(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=2,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            ),
            disable_database_delete=False
        )

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        coll.create_or_overwrite_doc('test_doc', {'foo': 3}, ttl=6)
        self.assertEqual(coll.read_doc('test_doc'), {'foo': 3})
        self.assertTrue(db.force_delete())

    def test_override_to_no_ttl(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=2,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            ),
            disable_database_delete=False
        )

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        coll.create_or_overwrite_doc('test_doc', {'foo': 3}, ttl=None)
        self.assertEqual(coll.read_doc('test_doc'), {'foo': 3})
        self.assertTrue(db.force_delete())


if __name__ == '__main__':
    unittest.main()
