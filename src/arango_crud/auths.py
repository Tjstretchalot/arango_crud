"""Describes authorization strategies and provides concrete implementations.
"""
from dataclasses import dataclass
import pytypeutils as tus
import base64
import threading
import os
import json
import random
import math
import uuid
import time
from . import helper


class Auth:
    """Describes something which is capable of setting the authentication
    headers.
    """
    def prepare(self, config):
        """A side-effectful call that sets the state up on this instance so
        that future requests can be served quickly. Not required to be called.
        Implementations which use this function should provide the option to
        use locking mechanisms to ensure thread and process safety.

        @param [Config] config The configuration to use to make any requests
            if necessary
        """
        raise NotImplementedError  # pragma: no cover

    def try_recover_auth_failure(self):
        """This is called after the server rejects our authorization from this
        object. Should return True if this believes the problem has been
        resolved and False otherwise.

        Returns:
            True if authorization was refreshed and False otherwise
        """
        raise NotImplementedError  # pragma: no cover

    def authorize(self, headers, config):
        """Adds the required authentication headers to the given dict of
        headers. This may require network requests if this is a stateful
        authorization (see prepare).

        Arguments:
            headers (dict): A possible empty dictionary of headers which will
                be passed to requests.
            config (Config): The config to use for making any requests required
                to authorize
        """
        raise NotImplementedError  # pragma: no cover


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

    def prepare(self, config):
        """Unused"""
        pass

    def try_recover_auth_failure(self):
        """There is no state in this object and hence auth failure is not
        recoverable

        Returns:
            False
        """
        return False

    def authorize(self, headers, config):
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
        raise NotImplementedError  # pragma: no cover


