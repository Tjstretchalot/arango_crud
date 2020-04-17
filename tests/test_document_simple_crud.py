import unittest
import sys
from . import helper

sys.path.append('src')

from arango_crud import (  # noqa: E402
    Config,
    RandomCluster,
    StepBackOffStrategy,
    BasicAuth
)


def create_config(ttl=60):
    return Config(
        cluster=RandomCluster(urls=helper.TEST_CLUSTER_URLS),
        timeout_seconds=10,
        back_off=StepBackOffStrategy(steps=[1]),
        ttl_seconds=ttl,
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

        self.assertIsNone(coll.read_doc('test_doc'))
        self.assertFalse(coll.touch_doc('test_doc'))
        self.assertFalse(coll.force_delete_doc('test_doc'))
        coll.create_or_overwrite_doc('test_doc', {'a': 'A'})
        self.assertEqual(coll.read_doc('test_doc'), {'a': 'A'})
        self.assertTrue(coll.touch_doc('test_doc'))
        self.assertTrue(coll.touch_doc('test_doc'), ttl=120)
        self.assertTrue(coll.force_delete_doc('test_doc'))

        self.assertTrue(db.force_delete())

    def test_touch_no_ttl(self):
        cfg = create_config(ttl=None)
        db = cfg.database(helper.TEST_ARANGO_DB)
        self.assertTrue(db.create_if_not_exists())

        coll = db.collection('test_coll')
        self.assertTrue(coll.create_if_not_exists())

        self.assertIsNone(coll.read_doc('test_doc'))
        self.assertFalse(coll.touch_doc('test_doc'))
        coll.create_or_overwrite_doc('test_doc', {'a': 'A'})
        self.assertFalse(coll.touch_doc('test_doc'))

        self.assertTrue(db.force_delete())


if __name__ == '__main__':
    unittest.main()
