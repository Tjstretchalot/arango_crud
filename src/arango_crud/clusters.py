"""Describes an object responsible for distributing requests to a cluster as
well as various common concrete implementations.
"""

class Cluster:
    pass


class WeightedRoundRobinCluster(Cluster):
    pass


class RoundRobinCluster(Cluster):
    """A special case of a weighted round robin cluster where all the weights
    are 1."""
    pass


class RandomCluster(Cluster):
    pass
