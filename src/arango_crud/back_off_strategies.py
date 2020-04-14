"""Describes an object that describes how to back-off if the cluster is having
issues and provides a concrete implementation."""

class BackOffStrategy:
    pass


class StepBackOffStrategy(BackOffStrategy):
    pass
