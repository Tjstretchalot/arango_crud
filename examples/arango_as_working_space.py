"""This shows a use-case for this library for performing computations on
an underlying set of data which is too big to fit in memory. If ArangoDB
is used it can scale to as much disk space as ArangoDB has available while
still taking advantage of memory caching on the ArangoDB cluster.

This performs an array sort without ever filling more than a certain amount
in this instances memory. The suggested numbers are small so the example
completes quickly but is trivially configurable. It should work even when
the list is many billions of numbers. Notice how in the default configuration
the sorter may only view 0.1% of the underlying data array at once.
"""

NUM_FLOATS_IN_DATA_ARRAY = 10_000_000
NUM_FLOATS_IN_SORTER_MEMORY = 10_000

def main():
    pass
