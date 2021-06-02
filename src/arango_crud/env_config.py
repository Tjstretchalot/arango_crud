"""This module mainly exposes the env_config() which builds a Config instance
using an ultra simple flat dictionary, which defaults to screaming snake case.
This provides reasonably informative error messages and warnings as well.
"""
from .config import Config
from .clusters import Cluster, RandomCluster, WeightedRandomCluster
from .back_off_strategies import BackOffStrategy, StepBackOffStrategy
from .auths import Auth, BasicAuth, JWTAuth, JWTDiskCache
from urllib.parse import urlparse
import warnings
import typing
import os


def env_config(cfg=None):
    """Loads an arango Config instance based on the given dictionary. If the
    dictionary is not provided, os.environ is used instead.

    Arguments:
        cfg (dict, None): Dictates how the cluster is setup. Has the following
            keys, formatted as if they were nested for ease of reading, but
            note that all parameters are top-level. If this is None then os.env
            is used in its place. For all values a blank string is treated as
            None.

            ARANGO_CLUSTER (str): A comma-separated list of URLs for
                coordinators in the cluster.

                ARANGO_CLUSTER_STYLE (str, None): A string as an enum or
                    None to take the value 'random'. Either 'random' or
                    'weighted-random'. Additional arguments by choice:

                    'random': No additional arguments. Requests are distributed
                        uniformly at random amongst coordinators.
                    'weighted-random':
                        ARANGO_CLUSTER_WEIGHTS (str): A comma-separated list
                            of floats. Should have one value per coordinator
                            URL. The url with the corresponding index will
                            receive requests proportional to their weight; so
                            if there are three urls and the weights are 1,2,1
                            the second URL receives 2x as many requests as URL
                            1 and 3, which only happens with the probability
                            distribution 25%, 50%, 25%.
            ARANGO_VERIFY (str, None): If specified should be a path to a
                certificate bundle to use to verify SSL certificates.
                Forwarded directly to requests using the verify keyword.
                See https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification
            ARANGO_TIMEOUT_SECONDS (str, None): A float base-10 expansion for
                the number of seconds before requests to ArangoDB are timed
                out. https://requests.readthedocs.io/en/master/user/quickstart/#timeouts
                Defaults to 3 but can often be reduced if ping time is low and
                coordinators are expected to never queue requests. Note that
                if the request takes arango more than this amount of time to
                process it will be impossible to get a result. Since this
                library is intended for a simple key/value ttl store this
                doesn't need to wait long to feel confident something is wrong,
                but if the values are huge or the cluster is overloaded this
                should be closer to 20 seconds as it takes longer to feel
                confident it's a connectivity issue.

            ARANGO_BACK_OFF (str, None): A string as an enum. Always 'step'.
                None is treated as 'step'. Additional arguments by choice:

                'step': Back-off occurs on a fixed schedule with a fixed upper
                    limit on the number of retries.

                    ARANGO_BACK_OFF_STEPS (str, None): A comma-separated list
                        of floats. If this has 1 value then there will be one
                        additional request after the first failure, and it will
                        occur after sleeping the value in seconds. Ex:
                        0.1,0.5,1 will go failure -> 0.1 second sleep ->
                        failure, 0.5 second sleep -> failure -> 1 second sleep
                        -> error if there are network connectivity issues.

                        Defaults to 0.1,0.5,1,1,1

            ARANGO_TTL_SECONDS (str, None): Either an integer in base-10 format
                for the time after which objects may be deleted arbitrarily if
                they are unused, or None/empty string for objects to never be
                automatically cleaned up. If a TTL is not set one must be very
                careful to not "leak" keys (i.e., if you set a key it must
                eventually be deleted as there will be no easy way to find it
                again). Once keys are leaked one is in linear time on all keys
                in the database to find them which is often painfully slow,
                very expensive, a lot of throwaway development time, or all 3.
                Note that a TTL means that ArangoDB cannot be used as the
                long-term source of truth, but arango_crud is not intended for
                ArangoDB to be used as a database.

            ARANGO_AUTH (str): A string as an enum. One of 'basic', 'jwt'.
                Always requires the following arguments:

                ARANGO_AUTH_USERNAME (str): The username to authenticate with.
                ARANGO_AUTH_PASSWORD (str, None): The password to authenticate
                    with; treats None as an empty string, which works better in
                    some shells when using environment variables.

                With the following additional arguments by choice:

                'basic': No additional arguments, uses basic authentication
                'jwt': Converts the username and password to a JWT for most
                    requests. The conversion to a JWT is usually a performance
                    gain, as long as the JWT is not generated frequently. See
                    the README "JWT Locking and Store" for details. 99% of the
                    time the best implemented choice is ARANGO_AUTH='jwt',
                    ARANGO_AUTH_CACHE='disk', and the remaining auth settings
                    on their default values. The most common thing to change
                    is where the files are if the application doesn't have
                    permission to modify the current working directory or the
                    current working directory is not consistent.

                    ARANGO_AUTH_CACHE (str): A string as enum. The cache style
                        to use for the JWT in a addition to storing it memory.
                        Must be one of 'disk', 'none' - 'none' is required to
                        be explicit since it's a bad choice in most production
                        environments and can lead to unpredictable load
                        spiking. Additional arguments by choice:

                        'none': JWT's are only reused if the same Config
                            instance is used for both calls. No additional
                            arguments.
                        'disk': JWT's are stored on disk, allowing all Config
                            instances which are initialized with the same file
                            to reuse the token. Safe for highly concurrent
                            environments and alleviates retry-hammering Arango
                            (network hiccup -> error -> instances restart ->
                            all of them request new JWTs at the same time,
                            causing Arango to hiccup -> repeat).

                            ARANGO_AUTH_CACHE_LOCK_FILE (str, None): A path to
                                a lock file which ensures multiple instances
                                running against the same JWT do not all acquire
                                or refresh at the same time. Defaults to
                                '.arango_jwt.lock'
                            ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS (str, None): A
                                base-10 expansion of an integer for the number
                                of seconds that a single instance may hold the
                                lock. An error will be raised if this is less
                                than ARANGO_TIMEOUT_SECONDS, and a warning will
                                be raised if this is less than
                                ARANGO_TIMEOUT_SECONDS + 1. If None, this is
                                ARANGO_TIMEOUT_SECONDS + 3.
                            ARANGO_AUTH_CACHE_STORE_FILE (str, None): The file
                                where the JWT and some metadata are stored.
                                Note this only needs to be accessed when
                                initializing, acquiring, or refreshing the JWT
                                which lasts 1 month. Defaults to '.arango_jwt'

            ARANGO_DISABLE_DATABASE_DELETE (str, None): Either the string
                'false' to allow database deletes using arango_crud, otherwise
                treated as True and will raise an AssertionError if a database
                delete is attempted via arango_crud

            ARANGO_PROTECTED_DATABASES (str, None): If
                ARANGO_DISABLE_DATABASE_DELETE is not 'false' this is ignored.
                Otherwise, this may be a comma separated list of database names
                which will cause an AssertionError if a database delete is
                attempted on them via arango_crud.

            ARANGO_DISABLE_COLLECTION_DELETE (str, None): Either the string
                'false' to allow database deletes using arango_crud, otherwise
                treated as True and will raise an AssertionError if a
                collection delete is attempted via arango_crud

            ARANGO_PROTECTED_COLLECTIONS (str, None): If
                ARANGO_DISABLE_COLLECTION_DELETE is not 'false' this is
                ignored. Otherwise, this may be a comma separated list of
                collection names which will cause an AssertionError if a
                collection delete is attempted on them in any database via
                arango_crud.

    Returns:
        An Arango Config instance initialized using the values in the config.
    """
    if cfg is None:
        cfg = os.environ

    cluster = env_cluster(cfg)
    verify = env_verify(cfg)
    timeout_seconds = env_timeout_seconds(cfg)
    back_off = env_back_off(cfg)
    ttl_seconds = env_ttl_seconds(cfg)
    auth = env_auth(cfg, timeout_seconds)
    disable_database_delete = env_disable_database_delete(cfg)
    protected_databases = env_protected_databases(cfg)
    disable_collection_delete = env_disable_collection_delete(cfg)
    protected_collections = env_protected_collections(cfg)

    return Config(
        cluster, timeout_seconds, back_off, ttl_seconds, auth,
        verify=verify,
        disable_database_delete=disable_database_delete,
        protected_databases=protected_databases,
        disable_collection_delete=disable_collection_delete,
        protected_collections=protected_collections
    )


