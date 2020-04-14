"""Describes authorization strategies and provides concrete implementations.
"""
from dataclasses import dataclass


class Auth:
    """Describes something which is capable of setting the authentication
    headers.
    """
    def prepare(self):
        """A side-effectful call that sets the state up on this instance so
        that future requests can be served quickly. Not required to be called.
        Implementations which use this function should provide the option to
        use locking mechanisms to ensure thread and process safety.
        """
        raise NotImplementedError

    def try_recover_auth_failure(self):
        """This is called after the server rejects our authorization from this
        object. Should return True if this believes the problem has been
        resolved and False otherwise.

        Returns:
            True if authorization was refreshed and False otherwise
        """
        raise NotImplementedError

    def authorize(self, headers):
        """Adds the required authentication headers to the given dict of
        headers. This may require network requests if this is a stateful
        authorization (see prepare).

        Arguments:
            headers (dict): A possible empty dictionary of headers which will
                be passed to requests.
        """
        raise NotImplementedError


class BasicAuth(Auth):
    """A stateless basic authentication approach, where the username and
    password are sent along every request.

    Attributes:
        username (str): The username to authenticate with
        password (str): The password to authenticate with
    """
    def prepare(self):
        """Unused"""
        pass

    def try_recover_auth_failure(self):
        """There is no state in this object and hence auth failure is not
        recoverable

        Returns:
            False
        """
        return False

    def authorize(self, headers):
        """Uses the basic authentication strategy to set the Authorization
        header.
        """
        pass


class StatefulAuth(Auth):
    """An interface extension to auth to support deep-copying. This will
    allow a StatefulAuthWrapper to protect against multi-threading.
    """
    def copy_and_strip_state(self):
        """Returns a deep copy of this instance with all the state removed.
        For example, a JWT strategy would return a new instance with no JWT
        token initialized."""
        raise NotImplementedError


class StatefulAuthWrapper(Auth):
    """A concrete implementation of Auth which simply delegates to a stateful
    auth, except it will check if it's being used in a different thread or
    process than it was initialized in. If this happens the underlying auth
    is replaced with a new instance. This isn't perfect protection since
    process ids and thread ids are reused but without any purposeful
    serialization it's unlikely to fail.

    Attributes:
        delegate (StatefulAuth): The real underlying delegate instance
        pid (int): The PID of the process the delegate was initialized in
        tid (int): The TID of the current thread.
    """
    def __init__(self, delegate):
        pass

    def prepare(self):
        """Verify PID and TID then delegate"""
        pass

    def try_recover_auth_failure(self):
        """Verify PID and TID then delegate"""
        pass

    def authorize(self, headers):
        """Verify PID and TID then delegate"""
        pass


@dataclass
class JWTToken:
    """Describes a token and the expected expiration time"""
    token: str
    expires_at_utc_seconds: float


class JWTCache:
    """Describes an approach for storing a JWT token in a thread-safe and
    multi-processed-safe way. The more reuse of the token is possible for
    a given cache the better performance will tend to be on authorization.
    """
    def fetch(self):
        """Attempt to fetch the value from the cache.

        Returns:
            If the cache has a value, this is the JWTToken in the cache.
            Otherwise this is None.
        """
        raise NotImplementedError

    def try_acquire_lock(self):
        """Attempt to acquire permission to fetch a new token. This might
        happen a bit before the token expires so that one instance can
        refresh the token while the other instances are still using the
        old one.

        Returns:
            True if the lock was acquired, False otherwise
        """
        raise NotImplementedError

    def try_set(self, token):
        """Attempt to set the value in the cache to the given token. Only
        called if we successfully acquired the lock recently. This should only
        work if the lock is still held. Note that if we fail to set the JWT
        token in the cache it will still be used by our instance. Hence if
        this simply returns False it is effectively memory caching.

        Arguments:
            token (JWTToken): The token that should be set in the cache

        Returns:
            True if the cache was updated. Otherwise, when we lost access to
            the lock and hence did nothing, returns False.
        """
        raise NotImplementedError


class JWTDiskCache(JWTCache):
    """A disk-based JWT cache which will allow all processes or threads
    pointing at the same token and lock-file to share a JWT token. This is
    fairly simple and good enough for the great majority of use-cases.
    """
    pass


class JWTAuth(StatefulAuth):
    pass
