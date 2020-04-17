# Tests

Tests purposely deviate from the standard environment variables to test other
ways of initializing and to have fine-grained pre-test setups. This will touch
files within the current working directory, where all files are prefixed with
"test"

Required environment variables through example:

```sh
export TEST_ARANGO_CLUSTER_URLS=http://localhost:5829
export TEST_ARANGO_DB=test_db
export TEST_ARANGO_USERNAME=root
export TEST_ARANGO_PASSWORD=
```
