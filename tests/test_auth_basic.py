import unittest
import helper
from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    StepBackOffStrategy,
    BasicAuth
)


class Test(unittest.TestCase):
    def test_database_exists(self):
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
        self.assertFalse(db.check_if_exists())

    def test_recover(self):
        auth = BasicAuth(
            username=helper.TEST_USERNAME,
            password=helper.TEST_PASSWORD
        )
        self.assertFalse(auth.try_recover_auth_failure())


if __name__ == '__main__':
    unittest.main()
