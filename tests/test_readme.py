import unittest
import helper
from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    WeightedRandomCluster,
    StepBackOffStrategy,
    BasicAuth,
    JWTAuth, JWTDiskCache,
    env_config
)


class Test(unittest.TestCase):
    def test_code_as_config_basic_auth(self):
        config = Config(
            cluster=RandomCluster(urls=['http://127.0.0.1:8529']),  # see Cluster Styles
            timeout_seconds=3,
            back_off=StepBackOffStrategy([0.1, 0.5, 1, 1, 1]),  # see Back Off Strategies
            auth=BasicAuth(username='root', password=''),
            ttl_seconds=31622400
        )
        self.assertIsNotNone(config)

    def test_code_as_config_jwt(self):
        config = Config(
            cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
            timeout_seconds=3,
            back_off=StepBackOffStrategy(steps=[0.1, 0.5, 1, 1, 1]),
            ttl_seconds=31622400,
            auth=JWTAuth(
                username=helper.TEST_USERNAME,
                password=helper.TEST_PASSWORD,
                cache=JWTDiskCache(  # See JWT Caches
                    lock_file='.arango_jwt.lock',
                    lock_time_seconds=10,
                    store_file='.arango_jwt'
                )
            )
        )
        self.assertIsNotNone(config)
        config.prepare()

    def test_envvar_basic_auth(self):
        config = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:8529',
                'ARANGO_CLUSTER_STYLE': 'random',
                'ARANGO_TIMEOUT_SECONDS': 3,
                'ARANGO_BACK_OFF': 'step',
                'ARANGO_BACK_OFF_STEPS': '0.1,0.5,1,1,1',
                'ARANGO_TTL_SECONDS': '31622400',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': 'root',
                'ARANGO_AUTH_PASSWORD': ''
            }
        )
        self.assertIsNotNone(config)

    def test_envvar_jwt(self):
        config = env_config(
            cfg={
                'ARANGO_CLUSTER': 'http://localhost:8529',
                'ARANGO_CLUSTER_STYLE': 'random',
                'ARANGO_TIMEOUT_SECONDS': 3,
                'ARANGO_BACK_OFF': 'step',
                'ARANGO_BACK_OFF_STEPS': '0.1,0.5,1,1,1',
                'ARANGO_TTL_SECONDS': '31622400',
                'ARANGO_AUTH': 'jwt',
                'ARANGO_AUTH_USERNAME': 'root',
                'ARANGO_AUTH_PASSWORD': '',
                'ARANGO_AUTH_CACHE': 'disk',
                'ARANGO_AUTH_CACHE_LOCK_FILE': '.arango_jwt.lock',
                'ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS': '10',
                'ARANGO_AUTH_CACHE_STORE_FILE': '.arango_jwt'
            }
        )
        self.assertIsNotNone(config)

    def test_crud(self):
        config = env_config(
            cfg={
                'ARANGO_CLUSTER': ','.join(helper.TEST_CLUSTER_URLS),
                'ARANGO_CLUSTER_STYLE': 'random',
                'ARANGO_TIMEOUT_SECONDS': 3,
                'ARANGO_BACK_OFF': 'step',
                'ARANGO_BACK_OFF_STEPS': '0.1,0.5,1,1,1',
                'ARANGO_TTL_SECONDS': '31622400',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD,
                'ARANGO_DISABLE_DATABASE_DELETE': 'false',
                'ARANGO_DISABLE_COLLECTION_DELETE': 'false'
            }
        )
        config.prepare()

        db = config.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())
        coll = db.collection('users')
        self.assertTrue(coll.create_if_not_exists())

        # The simplest interface
        self.assertIsNone(coll.create_or_overwrite_doc('tj', {'name': 'TJ'}))
        self.assertEqual(coll.read_doc('tj'), {'name': 'TJ'})
        self.assertTrue(coll.force_delete_doc('tj'))

        # non-expiring
        coll.create_or_overwrite_doc('tj', {'name': 'TJ'}, ttl=None)
        self.assertTrue(coll.force_delete_doc('tj'))

        # custom expirations with touching. Note that touching a document is not
        # a supported atomic operation on ArangoDB and is hence faked with
        # read -> compare_and_swap. Presumably if the CAS fails the document was
        # touched recently anyway.
        coll.create_or_overwrite_doc('tj', {'name': 'TJ'}, ttl=30)
        self.assertTrue(coll.touch_doc('tj', ttl=60))
        self.assertTrue(coll.force_delete_doc('tj'))

        # Alternative interface. For anything except one-liners, usually nicer.
        doc = coll.document('tj')
        doc.body['name'] = 'TJ'
        self.assertTrue(doc.create())
        doc.body['note'] = 'Pretty cool'
        self.assertTrue(doc.compare_and_swap())

        # We may use etags to avoid redownloading an unchanged document, but be careful
        # if you are modifying the body.

        # Happy case:
        doc2 = coll.document('tj')
        self.assertTrue(doc2.read())
        self.assertEqual(doc2.body, {'name': 'TJ', 'note': 'Pretty cool'})

        self.assertFalse(doc.read_if_remote_newer())
        self.assertFalse(doc2.read_if_remote_newer())

        doc.body['note'] = 'bar'
        self.assertTrue(doc.compare_and_swap())
        self.assertFalse(doc.read_if_remote_newer())
        self.assertTrue(doc2.read_if_remote_newer())
        self.assertEqual(doc2.body, {'name': 'TJ', 'note': 'bar'})

        # Where it can get dangerous
        doc.body['note'] = 'foo'
        self.assertEqual(doc.body, {'name': 'TJ', 'note': 'foo'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'name': 'TJ', 'note': 'bar'})
        self.assertFalse(doc.read_if_remote_newer())
        self.assertEqual(doc.body, {'name': 'TJ', 'note': 'bar'})
        doc.body['note'] = 'foo'
        self.assertEqual(doc.body, {'name': 'TJ', 'note': 'foo'})
        self.assertFalse(doc.read_if_remote_newer())
        self.assertEqual(doc.body, {'name': 'TJ', 'note': 'foo'})
        self.assertTrue(doc.read())
        self.assertEqual(doc.body, {'name': 'TJ', 'note': 'bar'})

        self.assertTrue(doc.compare_and_delete())

        # Simple caching
        for i in range(2):
            doc = coll.document('tj')
            hit = doc.read()
            if hit:
                doc.compare_and_swap()
            else:
                doc.body = {'name': 'TJ', 'note': 'Pretty cool'}
                doc.create_or_overwrite()

            self.assertEqual(hit, i == 1)
            self.assertEqual(doc.body, {'name': 'TJ', 'note': 'Pretty cool'})

        coll.force_delete()
        self.assertTrue(db.force_delete())

    def test_weighted_random_cluster(self):
        cluster = WeightedRandomCluster(
            urls=['http://localhost:8529', 'http://localhost:8530', 'http://localhost:8531'],
            weights=[1, 2, 1]
        )
        self.assertIsNotNone(cluster)

    def test_weighted_random_cluster_envvar(self):
        cfg = env_config(
            cfg={
                'ARANGO_CLUSTER': (
                    'http://localhost:8529,http://localhost:8530,http://localhost:8531'
                ),
                'ARANGO_CLUSTER_STYLE': 'weighted-random',
                'ARANGO_CLUSTER_WEIGHTS': '1,2,1',
                'ARANGO_AUTH': 'basic',
                'ARANGO_AUTH_USERNAME': helper.TEST_USERNAME,
                'ARANGO_AUTH_PASSWORD': helper.TEST_PASSWORD
            }
        )
        self.assertIsNotNone(cfg)


if __name__ == '__main__':
    unittest.main()
