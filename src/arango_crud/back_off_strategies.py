"""Describes an object that describes how to back-off if the cluster is having
issues and provides a concrete implementation."""
import pytypeutils as tus


class BackOffStrategy:
    """Describes the interface for backing off from a cluster. These instances
    must be stateless or detect multi-threading / forking"""
    def get_back_off(self, num_failed_requests):
        """Returns how much to back off from the server if we have failed the
        given number of requests due to server or network issues so far for
        this request.

        Returns:
            Either a float which is the number of seconds to sleep before
            attempting the request again or None to raise an error.
        """
        raise NotImplementedError  # pragma: no cover


class StepBackOffStrategy(BackOffStrategy):
    """Describes an extremely easy to understand approach - a direct mapping
    between the number of failed requests and a time to sleep. Once we exhaust
    the mapping we return None, which raises an error.

    Attributes:
        steps (list[float]): At index 0 is the back-off for 1 failed request,
            etc. If this has 2 elements, there will be 3 retries.
    """
    def __init__(self, steps):
        tus.check(steps=(steps, (list, tuple)))
        tus.check_listlike(steps=(steps, (int, float)))
        self.steps = [float(step) for step in steps]

    def get_back_off(self, num_failed_requests):
        tus.check(num_failed_requests=(num_failed_requests, int))
        if num_failed_requests <= 0:
            raise ValueError('Backoff only makes sense after failed requests!')
        if num_failed_requests <= len(self.steps):
            return self.steps[num_failed_requests - 1]
        return None
