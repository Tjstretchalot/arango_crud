"""This module mainly exposes the env_config() which builds a Config instance
using an ultra simple flat dictionary, which defaults to screaming snake case.
This provides reasonably informative error messages and warnings as well.
"""

def env_config(cfg=None):
    """Loads an arango Config instance based on the given dictionary. If the
    dictionary is not provided, os.env is used instead.

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

            ARANGO_BACK_OFF (str): A string as an enum. Always 'step'.
                Additional arguments by choice:

                'step': Back-off occurs on a fixed schedule with a fixed upper
                    limit on the number of retries.

                    ARANGO_BACK_OFF_STEPS (str): A comma-separated list of
                        floats. If this has 1 value then there will be one
                        additional request after the first failure, and it will
                        occur after sleeping the value in seconds. Ex:
                        0.1,0.5,1 will go failure -> 0.1 second sleep ->
                        failure, 0.5 second sleep -> failure -> 1 second sleep
                        -> error if there are network connectivity issues.

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
                            instance is used for both calls. No additonal
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

    Returns:
        An Arango Config instance initialized using the values in the config.
    """
    print('foo')
