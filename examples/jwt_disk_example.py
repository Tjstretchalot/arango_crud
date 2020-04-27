"""Connects to arango and performs an authenticated request using JWT. This
shows how to use a disk JWT cache, which uses a disk locking and caching
strategy to share a single JWT across all instances running on the same
machine.
"""
from arango_crud import (
    Config, RandomCluster, StepBackOffStrategy, JWTAuth,
    JWTDiskCache
)
from arango_crud.database import Database
import os


def main():
    # Normally one would use env_config instead of parsing the environment
    # variables directly, but we do this here to make the example have as
    # little magic as possible.
    urls = os.environ.get('ARANGO_CLUSTER', 'http://localhost:8529').split(',')
    username = os.environ.get('ARANGO_AUTH_USERNAME', 'root')
    password = os.environ.get('ARANGO_AUTH_PASSWORD')

    cfg = Config(
        cluster=RandomCluster(urls=urls),
        timeout_seconds=3,
        back_off=StepBackOffStrategy(steps=[0.1, 0.5, 1, 1, 1]),
        ttl_seconds=31622400,
        auth=JWTAuth(
            username=username,
            password=password,
            cache=JWTDiskCache(  # See JWT Caches
                lock_file='.jwt_disk_example.lock',
                lock_time_seconds=10,
                store_file='.jwt_disk_example'
            )
        )
    )

    print(f'Connecting to cluster={urls}, username={username}')
    cfg.prepare()

    db: Database = cfg.database('fake_db')
    assert isinstance(db, Database)
    assert db.check_if_exists() is False

    print('Lock file:')
    with open('.jwt_disk_example.lock') as fin:
        print(fin.read())
    print()
    print('JWT file:')
    with open('.jwt_disk_example') as fin:
        print(fin.read())

    os.remove('.jwt_disk_example.lock')
    os.remove('.jwt_disk_example')
