import unittest
import helper
from arango_crud import (  # noqa: E402
    env_config,
    RandomCluster,
    WeightedRandomCluster,
    StepBackOffStrategy,
    BasicAuth,
    JWTAuth,
    JWTDiskCache
)
from arango_crud.auths import StatefulAuthWrapper  # noqa: E402


class Test(unittest.TestCase):
    def test_cluster_random(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_CLUSTER_STYLE': 'random',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertIsInstance(cfg.cluster, RandomCluster)
        self.assertEqual(cfg.cluster.urls, ['http://localhost:5289'])

        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289,http://localhost:5290',
                'ARANGO_CLUSTER_STYLE': 'random',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertIsInstance(cfg.cluster, RandomCluster)
        self.assertEqual(cfg.cluster.urls, ['http://localhost:5289', 'http://localhost:5290'])

    def test_cluster_weighted_random(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289,http://localhost:5290',
                'ARANGO_CLUSTER_STYLE': 'weighted-random',
                'ARANGO_CLUSTER_WEIGHTS': '1,2.1',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertIsInstance(cfg.cluster, WeightedRandomCluster)
        self.assertEqual(cfg.cluster.urls, ['http://localhost:5289', 'http://localhost:5290'])
        self.assertEqual(cfg.cluster.weights, [1.0, 2.1])

    def test_timeout(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'basic',
                'ARANGO_TIMEOUT_SECONDS': '20',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertEqual(cfg.timeout_seconds, 20.0)

    def test_back_off_step(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_BACK_OFF': 'step',
                'ARANGO_BACK_OFF_STEPS': '1,2.5,0.1',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertIsInstance(cfg.back_off, StepBackOffStrategy)
        self.assertEqual(cfg.back_off.steps, [1.0, 2.5, 0.1])

    def test_ttl(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_TTL_SECONDS': '12000',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertEqual(cfg.ttl_seconds, 12000)

    def test_basic_auth(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertIsInstance(cfg.auth, BasicAuth)
        self.assertEqual(cfg.auth.username, helper.TEST_USERNAME)
        self.assertEqual(cfg.auth.password, helper.TEST_PASSWORD)

    def test_jwt_auth_no_cache(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'jwt',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_AUTH_CACHE': 'none'
            }
        )
        self.assertIsInstance(cfg.auth, StatefulAuthWrapper)
        self.assertIsInstance(cfg.auth.delegate, JWTAuth)
        self.assertEqual(cfg.auth.delegate.username, helper.TEST_USERNAME)
        self.assertEqual(cfg.auth.delegate.password, helper.TEST_PASSWORD)
        self.assertIsNone(cfg.auth.delegate.cache)

    def test_jwt_auth_disk_cache(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'jwt',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_AUTH_CACHE': 'disk',
                'ARANGO_AUTH_CACHE_LOCK_FILE': 'foo.lock',
                'ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS': '10',
                'ARANGO_AUTH_CACHE_STORE_FILE': 'foo.jwt'
            }
        )
        self.assertIsInstance(cfg.auth, StatefulAuthWrapper)
        self.assertIsInstance(cfg.auth.delegate, JWTAuth)
        self.assertEqual(cfg.auth.delegate.username, helper.TEST_USERNAME)
        self.assertEqual(cfg.auth.delegate.password, helper.TEST_PASSWORD)
        self.assertIsInstance(cfg.auth.delegate.cache, JWTDiskCache)
        self.assertEqual(cfg.auth.delegate.cache.lock_file, 'foo.lock')
        self.assertEqual(cfg.auth.delegate.cache.lock_time_seconds, 10.0)
        self.assertEqual(cfg.auth.delegate.cache.store_file, 'foo.jwt')

    def test_disable_db_delete(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_DISABLE_DATABASE_DELETE': 'false'
            }
        )
        self.assertFalse(cfg.disable_database_delete)

    def test_protect_db(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_DISABLE_DATABASE_DELETE': 'false',
                'ARANGO_PROTECTED_DATABASES': 'test_db,test_db2'
            }
        )
        self.assertFalse(cfg.disable_database_delete)
        self.assertEqual(cfg.protected_databases, ['test_db', 'test_db2'])

    def test_disable_coll_delete(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_DISABLE_COLLECTION_DELETE': 'false'
            }
        )
        self.assertFalse(cfg.disable_collection_delete)

    def test_protect_coll(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:5289',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_DISABLE_COLLECTION_DELETE': 'false',
                'ARANGO_PROTECTED_COLLECTIONS': 'test_coll,test_coll2'
            }
        )
        self.assertFalse(cfg.disable_collection_delete)
        self.assertEqual(cfg.protected_collections, ['test_coll', 'test_coll2'])


if __name__ == '__main__':
    unittest.main()