def env_cluster(cfg) -> Cluster:
    """Parses a cluster from the given dictionary of string to string mappings.
    See "env_config" for details on how this is parsed."""
    urls_str = _get_with_error(
        cfg,
        'ARANGO_CLUSTER',
        'Expected a comma-separated list of urls for coordinators'
    )
    urls = urls_str.split(',')
    if not urls:
        raise ValueError(
            f'ARANGO_CLUSTER={urls_str} does not specify any urls'
        )

    for idx, url in enumerate(urls):
        try:
            urlparse(url)
        except ValueError:
            raise ValueError(
                f'ARANGO_CLUSTER={urls_str} should be a comma-separated list '
                + f'of urls. URL at index {idx} = {url} is malformed.'
            )

    style = cfg.get('ARANGO_CLUSTER_STYLE', 'random')
    if style == '':
        style = 'random'

    if style == 'random':
        return RandomCluster(urls)
    elif style == 'weighted-random':
        weights_str = _get_with_error(
            cfg,
            'ARANGO_CLUSTER_WEIGHTS',
            'Expected a comma-separated list of floats for coordinator weights'
        )
        weights_str_list = weights_str.split(',')
        if len(weights_str_list) != len(urls):
            raise ValueError(
                f'ARANGO_CLUSTER_WEIGHTS={weights_str} should have the same '
                + f'number of elements as ARANGO_CLUSTER={urls_str}. Got '
                + f'{len(weights_str_list)} weights and {len(urls)} '
                + 'coordinators.'
            )
        for idx, weight in enumerate(weights_str_list):
            try:
                float(weight)
            except ValueError:
                raise ValueError(
                    f'ARANGO_CLUSTER_WEIGHTS={weights_str} should be a comma-'
                    + f'separated list of floats, but index {idx} = {weight} '
                    + 'could not be interpreted as a float.'
                )

            if float(weight) < 0:
                raise ValueError(
                    f'ARANGO_CLUSTER_WEIGHTS={weights_str} at index {idx} is '
                    + 'negative. Should be positive.'
                )
        weights = [float(weight) for weight in weights_str_list]
        return WeightedRandomCluster(urls, weights)
    else:
        raise ValueError(
            f'ARANGO_CLUSTER_STYLE={style} is not a recognized style.'
        )


