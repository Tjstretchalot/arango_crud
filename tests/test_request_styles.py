import unittest
import helper  # noqa: F401
from arango_crud import (  # noqa: E402
    RandomCluster,
    WeightedRandomCluster
)


class Test(unittest.TestCase):
    def test_random_cluster_single(self):
        cluster = RandomCluster(urls=['http://localhost:8529'])
        self.assertIsNotNone(cluster)

        url = cluster.select_next_url()
        self.assertEqual(url, 'http://localhost:8529')

    def test_random_cluster_multi(self):
        urls = ['http://localhost:8529', 'http://localhost:8530']
        cluster = RandomCluster(urls)

        seen = {}
        for i in range(100):
            url = cluster.select_next_url()
            self.assertIn(url, urls)
            seen[url] = True
            if len(seen) == 2:
                break

        self.assertEqual(len(seen), 2, seen)

    def test_weighted_random_cluster_single(self):
        cluster = WeightedRandomCluster(urls=['http://localhost:8529'], weights=[1])
        self.assertIsNotNone(cluster)

        url = cluster.select_next_url()
        self.assertEqual(url, 'http://localhost:8529')

    def test_weighted_random_cluster_multi(self):
        urls = ['http://localhost:8529', 'http://localhost:8530']
        cluster = WeightedRandomCluster(
            urls=urls,
            weights=[1, 2]
        )

        seen = {}
        for i in range(500):
            url = cluster.select_next_url()
            self.assertIn(url, urls)
            seen[url] = True
            if len(seen) == 2:
                break

        self.assertEqual(len(seen), 2, seen)


if __name__ == '__main__':
    unittest.main()
