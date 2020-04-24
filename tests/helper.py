"""Test helper"""
import os
import sys

TEST_CLUSTER_URLS = os.environ['TEST_ARANGO_CLUSTER_URLS'].split(',')
TEST_ARANGO_DB = os.environ['TEST_ARANGO_DB']
TEST_USERNAME = os.environ['TEST_ARANGO_USERNAME']
TEST_PASSWORD = os.environ.get('TEST_ARANGO_PASSWORD', '')


def append_src_to_sys_path():
    target_paths = ['src', '../src']
    for path in target_paths:
        if os.path.exists(path):
            if path not in sys.path:
                sys.path.append(path)
            return

    raise Exception(f'failed to find src folder to test!; cwd={os.getcwd()}')


def cleanup_test_db():
    from arango_crud import Config, RandomCluster, StepBackOffStrategy, BasicAuth
    cfg = Config(
        cluster=RandomCluster(urls=TEST_CLUSTER_URLS),
        timeout_seconds=10,
        back_off=StepBackOffStrategy(steps=[1]),
        ttl_seconds=None,
        auth=BasicAuth(
            username=TEST_USERNAME,
            password=TEST_PASSWORD
        ),
        disable_database_delete=False
    )
    db = cfg.database(TEST_ARANGO_DB)
    db.force_delete()


def cleanup_lock_files():
    if os.path.exists('test.jwt'):
        os.remove('test.jwt')
    if os.path.exists('test.jwt.lock'):
        os.remove('test.jwt.lock')


append_src_to_sys_path()
cleanup_test_db()