def env_verify(cfg) -> str:
    """Get the certfile to use for verifying the SSL certificate, if one
    is explicitly specified. Otherwise return None."""
    verify_str = cfg.get('ARANGO_VERIFY')
    if verify_str is None or verify_str == '':
        return None
    return verify_str


def env_timeout_seconds(cfg) -> int:
    """Get the number of seconds before timing out requests to the cluster.
    See env_config for details on how this is parsed"""
    timeout_seconds_str = cfg.get('ARANGO_TIMEOUT_SECONDS')
    if timeout_seconds_str is None or timeout_seconds_str == '':
        return 3

    try:
        timeout_seconds = int(timeout_seconds_str)
    except ValueError:
        raise ValueError(
            f'ARANGO_TIMEOUT_SECONDS={timeout_seconds_str} should be an int '
            + 'could not be interpreted as such.'
        )

    if timeout_seconds <= 0:
        raise ValueError(
            f'ARANGO_TIMEOUT_SECONDS={timeout_seconds_str} needs to be postive!'
        )

    return timeout_seconds


def env_back_off(cfg) -> BackOffStrategy:
    """Loads the back-off strategy from the given dict of strings to strings.
    See "env_config" for implementation details."""
    back_off = cfg.get('ARANGO_BACK_OFF')
    if back_off is None or back_off == '':
        back_off = 'step'

    if back_off == 'step':
        steps_str = cfg.get('ARANGO_BACK_OFF_STEPS')
        if steps_str is None or steps_str == '':
            steps_str = '0.1,0.5,1,1,1'

        steps_str_spl = steps_str.split(',')
        if not steps_str_spl:
            raise ValueError(
                f'ARANGO_BACK_OFF_STEPS={steps_str} must be a non-empty list '
                + 'of comma-separated floats!'
            )

        for idx, step in enumerate(steps_str_spl):
            try:
                float(step)
            except ValueError:
                raise ValueError(
                    f'ARANGO_BACK_OFF_STEPS={steps_str} should be a comma-'
                    + f'separated list of floats, but at index {idx} got '
                    + f'{step} which could not be interpreted as a float'
                )
            if float(step) < 0:
                raise ValueError(
                    f'ARANGO_BACK_OFF_STEPS={steps_str} at index {idx} is '
                    + 'negative, but every step must be non-negative!'
                )

        steps = [float(step) for step in steps_str_spl]
        return StepBackOffStrategy(steps)
    else:
        raise ValueError(
            f'ARANGO_BACK_OFF={back_off} should be \'step\''
        )


def env_ttl_seconds(cfg) -> int:
    """Loads the default time-to-live for all documents from the given str to
    str dict. See "env_config" for details."""
    ttl_str = cfg.get('ARANGO_TTL_SECONDS')
    if ttl_str is None or ttl_str == '':
        return None

    try:
        ttl = int(ttl_str)
    except ValueError:
        raise ValueError(
            f'Expected ARANGO_TTL_SECONDS={ttl_str} is an integer, but it could '
            + 'not be parsed as such.'
        )

    if ttl <= 0:
        raise ValueError(
            f'ARANGO_TTL_SECONDS={ttl_str} must be a positive integer!'
        )

    return ttl


