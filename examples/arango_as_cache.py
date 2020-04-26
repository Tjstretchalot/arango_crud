"""This shows an easy example of using ArangoDB as a cache for a triangle
numbers function., T(0) = 0, T(n) = n + T(n - 1). The triangle numbers are
similar to the factorial numbers for examples except the numbers don't get
so large so quickly.

This is obviously not a particularly good function to cache naively since
an iterative solution could calculate a very large number of these before
it's slower than the network IO, but it's a familiar example.
"""
from arango_crud import env_config


def main():
    cfg = env_config()
    cfg.disable_collection_delete = False
    db = cfg.database('arango_crud_examples')
    coll = db.collection('arango_as_cache')

    db.create_if_not_exists()
    coll.create_if_not_exists()

    def triangle(n):
        if n == 0:
            return 1

        doc = coll.document(str(n))
        if not doc.read():
            doc.body['value'] = n + triangle(n - 1)
            assert doc.create() is True
        return doc.body['value']

    print('Calculating triangle(19):')
    print(triangle(19))

    print('Calculating triangle(20):')
    print(triangle(20))

    assert coll.force_delete() is True
