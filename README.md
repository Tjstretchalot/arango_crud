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
from arango_crub import Config, BasicAuth

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
        lock_style='mutex', # See JWT Locking and Store
        store_style='disk' # See JWT Locking and Store
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
from arango_crud import EnvConfig

config = EnvConfig()
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
from arango_crud import EnvConfig

config = EnvConfig()
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
from arango_crud import EnvConfig
import time

config = EnvConfig()
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