def env_auth(cfg, timeout_seconds: int) -> Auth:
    """Get the mechanism for authorizing requests to the cluster. See
    "env_config" for details. Uses timeout_seconds for the default JWT
    lock time and for warnings related to the JWT lock time.
    """
    style = cfg.get('ARANGO_AUTH')
    if style is None or style == '':
        raise ValueError(
            'ARANGO_AUTH is missing but is required.'
        )

    username = cfg.get('ARANGO_AUTH_USERNAME')
    if username is None or username == '':
        raise ValueError(
            'ARANGO_AUTH_USERNAME is missing but is required.'
        )

    password = cfg.get('ARANGO_AUTH_PASSWORD', '')

    if style == 'basic':
        return BasicAuth(username, password)
    elif style == 'jwt':
        cache_str = cfg.get('ARANGO_AUTH_CACHE')
        if cache_str is None or cache_str == '':
            raise ValueError(
                'For JWT Auth, ARANGO_AUTH_CACHE is required. It is not set.'
            )

        if cache_str == 'none':
            cache = None
        elif cache_str == 'disk':
            min_lock_seconds = timeout_seconds
            min_no_warn_lock_seconds = timeout_seconds + 1
            def_lock_seconds = timeout_seconds + 3

            lock_file = cfg.get('ARANGO_AUTH_CACHE_LOCK_FILE')
            if lock_file is None or lock_file == '':
                lock_file = '.arango_jwt.lock'

            lock_seconds_str = cfg.get(
                'ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS', str(def_lock_seconds))
            try:
                lock_seconds = int(lock_seconds_str)
            except ValueError:
                raise ValueError(
                    f'ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS={lock_seconds_str} '
                    + 'should be an int but could not be interpreted as such.'
                )

            if lock_seconds < min_lock_seconds:
                raise ValueError(
                    f'ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS={lock_seconds_str} '
                    + 'is dangerously low for the given request timeout! '
                    + f'Should be at least {min_lock_seconds}'
                )

            if lock_seconds < min_no_warn_lock_seconds:
                warnings.warn(
                    f'ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS={lock_seconds_str} '
                    + 'is concerningly low for the given request timeout! '
                    + f'Recommended to be at least {min_lock_seconds} to '
                    + 'avoid false negatives.',
                    UserWarning
                )

            jwt_file = cfg.get('ARANGO_AUTH_CACHE_STORE_FILE')
            if jwt_file is None or jwt_file == '':
                jwt_file = '.arango_jwt'

            cache = JWTDiskCache(lock_file, lock_seconds, jwt_file)
        else:
            raise ValueError(
                f'ARANGO_AUTH_CACHE={cache_str} is not a recognized JWT token '
                + 'caching technique.'
            )

        return JWTAuth(username, password, cache)
    else:
        raise ValueError(
            f'ARANGO_AUTH={style} is not a recognized authorization scheme'
        )


def env_disable_database_delete(cfg) -> bool:
    """Determine if database delete convenience functions should be disabled.
    See "env_config" for details."""
    return cfg.get('ARANGO_DISABLE_DATABASE_DELETE') != 'false'


def env_protected_databases(cfg) -> typing.List[str]:
    """Determine what databases, if any, are protected even if database deletes
    are in general allowed. See "env_config" for details."""
    protected_str = cfg.get('ARANGO_PROTECTED_DATABASES')
    if protected_str is None or protected_str == '':
        return []

    return protected_str.split(',')


def env_disable_collection_delete(cfg) -> bool:
    """Determine if collection delete convenience functions should be disabled.
    See "env_config" for details."""
    return cfg.get('ARANGO_DISABLE_COLLECTION_DELETE') != 'false'


def env_protected_collections(cfg) -> typing.List[str]:
    """Determine what collections, if any, are protected even if collection
    deletes are in general allowed. See "env_config" for details."""
    protected_str = cfg.get('ARANGO_PROTECTED_COLLECTIONS')
    if protected_str is None or protected_str == '':
        return []

    return protected_str.split(',')


def _get_with_error(cfg, key, error):
    """Fetches key from cfg if it exists, otherwise raises an ValueError
    with the given message. Empty string or None both raise ValueError.

    Arguments:
        cfg (dict): The dictionary to load the value from
        key (str): The key to load from cfg
        error (str): The error message if key is not set.
    """
    val = cfg.get(key, '')
    if val == '':
        raise ValueError(f'missing environment variable {key}: {error}')
    return val
