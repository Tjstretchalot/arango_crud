"""Provides an object-oriented interface of a database within ArangoDB. This
supports existence checks, creation, and deletion on the database directly.
Most of the time, however, it's just used to create a Collection instance
within the database with the same configuration.
"""
from . import helper
from .config import Config
import pytypeutils as tus


class Database:
    """A database within ArangoDB, which acts as a collection of Collections.

    Attributes:
        config (Config): The configuration details for connecting to the
            cluster.
        name (str): The unique name for this database.
    """
    def __init__(self, config, name):
        tus.check(config=(config, Config), name=(name, str))
        self.config = config
        self.name = name

    def create_if_not_exists(self):
        """Create this database if it does not exist remotely.

        Returns:
            True if the database did not exist and was created, False if it
            did exist and was not changed.
        """

        # This is a bit hacky but it's weird we have to specify it for
        # each new database...
        username = None
        password = None
        if hasattr(self.config.auth, 'username'):
            username = self.config.auth.username
            password = self.config.auth.password
        else:
            username = self.config.auth.delegate.username
            password = self.config.auth.delegate.password

        resp = helper.http_post(
            self.config,
            '/_api/database',
            json={
                'name': self.name,
                'users': [
                    {
                        'username': username,
                        'password': password,
                        'active': True
                    }
                ]
            }
        )
        if resp.status_code == 409:
            return False
        resp.raise_for_status()
        if resp.status_code != 201:
            raise Exception(f'Unexpected status code {resp.status_code} for create index')
        return True

    def check_if_exists(self):
        """Determines if this database exists remotely.

        Returns:
            True if the database exists remotely, False when it does not exist
            remotely.
        """
        res = helper.http_get(
            self.config,
            f'/_db/{self.name}/_api/database/current'
        )
        if res.status_code == 404:
            return False
        if res.status_code == 200:
            return True
        res.raise_for_status()
        raise Exception(f'unexpected status code: {res.status_code}')

    def force_delete(self):
        """Deletes this database if it exists remotely, which will delete all
        of its collections and all the documents within those collections.

        Raises:
            AssertionError: If config.disable_database_delete is True or this
                database is in config.protected_databases. This is to help
                protect against developer error and is not meant as a form of
                security.

        Returns:
            True if the database existed remotely and was deleted, False if it
            did not exist remotely.
        """
        assert not self.config.disable_database_delete
        assert self.name not in self.config.protected_databases
        res = helper.http_delete(
            self.config,
            f'/_api/database/{self.name}'
        )
        if res.status_code == 404:
            return False
        res.raise_for_status()
        if res.status_code != 200:
            raise Exception(f'unexpected status code {res.status_code} for drop database')
        return True

    def collection(self, name):
        """Initialize the Collection object within this Database with the given
        name. This performs no networking. The returned object provides access
        to a convenient object-oriented interface for the given collection.

        Args:
            name (str): The name of the collection to initialize

        Returns:
            The collection instance within this database with the given name.
        """
        from .collection import Collection
        return Collection(self, name)
