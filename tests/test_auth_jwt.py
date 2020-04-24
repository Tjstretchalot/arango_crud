import unittest
import helper
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    StepBackOffStrategy,
    JWTAuth,
    JWTDiskCache
)


def my_runner(cfg, copy=False):
    """Used for testing concurrency"""
    if copy:
        cfg = cfg.thread_safe_copy()
    return (
        cfg
        .database(helper.TEST_ARANGO_DB)
        .check_if_exists()
    )


class Test(unittest.TestCase):
    def test_database_exists_no_cache(self):
        cfg = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=10,
            back_off=StepBackOffStrategy(steps=[1]),
            ttl_seconds=None,
            auth=JWTAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD,
                cache=None
            )
        )
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertFalse(db.check_if_exists())

    def test_database_exists_disk_cache(self):
        self.assertFalse(os.path.exists('test.jwt'))
        self.assertFalse(os.path.exists('test.jwt.lock'))

        def create_config():
            return Config(
                cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
                timeout_seconds=10,
                back_off=StepBackOffStrategy(steps=[1]),
                ttl_seconds=None,
                auth=JWTAuth(
                    username=helper.TEST_USERNAME,
                    password=helper.TEST_PASSWORD,
                    cache=JWTDiskCache(
                        lock_file='test.jwt.lock',
                        lock_time_seconds=10,
                        store_file='test.jwt'
                    )
                )
            )

        for i in range(3):
            cfg = create_config()
            db = cfg.database(helper.TEST_ARANGO_DB)
            for i in range(3):
                self.assertFalse(db.check_if_exists())

        self.assertTrue(os.path.exists('test.jwt'))
        os.remove('test.jwt')
        if os.path.exists('test.jwt.lock'):
            os.remove('test.jwt.lock')

        cfg = create_config()

        with ThreadPoolExecutor(max_workers=8) as executor:
            res = executor.map(
                my_runner,
                [cfg for _ in range(100)],
                [True for _ in range(100)]
            )
            for i, val in enumerate(res):
                self.assertFalse(val, f'res={res}, i={i}')

        self.assertTrue(os.path.exists('test.jwt'))
        os.remove('test.jwt')
        if os.path.exists('test.jwt.lock'):
            os.remove('test.jwt.lock')

        with ProcessPoolExecutor(max_workers=8) as executor:
            res = executor.map(my_runner, [cfg for _ in range(100)])
            for i, val in enumerate(res):
                self.assertFalse(val, f'res={res}, i={i}')

        self.assertTrue(os.path.exists('test.jwt'))
        os.remove('test.jwt')
        if os.path.exists('test.jwt.lock'):
            os.remove('test.jwt.lock')


if __name__ == '__main__':
    unittest.main()
