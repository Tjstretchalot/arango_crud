"""Connects to arango and performs an authenticated request using JWT. This
shows how to use no JWT cache, which can result in significantly degraded
performance when many instances are running on the same machine and restarts
are common.
"""
from arango_crud import (
    Config, RandomCluster, StepBackOffStrategy, JWTAuth
)
from arango_crud.database import Database
import os


def main():
    # Normally one would use env_config instead of parsing the environment
    # variables directly, but we do this here to make the example have as
    # little magic as possible.
    urls = os.environ.get('ARANGO_CLUSTER', 'http://localhost:8529').split(',')
    username = os.environ.get('ARANGO_USERNAME', 'root')
    password = os.environ.get('ARANGO_PASSWORD')

    cfg = Config(
        cluster=RandomCluster(urls=urls),
        timeout_seconds=3,
        back_off=StepBackOffStrategy(steps=[0.1, 0.5, 1, 1, 1]),
        ttl_seconds=31622400,
        auth=JWTAuth(
            username=username,
            password=password,
            cache=None
        )
    )

    db: Database = cfg.database('fake_db')
    assert isinstance(db, Database)
    assert db.check_if_exists() is False
