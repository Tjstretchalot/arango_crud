import unittest
import helper
from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    StepBackOffStrategy,
    BasicAuth
)


class Test(unittest.TestCase):
    def test_create_read_delete(self):
        cfg = Config(
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
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertFalse(coll.check_if_exists())
        self.assertFalse(coll.force_delete())
        self.assertTrue(coll.create_if_not_exists())
        self.assertTrue(coll.check_if_exists())
        self.assertFalse(coll.create_if_not_exists())
        self.assertTrue(coll.force_delete())

        self.assertTrue(db.force_delete())

    def test_create_delete_ttl(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=10,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            ),
            disable_database_delete=False,
            disable_collection_delete=False
        )
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertFalse(coll.check_if_exists())
        self.assertFalse(coll.force_delete())
        self.assertTrue(coll.create_if_not_exists())
        self.assertTrue(coll.check_if_exists())
        self.assertFalse(coll.create_if_not_exists())
        self.assertTrue(coll.force_delete())

        self.assertTrue(db.force_delete())

    def test_disable_delete(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=None,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            )
        )
        db = cfg.database(helper.TEST_ARANGO_DB)
        coll = db.collection('test_coll')
        self.assertRaises(AssertionError, lambda: coll.force_delete())

    def test_protect(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=None,
            auth=BasicAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD
            ),
            disable_database_delete=False,
            disable_collection_delete=False,
            protected_collections=['test_coll']
        )
        db = cfg.database(helper.TEST_ARANGO_DB)
        coll = db.collection('test_coll')
        self.assertRaises(AssertionError, lambda: coll.force_delete())

        self.assertTrue(db.create_if_not_exists())
        coll = db.collection('test_coll2')
        self.assertFalse(coll.force_delete())
        self.assertTrue(db.force_delete())


if __name__ == '__main__':
    unittest.main()
