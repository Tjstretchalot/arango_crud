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
            disable_database_delete=False
        )
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertFalse(db.check_if_exists())
        self.assertTrue(db.create_if_not_exists())
        self.assertTrue(db.check_if_exists())
        self.assertFalse(db.create_if_not_exists())
        self.assertTrue(db.force_delete())
        self.assertFalse(db.force_delete())

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
        self.assertRaises(AssertionError, lambda: db.force_delete())

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
            protected_databases=[helper.TEST_ARANGO_DB]
        )

        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertRaises(AssertionError, lambda: db.force_delete())


if __name__ == '__main__':
    unittest.main()
