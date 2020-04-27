"""Describes an object responsible for distributing requests to a cluster as
well as various common concrete implementations.
"""
import pytypeutils as tus
import random


class Cluster:
    """Describes the interface for a cluster. This is something which is
    capable of selecting a URL to direct requests to. Cluster instances
    should be stateless."""
    def select_next_url(self):
        """Returns the URL to a coordinator in the cluster which the next
        request will be sent to.

        Returns:
            The str url to a coordinator not suffixed with a slash. For
            example: http://localhost:5289
        """
        raise NotImplementedError  # pragma: no cover


class WeightedRandomCluster(Cluster):
    """Describes a cluster where requests are distributed at random according
    to the given set of probabilities.

    Attributes:
        urls (list[str]): A list of urls for coordinators within the cluster
        weights (list[float]): A list of positive floats that corresponds to
            the weight of the corresponding index in urls. If url A and B are
            such that A has 2x the weight of B, A will receive 2x the requests
            of B.
        _rolling_sum_weights (list[float]): The rolling sums of weights. If
            weights are 1, 2, 3 then this is 1, 3, 6
    """
    def __init__(self, urls, weights):
        tus.check(urls=(urls, (list, tuple)), weights=(weights, (list, tuple)))
        tus.check_listlike(urls=(urls, str), weights=(weights, (int, float)))

        self.urls = urls
        self.weights = [float(w) for w in weights]
        self._rolling_sum_weights = []

        _sum = 0.0
        for weight in self.weights:
            _sum += weight
            self._rolling_sum_weights.append(_sum)

    def select_next_url(self):
        choice = random.random() * self._rolling_sum_weights[-1]
        return next(
            self.urls[idx]
            for (idx, roll_sum) in enumerate(self._rolling_sum_weights)
            if roll_sum >= choice
        )


class RandomCluster(Cluster):
    """A special case of a weighted random cluster where all the urls have the
    same weight. Distributes requests uniformly at random to coordinators in
    the cluster.

    Attributes:
        urls (list[str]): A list of urls for coordinators within the cluster
    """
    def __init__(self, urls):
        tus.check(urls=(urls, (list, tuple)))
        tus.check_listlike(urls=(urls, str))
        if not urls:
            raise ValueError('need at least one URL')
        self.urls = urls

    def select_next_url(self):
        idx = random.randrange(len(self.urls))
        return self.urls[idx]
