"""Completely characterizes how communication with the ArangoDB coordinators
occurs. This is responsible for authenticating and initializing new Database
instances with a backwards reference to this configuration.
"""
from .auths import Auth, StatefulAuth, StatefulAuthWrapper
from .clusters import Cluster
from .back_off_strategies import BackOffStrategy
import pytypeutils as tus


class Config:
    """Describes how to connect to ArangoDB coordinators. Mainly responsible
    for authenticating requests and initiating Database instances.

    Attributes:
        cluster (Cluster): Decides which URL requests go to.
        timeout_seconds (float): The timeout for requests to the cluster,
            https://requests.readthedocs.io/en/master/user/quickstart/#timeouts
        back_off (BackOffStrategy): Decides what to do if a server or network
            error occurs.
        ttl_seconds (int, None): The number of seconds by default that objects
            live. If set to None TTL is disabled and collections are created
            without TTL indexes. TTL indexes are not modified after creation,
            so manual intervention is required to change this from None to
            not-None.
        auth (Auth): Sets authentication headers.
        verify (str, None): If specified, then requests should verify certs
            using the certificate bundle at this path. This is forwarded
            directly to requests.
        disable_database_delete (bool): True if database deletes are prevented,
            False if database deletes are allowed.
        protected_databases (list[str]): A list of database names which are
            prevented from deletion. Only has an effect if
            disable_database_delete is False.
        disable_collection_delete (bool): True if collection deletes are
            prevented, False if collection deletes are allowed.
        protected_collections (list[str]): A list collection names which are
            prevented from deletion. Only has an effect if
            disable_collection_delete is False.
    """
    def __init__(
            self, cluster, timeout_seconds, back_off, ttl_seconds, auth,
            verify=None, disable_database_delete=True, protected_databases=None,
            disable_collection_delete=True, protected_collections=None):
        """Initializes Config by setting the corresponding attributes. For
        auth if it is a StatefulAuth it is wrapped with a StatefulAuthWrapper.
        """
        if isinstance(auth, StatefulAuth):
            auth = StatefulAuthWrapper(auth)
        if protected_databases is None:
            protected_databases = []
        if protected_collections is None:
            protected_collections = []

        tus.check(
            cluster=(cluster, Cluster),
            timeout_seconds=(timeout_seconds, int),
            back_off=(back_off, BackOffStrategy),
            ttl_seconds=(ttl_seconds, (int, type(None))),
            auth=(auth, Auth),
            verify=(verify, (str, type(None))),
            disable_database_delete=(disable_database_delete, bool),
            protected_databases=(protected_databases, (list, tuple)),
            disable_collection_delete=(disable_collection_delete, bool),
            protected_collections=(protected_collections, (list, tuple))
        )
        tus.check_listlike(
            protected_databases=(protected_databases, str),
            protected_collections=(protected_collections, str)
        )

        self.cluster = cluster
        self.timeout_seconds = timeout_seconds
        self.back_off = back_off
        self.ttl_seconds = ttl_seconds
        self.auth = auth
        self.verify = verify
        self.disable_database_delete = disable_database_delete
        self.protected_databases = protected_databases
        self.disable_collection_delete = disable_collection_delete
        self.protected_collections = protected_collections

    def database(self, name):
        """Fetch the Database object which acts as interface for using the
        ArangoDB database with the given name. This performs no networking.

        Arguments:
            name (str): The name of the database

        Returns:
            The Database object which provides an interface to the
            corresponding database on ArangoDB.
        """
        from .database import Database

        return Database(self, name)

    def prepare(self):
        """Performs any initial loading that is required on this configuration.
        If this is not called directly it will occur on the first request. This
        loads stateful information, typically JWTs, and hence uses locking
        mechanisms to maintain thread-safety.
        """
        self.auth.prepare(self)

    def thread_safe_copy(self):
        """Returns a copy of this instance with local variables removed. This
        should be called whenever a config is suspected be used from a new
        thread. Note that this is not necessary when forking as that can be
        detected and handled due to copy-on-write semantics, but it won't
        hurt. Note that read-only references are still copied by reference."""
        if isinstance(self.auth, StatefulAuthWrapper):
            return Config(
                self.cluster,
                self.timeout_seconds,
                self.back_off,
                self.ttl_seconds,
                StatefulAuthWrapper(
                    self.auth.delegate.copy_and_strip_state()
                ),
                disable_database_delete=self.disable_database_delete,
                protected_databases=self.protected_databases,
                disable_collection_delete=self.disable_collection_delete,
                protected_collections=self.protected_collections
            )
        return self
