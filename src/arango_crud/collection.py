"""Provides an object-oriented interface of a Collection within ArangoDB.
Supports existence checks, creation, and deletion. However most of the time
it's used for initializing new Documents under this collection. This also
provides some convenience functions for just read/create-or-overwrite/delete
flows on documents.
"""
import pytypeutils as tus
from .database import Database
from . import helper


class Collection:
    """Describes a collection within ArangoDB, which acts as a namespace within
    the Database for documents.

    Attributes:
        database (Database): The database this collection resides in.
        name (str): The name of this collection
    """
    def __init__(self, database, name):
        tus.check(database=(database, Database), name=(name, str))
        self.database = database
        self.name = name

    def create_if_not_exists(self, ttl='default'):
        """If this collection does not exist it is created remotely, otherwise
        this does nothing.

        Args:
            ttl (str, int, None): If a string it must be 'default', in which
                this takes the value in the Config. If this describes a non-
                None TTL, a TTL index is created on "expires_at" if this
                collection is created from this call.

        Returns:
            True if the collection did not exist and was created, False if the
            collection already existed and was not changed.
        """
        tus.check(ttl=(ttl, (str, int, type(None))))
        if ttl == 'default':
            ttl = self.database.config.ttl_seconds
        elif isinstance(ttl, str):
            raise ValueError(f'ttl must be int, None, or the string \'default\' but got \'{ttl}\'')

        resp = helper.http_post(
            self.database.config,
            f'/_db/{self.database.name}/_api/collection',
            json={
                'name': self.name
            }
        )
        if resp.status_code == 409:
            return False
        resp.raise_for_status()
        if resp.status_code != 200:
            raise Exception(f'Unexpected status code {resp.status_code} for create collection')

        if ttl is None:
            return True

        resp = helper.http_post(
            self.database.config,
            f'/_db/{self.database.name}/_api/index?collection={self.name}#ttl',
            json={
                'type': 'ttl',
                'fields': ['expires_at'],
                'expireAfter': 0
            }
        )
        resp.raise_for_status()
        if resp.status_code != 201:
            raise Exception(f'Unexpected status code {resp.status_code} for create index')
        return True

    def check_if_exists(self):
        """Check if this collection exists remotely.

        Returns:
            True if this collection exists remotely, False otherwise.
        """
        resp = helper.http_get(
            self.database.config,
            f'/_db/{self.database.name}/_api/collection/{self.name}'
        )
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        if resp.status_code != 200:
            raise Exception(f'Unexpected status code {resp.status_code} for get collection')
        return True

    def force_delete(self):
        """Delete this collection if it exists remotely. This will delete all
        documents within this collection.

        Raises:
            AssertionError: If config.disable_collection_delete is True or this
                collection is in config.protected_collections. This is to help
                protect against developer error and is not meant as a form of
                security.

        Returns:
            True if this collection existed and was deleted, False if this
            collection did not exist.
        """
        assert not self.database.config.disable_collection_delete
        assert self.name not in self.database.config.protected_collections

        resp = helper.http_delete(
            self.database.config,
            f'/_db/{self.database.name}/_api/collection/{self.name}',
        )
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        if resp.status_code != 200:
            raise Exception(f'Unexpected status code {resp.status_code} for drop collection')
        return True

    def document(self, key):
        """Initialize a new Document with the given key within this collection.
        This does not perform any networking.

        Args:
            key (str): The unique key within this collection for the document

        Returns:
            The Document instance for an object-oriented interface to the given
            document.
        """
        from .document import Document
        return Document(self, key)

    def create_or_overwrite_doc(self, key, body, ttl='default'):
        """Ensures that the document at the given key within this collection
        has the given body and TTL, regardless of the previous state.

        Args:
            key (str): The unique key within this collection for the document
                to either create or overwrite.
            body (dict): The new body of the document
            ttl (str, int, None): Either the string 'default' for the value in
                Config, and int for time to live in seconds, or None for no
                expiration time on this document.
        """
        doc = self.document(key)
        doc.body = body
        doc.create_or_overwrite(ttl)

    def read_doc(self, key):
        """Fetches the nody of the document with the given key.

        Args:
            key (str): The unique key within this collection for the document
                to read.

        Returns:
            Either the dict body of the document or None if the document with
            that key within this collection does not exist.
        """
        doc = self.document(key)
        if doc.read():
            return doc.body
        return None

    def touch_doc(self, key, ttl='default'):
        """Refreshes the TTL on the given document to the given value. This
        SHOULD not be used to disable/enable expiry times on documents, as it
        is not concurrency-safe. This SHOULD only be used with a consistent TTL
        as it is not concurrency-safe otherwise. This will never reset a
        document to an old version, but it may fail to do anything at all.

        Args:
            key (str): The unique key within this collection to touch.
            ttl (str, int, None): Either the string 'default' for the value in
                Config, or the time-to-live after touching in seconds, or None
                to set no expiration time.

        Returns:
            True if the document existed and had its expiry time modified,
            False when the documetn did not exist or did not have its expiry
            time modified.
        """
        if self.database.config.ttl_seconds is None:
            return False
        doc = self.document(key)
        if not doc.read():
            return False
        return doc.compare_and_swap(ttl)

    def force_delete_doc(self, key):
        """Delete the document at the given key if it exists.

        Args:
            key (str): The unique key within this collection to delete.

        Returns:
            True if the document existed and was deleted, False when the
            document did not exist and was not changed.
        """
        doc = self.document(key)
        return doc.force_delete()
