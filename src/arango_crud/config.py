"""Completely characterizes how communication with the ArangoDB coordinators
occurs. This is responsible for authenticating and initializing new Database
instances with a backwards reference to this configuration.
"""

class Config:
    """Describes how to connect to ArangoDB coordinators. Mainly responsible
    for authenticating requests and initiating Database instances.

    Attributes:
        cluster (Cluster): Decides which URL requests go to.
        back_off (BackOffStrategy): Decides what to do if a server or network
            error occurs.
        ttl_seconds (int, None): The number of seconds by default that objects
            live. If set to None TTL is disabled and collections are created
            without TTL indexes. TTL indexes are not modified after creation,
            so manual intervention is required to change this from None to
            not-None.
        auth (Auth): Sets authentication headers.
    """
    def __init__(self, cluster, back_off, ttl_seconds, auth):
        """Initializes Config by setting the corresponding attributes. For
        auth if it is a StatefulAuth it is wrapped with a StatefulAuthWrapper.
        """
        pass

    def database(self, name):
        """Fetch the Database object which acts as interface for using the
        ArangoDB database with the given name. This performs no networking.

        Arguments:
            name (str): The name of the database

        Returns:
            The Database object which provides an interface to the
            corresponding database on ArangoDB.
        """
        pass

    def prepare(self):
        """Performs any initial loading that is required on this configuration.
        If this is not called directly it will occur on the first request. This
        loads stateful information, typically JWTs, and hence uses locking
        mechanisms to maintain thread-safety.
        """
        pass
