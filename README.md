# arango_crud

This respository wraps the basic CRUD operations on ArangoDB for practical use.
This is not an official library; the official python library is
[pyArango](https://github.com/ArangoDB-Community/pyArango). The main reason to
use this over just [requests](https://requests.readthedocs.io/en/master/) is
authorization and server failure back-off. The main reason to use this over
pyArango is thread-safety, simpler interfaces, a more narrow focus, pep8
naming conventions, and complete support for either environment variable
configuration or code-as-configuration.

The main reason to use pyArango over arango_crud is field validation and access
to AQL. If you want to use ArangoDB as a database, use pyArango or similar. If
you want to use ArangoDB as a disk-based cache, use arango_crud or similar.

***Note***: This package recommends a time-to-live semantic. The TTL may be
set to "-1" in environment variables to be disabled, or "None" in code to be
disabled. A TTL index is only created when collections are initialized, so if
this library is used with TTL disabled and then TTL is enabled, one must
manually add the TTL indexes. Besides standard TTL usages, using a TTL means
that if there was a bug that leaked keys which was since patched, those keys
won't stay around forever. Furthermore, it means a small amount of key leakage,
such as through extremely unlikely race conditions which would be expensive
in either performance or developer time to fix, is not harmful to the long-term
health of the project.
https://www.arangodb.com/arangodb-training-center/ttl-indexes/

***Note***: This is not intended to provide much configurability for creating
databases or collections, providing only sane defaults for this particular
use-case. It's recommended to use a migration structure where databases and
collections are only initialized once and to call the appropriate HTTP endpoint
directly: https://www.arangodb.com/docs/stable/http/collection-creating.html

## Usage

### Installation

Supports python 3.7 or higher.

`pip install arango_crud`

### Initialize

#### Code-as-configuration BasicAuth

```py
from arango_crud import (
    Config, BasicAuth, RandomCluster, StepBackOffStrategy
)

config = Config(
    cluster=RandomCluster(),  # see Cluster Styles
    timeout_seconds=3,
    back_off=StepBackOffStrategy([0.1, 0.5, 1, 1, 1]),  # see Back Off Strategies
    auth=BasicAuth(username='root', password=''),
    ttl_seconds=31622400
)
```

#### Code-as-configuration JWT

```py
from arango_crud import (
    Config, JWTAuth, JWTDiskCache, RandomCluster, StepBackOffStrategy
)

config = Config(
    cluster=RandomCluster(urls=['http://localhost:8529']),
    timeout_seconds=3,
    back_off=StepBackOffStrategy(steps=[0.1, 0.5, 1, 1, 1]),
    ttl_seconds=31622400,
    auth=JWTAuth(
        username='root',
        password='',
        cache=JWTDiskCache(  # See JWT Caches
            lock_file='.arango_jwt.lock',
            lock_time_seconds=10,
            store_file='.arango_jwt'
        )
    )
)

# encouraged for easier performance tracing, not required. happens on first
# request otherwise. Fetches the JWT token if it does not exist.
config.prepare()
```

#### Environment variables BasicAuth

test.py
```py
from arango_crud import env_config

config = env_config()
config.prepare() # recommended, not required
```

run.sh
```sh
#!/usr/bin/env bash
# Cluster urls are separated by a comma
export ARANGO_CLUSTER=http://localhost:8529
export ARANGO_CLUSTER_STYLE=random
export ARANGO_TIMEOUT_SECONDS=3
export ARANGO_BACK_OFF=step
export ARANGO_BACK_OFF_STEPS=0.1,0.5,1,1,1
export ARANGO_TTL_SECONDS=31622400
export ARANGO_AUTH=basic
export ARANGO_AUTH_USERNAME=root
export ARANGO_AUTH_PASSWORD=
python test.py
```

#### Environment variables JWT

test.py
```py
from arango_crud import env_config

config = env_config()
```

run.sh
```sh
#!/usr/bin/env bash
# Cluster urls are separated by a comma
export ARANGO_CLUSTER=http://localhost:8529
export ARANGO_CLUSTER_STYLE=random
export ARANGO_TIMEOUT_SECONDS=3
export ARANGO_BACK_OFF=step
export ARANGO_BACK_OFF_STEPS=0.1,0.5,1,1,1
export ARANGO_TTL_SECONDS=31622400
export ARANGO_AUTH=jwt
export ARANGO_AUTH_USERNAME=root
export ARANGO_AUTH_PASSWORD=
export ARANGO_AUTH_CACHE=disk
export ARANGO_AUTH_CACHE_LOCK_FILE=.arango_jwt.lock
export ARANGO_AUTH_CACHE_LOCK_TIME_SECONDS=10
export ARANGO_AUTH_CACHE_STORE_FILE=.arango_jwt
python test.py
```


### CRUD

To make these runnable environment variables must be set and ArangoDB
needs to be reachable. Here are the configurations for ArangoDB running
locally on default development settings:

Windows:
```bat
SET ARANGO_CLUSTER=http://localhost:8529
SET ARANGO_CLUSTER_STYLE=random
SET ARANGO_TIMEOUT_SECONDS=3
SET ARANGO_BACK_OFF=step
SET ARANGO_BACK_OFF_STEPS=0.1,0.5,1,1,1
SET ARANGO_TTL_SECONDS=31622400
SET ARANGO_AUTH=basic
SET ARANGO_AUTH_USERNAME=root
SET ARANGO_AUTH_PASSWORD=
```

*Nix:
```sh
#!/usr/bin/env bash
export ARANGO_CLUSTER=http://localhost:8529
export ARANGO_CLUSTER_STYLE=random
export ARANGO_TIMEOUT_SECONDS=3
export ARANGO_BACK_OFF=step
export ARANGO_BACK_OFF_STEPS=0.1,0.5,1,1,1
export ARANGO_TTL_SECONDS=31622400
export ARANGO_AUTH=basic
export ARANGO_AUTH_USERNAME=root
export ARANGO_AUTH_PASSWORD=
```

```py
from arango_crud import env_config
import time

config = env_config()
config.prepare()

db = config.database('my_db')
db.create_if_not_exists()
coll = db.collection('users')
coll.create_if_not_exists()

# The simplest interface
coll.create_or_overwrite_doc('tj', {'name': 'TJ'})
coll.read_doc('tj') # {'name': 'TJ'}
coll.force_delete_doc('tj') # True

# non-expiring
coll.create_or_overwrite_doc('tj', {'name': 'TJ'}, ttl=None)
coll.force_delete_doc('tj')

# custom expirations with touching. Note that touching a document is not
# a supported atomic operation on ArangoDB and is hence faked with
# read -> compare_and_swap. Presumably if the CAS fails the document was
# touched recently anyway.
coll.create_or_overwrite_doc('tj', {'name': 'TJ'}, ttl=30) # True
coll.touch_doc('tj', ttl=60) # True

# Alternative interface. For anything except one-liners, usually nicer.
doc = coll.document('tj')
doc.body['name'] = 'TJ'
doc.create() # True
doc.body['note'] = 'Pretty cool'
doc.compare_and_swap() # True

# We may use etags to avoid redownloading an unchanged document, but be careful
# if you are modifying the body.

# Happy case:
doc2 = coll.document('tj')
doc2.read() # loads {'name': 'TJ', 'note': 'Pretty cool'} from network

doc.read_if_remote_newer() # 304 not modified, returns False
doc2.read_if_remote_newer() # 304 not modified, returns False

doc.body['note'] = 'bar'
doc.compare_and_swap()
doc.read_if_remote_newer() # 304 not modified, returns False
doc2.read_if_remote_newer() # loads {'name': 'TJ', 'note': 'bar'} from network, returns True

# Where it can get dangerous
doc.body['note'] = 'foo'
print(doc.body) # {'name': 'TJ', 'note': 'foo'}
doc.read() # always a complete download
print(doc.body) # {'name': 'TJ', 'note': 'bar'}
doc.read_if_remote_newer() # no changes on server since last read; 304 not modified, returns False
print(doc.body) # {'name': 'TJ', 'note': 'bar'}
doc.body['note'] = 'foo'
print(doc.body) # {'name': 'TJ', 'note': 'foo'}
doc.read_if_remote_newer() # no changes on server since last read; 304 not modified, returns False
print(doc.body) # {'name': 'TJ', 'note': 'foo'}
doc.read()
print(doc.body) # {'name': 'TJ', 'note': 'bar'}

doc.compare_and_delete() # True


# Simple caching
for i in range(2):
    doc = coll.document('tj')
    hit = doc.read()
    if hit:
        doc.compare_and_swap() # refreshes TTL, usefulness depends
    else:
        # .... expensive computation ....
        doc.body = {'name': 'TJ', 'note': 'Pretty cool'}
        doc.create_or_overwrite()

    print(f'cached value (loop {i + 1}/2) (hit: {hit}): {doc.body}')
```

The following is in a separate code-block and is commented out to prevent
accidentally copy+paste into somewhere it should not be pasted. When running
tests it's helpful to cleanup the collections and databases afterward. It's
encouraged that if you do not need to delete collections and databases on
production these operations are disabled to help prevent developer error, which
is done by setting `ARANGO_DISABLE_DATABASE_DELETE` and
`ARANGO_DISABLE_COLLECTION_DELETE` to `true` These environment variables are
treated as `true` unless explicitly set to `false`. This is not a substitute
for good backups and should not be considered a security feature.

```py
# coll.force_delete()
# db.force_delete()
```

## Contributing

This package adheres to pep8 guidelines unless an exception is listed in
`.flake8`. Comments are explicitly line-broken at 80 characters. Code
complexity measures (AbcComplexity, etc) are not used. This measures code
coverage and a build of below 70% code coverage is considered failing. Note
that the word "unit test" is avoided - if it's possible to test a line of
code without mocking or accessing private variables that is preferred. PRs
which reduce code coverage must include an explanation of why.

The examples directory should not contain non-functional lines of code, so
instead of

```py
bar = foo()
if bar is None:
    print('Foo gave none!') # prints Foo
else:
    print('Something went wrong!')
```

it should be the easier to read assert variant, which plays friendlier with
automated testing that the examples actually work:

```py
bar = foo()
assert bar is None
```

Hence any PR where the coverage in the examples directory is less than 100%
when running `coverage run --source=examples examples/run_all.py` will have
changes requested.

This repository is focused specifically on using ArangoDB as a disk-based
cache. Functionality which doesn't support that use-case will have their PR
closed with the recommendation that they fork. So AQL or graph support would
likely be closed, but (bulk) get/set operations or concurrency-safe patches
will likely be merged.

Inheritance is to be avoided, preferring delegation which respects contracts.
Interfaces are not included in this, where an interface is a class where all
the functions simply raise `NotImplementedError` and there is no constructor.

### Setup Development (Windows)

[Install ArangoDB](https://www.arangodb.com/download-major/) on default
development settings.

```bat
python -m venv venv
python -m pip install --upgrade pip
"venv/Scripts/activate.bat"
python -m pip install -r dev_requirements.txt
"scripts/windows_dev_env.bat"
coverage run --source=src -m unittest discover -s tests
coverage report
coverage run --source=examples examples/run_all.py
coverage report
```

### Setup Development (*Nix)

```bash
docker pull arangodb/arangodb
docker run -e ARANGO_NO_AUTH=1 -p 8529/tcp arangodb/arangodb arangod --server-endpoint tcp://0.0.0.0:8529
python -m venv venv
python -m pip install --upgrade pip
. venv/bin/activate
. scripts/nix_dev_env.sh
python -m pip install -r dev_requirements.txt
coverage run --source=src -m unittest discover -s tests
coverage report
coverage run --source=examples examples/run_all.py
coverage report
```

## Cluster Styles

When working with an ArangoDB cluster, it's important that the clients
distribute their requests amongst the various coordinators. The request
styles supported are `random` and `weighted-random`. Round-robin and
similar are avoided as they cannot be made thread-safe and performant
without context.

### Random

A random url is selected from the cluster for each request with equal
probability among all urls.

### Weighted Random

A random node in the cluster is selected on each request, except there may be
a different probability for different urls. This is useful if, for example,
one of the coordinators is running on a larger server than the rest.

Example:

```py
from arango_crud import WeightedRandomCluster

cluster = WeightedRandomCluster(
    urls=['http://localhost:8529', 'http://localhost:8530', 'http://localhost:8531'],
    weights=[1, 2, 1]
)
```

This will select port 8529 1/4 of the time, 8530 1/2 of the time, and 8531 1/4
of the time. If one prefers to set the exact percentages just ensure the
weights sum to one (i.e., `0.25, 0.5, 0.25`)

Example environment variables:

```sh
#!/usr/bin/env bash
export ARANGO_CLUSTER=http://localhost:8529,http://localhost:8530,http://localhost:8531
export ARANGO_CLUSTER_STYLE=weighted-random
export ARANGO_CLUSTER_WEIGHTS=1,2,1
```

## Alternatives to Environment Variables

Although environment variables are sometimes extremely convenient, they can
also be painful in other development environments. One can painlessly switch
these out for their preferred storage mechanism since `env_config` accepts
a dictionary which it uses to load variables from. Note that `env_config`
will exclusively use that dictionary - it will not fall back and use an
environment variable if something is missing.

The only caveat is that for simplicity of development and to reuse the same
documentation, the keys need to be screaming snake case and it will not
make use of nesting. If one prefers they can massage the data into this format
after loading to get more conventional looking configuration files. One can
also simply massage the data into the arguments for `Config` directly.

arango_config.json
```json
{
    "ARANGO_CLUSTER": "http://localhost:8529,http://localhost:8530,http://localhost:8531",
    "ARANGO_CLUSTER_STYLE": "weighted-random",
    "__comment": "... see src/arango_crud/env_config.py for complete argument docs ..."
}
```

Which allows loading as follows:

```py
from arango_crud import env_config
import json

with open('arango_config.json') as fin:
    cfg = json.load(fin)

arango_config = env_config(cfg)
```


## Server Failures

When a request fails due to a server-side issue it's usually desirable to try
again on a new coordinator. A small sleep is also helpful to avoid suddenly
massively spiking traffic to the coordinators whenever they hiccup. This
supports only a `step-back-off` policy. If the steps are `[0.1, 0.5, 1]` then
on the first server error this waits 0.1 seconds then tries again. If that
also fails this waits 0.5 seconds then tries again. If that fails this waits
1 second then tries again. If that fails, an error is raised.

## JWT Locking and Store

It's usually not a good idea to create a lot of new tokens when a client is
misbehaving, as token generation is generally meant to be expensive in order to
be secure. Hence JWT is necessarily stateful on the Config - rather than just
being able to create network requests we first need to fetch the JWT.
Furthermore, we may need to refresh the token on arbitrary requests.

The recommended way to handle JWT's cache is `JWTDiskCache`. A file will contain
the JWT and some metadata about it, which will be accessed in a safe way for
even highly concurrent environments, meaning that every instance running
arango_crud on the same machine using the same config will share JWT tokens
and will only create/renew the token once per renewal period. This overhead is
extremely minor for non-concurrent environments.

If you're very confident that JWT generation is not going to be a significant
source of load and there is no multithreading, a naive approach can be enabled
with the cache style `None`. See the examples jwt_disk_example.py and
jwt_none_example.py
