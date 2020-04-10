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

***Note***: All the examples in this package assume TTL is being used to cleanup
keys eventually. The TTL may be set to "-1" in environment variables to be
disabled, or "None" in code to be disabled. In this case some other solution for
cleaning up old keys is required.
https://www.arangodb.com/arangodb-training-center/ttl-indexes/

## Usage

### Installation

Supports python 3.7 or higher.

`pip install arango_crud`

### Initialize

#### Code-as-configuration BasicAuth

```py
from arango_crud import Config, BasicAuth

config = Config(
    cluster=['http://localhost:8529'],
    ttl_seconds=31622400,
    request_distribution='round-robin', # see Request Styles
    auth=BasicAuth(username='root', password=''),
    server_failures={ # see Server Failures
        'strategy': 'step-back-off',
        'steps': [0.1, 0.5, 1, 1, 1]
    }
)
```

#### Code-as-configuration JWT

```py
from arango_crud import Config, JWTAuth

config = Config(
    cluster=['http://localhost:8529'],
    ttl_seconds=31622400,
    request_style='round-robin', # see Request Styles
    auth=JWTAuth(
        username='root',
        password='',
        lock_style='disk', # See JWT Locking and Store for remaining
        lock_file='.arango_jwt.lock',
        lock_time_seconds=10,
        store_style='disk',
        store_file='.arango_jwt'
    ),
    server_failures={ # see Server Failures
        'strategy': 'step-back-off',
        'steps': [0.1, 0.5, 1, 1, 1]
    }
)

# encouraged for easier performance tracing, not required. happens on first
# request otherwise
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
export ARANGO_TTL_SECONDS=31622400
export ARANGO_REQUEST_STYLE=round-robin
export ARANGO_AUTH=basic
export ARANGO_USERNAME=root
export ARANGO_PASSWORD=
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
export ARANGO_TTL_SECONDS=31622400
export ARANGO_REQUEST_STYLE=round-robin
export ARANGO_AUTH=jwt
export ARANGO_AUTH_LOCK=mutex
export ARANGO_AUTH_STORE=disk
export ARANGO_USERNAME=root
export ARANGO_PASSWORD=
python test.py
```


### CRUD

To make these runnable environment variables must be set and ArangoDB
needs to be reachable. Here are the configurations for ArangoDB running
locally on default development settings:

Windows:
```cmd
SET ARANGO_CLUSTER=http://localhost:8529
SET ARANGO_TTL_SECONDS=31622400
SET ARANGO_REQUEST_STYLE=round-robin
SET ARANGO_AUTH=basic
SET ARANGO_USERNAME=root
SET ARANGO_DEFAULT_DATABASE=test_db
```

*Nix:
```sh
#!/usr/bin/env bash
export ARANGO_CLUSTER=http://localhost:8529
export ARANGO_TTL_SECONDS=31622400
export ARANGO_REQUEST_STYLE=round-robin
export ARANGO_AUTH=basic
export ARANGO_USERNAME=root
export ARANGO_PASSWORD=
export ARANGO_DEFAULT_DATABASE=test_db
```

```py
from arango_crud import env_config
import time

config = env_config()
config.prepare()

db = config.database() # alt: config.database('my_db')
coll = db.collection('users')
coll.ensure()

# The simplest interface
coll.replace('tj', {'name': 'TJ'}) # True
coll.read('tj') # {'name': 'TJ'}
coll.delete('tj') # True

# non-expiring
coll.replace('tj', {'name': 'TJ'}, ttl=None)
coll.delete('tj')

# custom expirations with touching
coll.replace('tj', {'name': 'TJ'}, ttl=60)
coll.touch('tj', ttl=60)

# Alternative interface.
doc = coll.document('tj')
doc.body['name'] = 'TJ'
doc.replace() # True
doc.body['note'] = 'Pretty cool'
doc.replace() # True

# We may use etags to avoid redownloading an unchanged document, but be careful
# if you are modifying the body.

# Happy case:
doc2 = coll.document('tj')
doc2.read(try_304=True) # loads {'name': 'TJ', 'note': 'Pretty cool'} from network

doc.read(try_304=True) # 304 not modified
doc2.read(try_304=True) # 304 not modified

doc.body['note'] = 'bar'
doc.replace()
doc.read(try_304=True) # 304 not modified
doc2.read(try_304=True) # loads {'name': 'TJ', 'note': 'bar'} from network

# Where it can get dangerous
doc.body['note'] = 'foo'
print(doc.body) # {'name': 'TJ', 'note': 'foo'}
doc.read() # always a complete download
print(doc.body) # {'name': 'TJ', 'note': 'bar'}
doc.read(try_304=True) # no changes on server since last read; 304 not modified
print(doc.body) # {'name': 'TJ', 'note': 'bar'}
doc.body['note'] = 'foo'
print(doc.body) # {'name': 'TJ', 'note': 'foo'}
doc.read(try_304=True) # no changes on server since last read; 304 not modified
print(doc.body) # {'name': 'TJ', 'note': 'foo'}
doc.read()
print(doc.body) # {'name': 'TJ', 'note': bar'}


# Simple caching
doc = coll.document('tj')
if not doc.read():
    # .... expensive computation ....
    doc.body = {'name': 'TJ', 'note': 'Pretty cool'}
    doc.replace()
print(f'cached value: {doc.body}')
```

## Contributing

This package adheres to pep8 guidelines unless an exception is listed in
`.flake8`. Comments are explicitly line-broken at 80 characters. Code
complexity measures (AbcComplexity, etc) are not used. This measures code
coverage and a build of below 90% code coverage is considered failing. PRs
which reduce code coverage must include an explanation of why. The examples
directory should not contain non-functional lines of code, so instead of

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
closed with the recommendation that they fork.

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

## Request Styles

When working with an ArangoDB cluster, it's important that the clients
distribute their requests amongst the various coordinators. This is why the
IP address of the coordinators is a list of addresses. The request styles
supported are `round-robin`, `weighted-round-robin`, and `random`

### Round Robin

### Weighted Round Robin

### Random

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

The recommended way to handle JWT's is the `'disk'` style. A file will contain
the JWT and some metadata about it, which will be accessed in a safe way for
even highly concurrent environments, meaning that every instance running
arango_crud on the same machine using the same config will share JWT tokens
and will only create/renew the token once per renewal period. This overhead is
extremely minor for non-concurrent environments.

If you're very confident that JWT generation is not going to be a significant
source of load and there is no multithreading, a naive approach can be enabled
with the lock and store style `None`. See the examples jwt_disk_example.py
and jwt_none_example.py
