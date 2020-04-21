"""Describes authorization strategies and provides concrete implementations.
"""
from dataclasses import dataclass
import pytypeutils as tus
import base64


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
        _header (str): The header we send on each request
    """
    def __init__(self, username, password):
        tus.check(
            username=(username, str),
            password=(password, str)
        )
        self.username = username
        self.password = password
        self._header = 'Basic ' + base64.b64encode(
            (self.username + ':' + self.password).encode('ascii')
        ).decode('ascii')

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
        headers['Authorization'] = self._header


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
        self.delegate = delegate
        # TODO

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

    Attributes:
        lock_file (str): The path to the file to use for locking. Will be
            formatted as url-safe UUID followed by a space and then a
            float seconds since MS when the lock request occurred. An atomic
            append occurs and then we look back to verify we weren't beat to
            the lock. Depends on everyone using the lock file doing the same
            thing.
        lock_time_seconds (float): How long we respect locks for. If someone
            has held the lock for this long we consider it safe to steal.
        store_file (str): The path to the file used to store the actual JWT
            alongside some meta info. Stored in json.
    """
    def __init__(self, lock_file, lock_time_seconds, store_file):
        self.lock_file = lock_file
        self.lock_time_seconds = lock_time_seconds
        self.store_file = store_file

    # TODO


class JWTAuth(StatefulAuth):
    """Uses a username and password authentication to acquire a JWT which is
    used for future requests. A JWT can be more performant than basic auth.

    Attributes:
        username (str): The username to authenticate with
        password (str): The password to authenticate with
        cache (JWTCache, None): The mechanism for caching the token, or None
            to cache in memory only

        _token (JWTToken, None): The current token we are authenticating with,
            if we have a token.
    """
    def __init__(self, username, password, cache):
        """Initializes authorization to use the given cache in the future. Does
        not actually attempt to use the cache or initialize the token yet; that
        will be done on the next prepare or authorize.
        """
        self.username = username
        self.password = password
        self.cache = cache
        self._token = None

    def prepare(self):
        """If this has no token in memory it will attempt to acquire one (first
        through the cache and then through networking). If it has a token it
        will consider refreshing it."""
        pass

    def try_recover_auth_failure(self):
        """If this has an active token it will be cleared and this will return
        True. Otherwise this will return False."""
        pass

    def authorize(self, headers):
        """Will attempt to ensure an active token. If this cannot acquire a
        token, typically due to locking issues, an error will be raised.
        Otherwise, the 'Authentication' header will be set in the dict of
        headers to authenticate with the JWT"""
        pass

    def copy_and_strip_state(self):
        """Returns a new JWTAuth instance which is exactly how this one was
        constructed. This must be called if the process is forked or this is
        accessed in a different thread."""
        pass