class StatefulAuthWrapper(Auth):
    """A concrete implementation of Auth which simply delegates to a stateful
    auth, except it will check if it's being used in a different thread or
    process than it was initialized in. If being used in a different process
    this can safely clean out local state and act as if it's a fresh instance,
    since by nature of being in a different process we can't interfere with
    other processes by writing.

    On the other hand when we're being used within the same process but on a
    different thread this is only able to catch the situation and raise an
    error since it's the Config instance itself which needs to be replaced
    to no longer reference this auth. See Config#thread_safe_copy for how
    to do this.

    Attributes:
        delegate (StatefulAuth): The real underlying delegate instance
        pid (int, None): The PID of the process the delegate was initialized
            in, if it has been initialized already.
        tid (int, None): The TID of the thread the delegate was initialized in,
            if it has been initialized already.
    """
    def __init__(self, delegate):
        self.delegate = delegate.copy_and_strip_state()
        self.pid = None
        self.tid = None

    def prepare(self, config):
        """Verify PID and TID then delegate"""
        self._check_match_affinity()
        return self.delegate.prepare(config)

    def try_recover_auth_failure(self):
        """Verify PID and TID then delegate"""
        self._check_match_affinity()
        return self.delegate.try_recover_auth_failure()

    def authorize(self, headers, config):
        """Verify PID and TID then delegate"""
        self._check_match_affinity()
        return self.delegate.authorize(headers, config)

    def reset_affinity(self):
        """Resets the affinity on this instance, stripping state so it can't
        be harmful."""
        self.pid = None
        self.tid = None
        self.delegate = self.delegate.copy_and_strip_state()

    def _check_match_affinity(self):
        """Verifies that we are running in our preferred process and thread.
        If we are being run in the right process but the wrong thread we're
        in shared memory and the only sane thing to do is raise an error."""
        if self.pid is None:
            self.pid = os.getpid()
            self.tid = threading.get_ident()
            return

        if os.getpid() != self.pid:
            self.reset_affinity()
            return

        if threading.get_ident() != self.tid:
            raise RuntimeError(
                'This StatefulAuthWrapper verifies that it is not being used '
                + 'on different threads or different processes in order to ensure '
                + 'the authorization approach does not get corrupted. When running '
                + 'in multiple processes this can be handled automatically by this '
                + 'instance reinitializing state, as writing to our instance variables '
                + "won't be replicated across other processes. However, this detected "
                + f'it was being run on process {self.pid}, thread {self.tid} and is now '
                + f'being run on the same process but thread {threading.get_ident()}. '
                + 'This requires that the Config instance itself is replaced using '
                'Config#thread_safe_copy on the new thread'
            )


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
        raise NotImplementedError  # pragma: no cover

    def try_acquire_lock(self):
        """Attempt to acquire permission to fetch a new token. This might
        happen a bit before the token expires so that one instance can
        refresh the token while the other instances are still using the
        old one.

        Returns:
            True if the lock was acquired, False otherwise
        """
        raise NotImplementedError  # pragma: no cover

    def try_set(self, token):
        """Attempt to set the value in the cache to the given token. Only
        called if we successfully acquired the lock recently. Note that
        if we fail to set the JWT token in the cache it will still be used
        by our instance. Hence if this simply returns False it is effectively
        memory caching.

        Arguments:
            token (JWTToken): The token that should be set in the cache

        Returns:
            True if the cache was updated. Otherwise, when we lost access to
            the lock and hence did nothing, returns False.
        """
        raise NotImplementedError  # pragma: no cover


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

    def fetch(self):
        """See JWTCache#fetch"""
        try:
            with open(self.store_file, 'r') as fin:
                str_contents = fin.read()
        except FileNotFoundError:
            return None

        try:
            json_contents = json.loads(str_contents)
        except json.decoder.JSONDecodeError:
            # This is a common error if the file was being written to while
            # we were reading
            return None

        return JWTToken(
            token=json_contents['token'],
            expires_at_utc_seconds=json_contents['expires_at_utc_seconds']
        )

    def try_acquire_lock(self):
        """See JWTCache#try_acquire_lock. This is a pessimistic locking tool to
        avoid blowing up the size of the lock file too quickly"""
        try_lock_at = time.time()
        try:
            with open(self.lock_file, 'r') as fin:
                line_contents = fin.readlines()
        except FileNotFoundError:
            line_contents = None

        num_lines = 0
        if line_contents:
            num_lines = len(line_contents)
            str_last_line = line_contents[-1]
            if str_last_line.strip() != '':
                try:
                    arr_last_line = json.loads(str_last_line)
                except json.decoder.JSONDecodeError:
                    # They were still writing; this shouldn't happen since we're
                    # supposed to do atomic writes :/
                    import warnings
                    warnings.warn(
                        'JWTDiskCache lock file is corrupted. If this file is '
                        + 'not being manually modified then the OS is not '
                        + 'performing atomic writes which could lead to '
                        + 'irrecoverable desync due to write interleaving.',
                        UserWarning
                    )
                    return False

                locked_at = arr_last_line[1]
                if locked_at > try_lock_at - self.lock_time_seconds:
                    return False

        lock_uuid = str(uuid.uuid4())
        row = json.dumps([lock_uuid, try_lock_at]) + "\n"

        # There are no reasons I can think of, which are recoverable, for this
        # to fail.
        with open(self.lock_file, 'a') as fout:
            fout.write(row)

        # Now we try to find our line and see if we won the race. If we won,
        # we're going to be the line at index num_lines
        lock_acquired = None
        with open(self.lock_file, 'r') as fin:
            for idx, line in enumerate(fin):
                if idx < num_lines:
                    continue

                try:
                    json.loads(line)
                except json.decoder.JSONDecodeError:
                    raise Exception(
                        'OS is not performing atomic small disk writes, '
                        + 'causing interleaving in the lock-file. This cannot '
                        + ' be automatically recovered.'
                    )

                lock_acquired = line == row
                break

        if lock_acquired is None:
            # If we got here the lock file was deleted between our write and our
            # read.
            return False

        if lock_acquired:
            if num_lines > 10_000:
                # We're going to overwrite the file. This is effectively going
                # to give up our lock for a tiny tiny period of time, so we
                # have to repeat this process. Luckily with only one line it's
                # a simpler process
                with os.open(self.lock_file, 'w') as fout:
                    fout.write(row)

                with os.open(self.lock_file) as fin:
                    first_row = fin.readline()

                if first_row != row:
                    return False

        return lock_acquired

    def try_set(self, token: JWTToken):
        """See JWTCache#try_set. This cannot fail, assuming that the os
        performs atomic writes for very small files which are only flushed
        when closed. This also cannot fail if we still hold the lock. So
        it would require a cacophony of errors to fail. Furthermore, if it
        does fail almost certainly it will not lead to parsable json, hence
        fetch will automatically recover. If it somehow errored every time,
        we degrade to memory caching"""
        dict_contents = {
            'token': token.token,
            'expires_at_utc_seconds': token.expires_at_utc_seconds
        }
        json_contents = json.dumps(dict_contents)
        with open(self.store_file, 'w') as fout:
            fout.write(json_contents)
        return True


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
        _forcing_refresh (str, None): Only set if we have a particular JWT token
            which we are not satisfied with. Otherwise, None.
    """
    def __init__(self, username, password, cache):
        """Initializes authorization to use the given cache in the future. Does
        not actually attempt to use the cache or initialize the token yet; that
        will be done on the next prepare or authorize.
        """
        tus.check(
            username=(username, str),
            password=(password, (str, type(None))),
            cache=(cache, (JWTCache, type(None)))
        )
        self.username = username
        self.password = password if password is not None else ''
        self.cache = cache
        self._token = None
        self._forcing_refresh = None

    def prepare(self, config):
        """If this has no token in memory it will attempt to acquire one (first
        through the cache and then through networking). If it has a token it
        will consider refreshing it."""
        if self._token is None:
            self.try_load_or_refresh_token(config)

        if self._token.expires_at_utc_seconds < time.time() + 60:
            self.force_refresh_token(config)
            return

        target_refresh_at = -250_000 * math.log(random.random())
        if self._token.expires_at_utc_seconds < time.time() + target_refresh_at:
            self.try_refresh_token(config)
            return

    def try_recover_auth_failure(self):
        """If this has an active token it will be cleared and this will return
        True. Otherwise this will return False."""
        if self._token is not None:
            self._forcing_refresh = self._token.token
            self._token = None
            return True
        return False

    def authorize(self, headers, config):
        """Will attempt to ensure an active token. If this cannot acquire a
        token, typically due to locking issues, an error will be raised.
        Otherwise, the 'Authorization' header will be set in the dict of
        headers to authenticate with the JWT"""
        self.prepare(config)
        if self._token is not None:
            # If the token is None we want them to fail the request and
            # see that we can't recover in try_recover_auth_failure
            headers['Authorization'] = f'Bearer {self._token.token}'

    def copy_and_strip_state(self):
        """Returns a new JWTAuth instance which is exactly how this one was
        constructed. This must be called if the process is forked or this is
        accessed in a different thread."""
        return JWTAuth(self.username, self.password, self.cache)

    def try_load_or_refresh_token(self, config):
        """Attempt to load the token from catch or fetch it from a network
        request. This may wait a while."""
        if self.cache is None:
            self._token = self.create_jwt_token(config)
            return

        for i in range(math.ceil(self.cache.lock_time_seconds / 10.0)):
            self._token = self.cache.fetch()
            if self._token is not None and self._forcing_refresh != self._token.token:
                return
            self._token = None
            if self.cache.try_acquire_lock():
                break
            time.sleep(0.1)

        token = self.create_jwt_token(config)
        self.cache.try_set(token)
        self._token = token
        self._forcing_refresh = None

    def try_refresh_token(self, config):
        """Attempts to refresh the token. This will do nothing if we fail to
        acquire the lock."""
        if self.cache is None:
            self._token = self.create_jwt_token(config)
            return

        if not self.cache.try_acquire_lock():
            return

        token = self.create_jwt_token(config)
        self.cache.try_set(token)
        self._token = token

    def force_refresh_token(self, config):
        if self.cache is None:
            self._token = self.create_jwt_token(config)
            return

        acquired_lock = self.cache.try_acquire_lock()
        token = self.create_jwt_token(config)
        if acquired_lock:
            self.cache.try_set(token)

        self._token = token

    def create_jwt_token(self, config) -> JWTToken:
        """Create a new token through a network request to ArangoDB
        """
        resp = helper.http_post(
            config,
            '/_open/auth',
            add_authorization=False,
            json={
                'username': self.username,
                'password': self.password
            }
        )
        resp.raise_for_status()
        token = resp.json()['jwt']
        expected_expire_time = time.time() + 60 * 60 * 24 * 30

        return JWTToken(
            token=token,
            expires_at_utc_seconds=expected_expire_time
        )
