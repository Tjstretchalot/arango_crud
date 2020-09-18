"""Describes a single document within ArangoDB. This is what actually stores
the data. Amounts to a single JSON object with create/read/overwrite/delete
semantics with optional time-to-live."""
from .collection import Collection
from . import helper
import pytypeutils as tus
from datetime import datetime, timedelta, timezone


class Document:
    """A document within ArangoDB.

    Attributes:
        collection (Collection): The collection this document resides in.
            Should not be modified after initialization.
        key (str): The key which is used to look this document up. Should not
            be modified after initialization.
        body (dict): The body of this document as far as we know. This may not
            match the ArangoDB version. This is initialized to an empty dict if
            no network requests are made. This does not include metavalues like
            _key. May be modified directly with an understanding of how etag's
            work.
        etag (str, None): If we've saved to or loaded from the underlying DB,
            this is the latest version of the document we used. Should not
            be modified directly.
    """
    def __init__(self, collection, key):
        tus.check(collection=(collection, Collection), key=(key, str))
        self.collection = collection
        self.key = key
        self.etag = None
        self.body = {}

    def read(self):
        """Fetches the current value for this document from remote. If this
        document exists remotely, the body and etag are overwritten and this
        returns True. If the document does not exist remotely, the body is
        set to an empty dict, etag is set to None, and this returns False.

        Returns:
            True if the document was found and loaded from ArangoDB, False
            if the document did not exist.
        """
        resp = helper.http_get(
            self.collection.database.config,
            f'/_db/{self.collection.database.name}/_api/document/{self.collection.name}/{self.key}'
        )
        if resp.status_code == 404:
            self.body = {}
            self.etag = None
            return False
        resp.raise_for_status()
        if resp.status_code != 200:
            raise Exception(f'unexpected status code {resp.status_code} for doc read')
        self.body = resp.json()['value']
        self.etag = resp.headers['etag']
        return True

    def read_if_remote_newer(self):
        """If the remote has a different etag than we have locally, this
        will update body and etag to reflect that new value. If the remote
        has the same etag as we have locally this does nothing.

        Raises:
            AssertionError: If this does not have an etag set.

        Returns:
            True if a newer version of the document was found and loaded from
            ArangoDB, False if the document did not exist or was at the same
            version.
        """
        assert self.etag is not None
        resp = helper.http_get(
            self.collection.database.config,
            f'/_db/{self.collection.database.name}/_api/document/{self.collection.name}/{self.key}',
            headers={
                'If-None-Match': self.etag
            }
        )
        if resp.status_code == 304 or resp.status_code == 404:
            return False
        resp.raise_for_status()
        if resp.status_code != 200:
            raise Exception(f'unexpected status code {resp.status_code} for get doc with etag')
        self.body = resp.json()['value']
        self.etag = resp.headers['etag']
        return True

    def create(self, ttl='default'):
        """If this document does not exist remotely it is created with our
        current body and the specified time to live and this returns True. If
        the document does exist remotely this does nothing and returns False.

        Raises:
            AssertionError: If this has an etag set.

        Args:
            ttl (str, int, None): Should be the time for the document to live
                if it is created, in seconds, or the string 'default' to take
                the value set in Config, or the value None to never expire.

        Returns:
            True if the document did not exist and was created, False if the
            document did exist and was not modified.
        """
        assert self.etag is None

        exp_at = self._calculate_expires_at_str(ttl)
        resp = helper.http_post(
            self.collection.database.config,
            f'/_db/{self.collection.database.name}/_api/document/{self.collection.name}',
            json={
                '_key': self.key,
                'expires_at': exp_at,
                'value': self.body
            }
        )
        if resp.status_code in (409, 412):
            return False
        resp.raise_for_status()
        if resp.status_code == 201 or resp.status_code == 202:
            self.etag = resp.headers['etag']
            return True
        raise Exception(f'unexpected status code {resp.status_code} for create doc')

    def compare_and_swap(self, ttl='default'):
        """Performs a compare-and-swap operation. If the remote document exists
        and has the same etag, the body is updated, the TTL is refreshed, and
        this returns True. Otherwise, when the remote document either does not
        exist or is at a different version, this does nothing and returns
        False.

        Raises:
            AssertionError: If this does not have an etag set.

        Args:
            ttl (str, int, None): Should be the time for the document to live
                if it is refreshed in seconds, or the string 'default' to take
                the value set in Config, or the value None to never expire.

        Returns:
            True if the remote document matched our etag and was updated, False
            if the remote document did not match and was not changed.
        """
        assert self.etag is not None

        exp_at = self._calculate_expires_at_str(ttl)
        resp = helper.http_put(
            self.collection.database.config,
            f'/_db/{self.collection.database.name}/_api/document/{self.collection.name}/{self.key}',
            json={
                'expires_at': exp_at,
                'value': self.body
            },
            headers={
                'If-Match': self.etag
            }
        )
        if resp.status_code == 412 or resp.status_code == 404:
            return False
        resp.raise_for_status()
        if resp.status_code == 201 or resp.status_code == 202:
            self.etag = resp.headers['etag']
            return True
        raise Exception(f'unexpected status code {resp.status_code} for replace doc')

    def overwrite(self, ttl='default'):
        """If this document exists in ArangoDB the body is updated, the TTL is
        refreshed, and this returns True. Otherwise, when the document does not
        exist, nothing happens and this returns False.

        Args:
            ttl (str, int, None): Should be the time for the document to live
                if it is refreshed in seconds, or the string 'default' to take
                the value set in Config, or the value None to never expire.

        Returns:
            True if the remote document existed and was updated, False if the
            remote document did not exist and was not created.
        """
        exp_at = self._calculate_expires_at_str(ttl)
        resp = helper.http_put(
            self.collection.database.config,
            f'/_db/{self.collection.database.name}/_api/document/{self.collection.name}/{self.key}',
            json={
                'expires_at': exp_at,
                'value': self.body
            }
        )
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        if resp.status_code == 201 or resp.status_code == 202:
            self.etag = resp.headers['etag']
            return True
        raise Exception(f'unexpected status code {resp.status_code} for replace doc')

    def create_or_overwrite(self, ttl='default'):
        """Regardless of the state of this document in ArangoDB, it will be
        created or updated to reflect this instances values and the given
        TTL.

        Args:
            ttl (str, int, None): Should be the time for the document to live
                if it is refreshed or created in seconds, or the string
                'default' to take the value set in Config, or the value None to
                never expire.
        """
        exp_at = self._calculate_expires_at_str(ttl)
        resp = helper.http_post(
            self.collection.database.config,
            (
                f'/_db/{self.collection.database.name}'
                + f'/_api/document/{self.collection.name}?overwrite=true'
            ),
            json={
                '_key': self.key,
                'expires_at': exp_at,
                'value': self.body
            }
        )
        resp.raise_for_status()
        if resp.status_code == 201 or resp.status_code == 202:
            self.etag = resp.headers['etag']
            return True
        raise Exception(f'unexpected status code {resp.status_code} for create doc')

    def compare_and_delete(self):
        """If the remote document exists and has the same etag it is deleted.
        Otherwise this does nothing.

        Raises:
            AssertionError: If this does not have an etag set

        Returns:
            True if the remote document matched and was deleted. False when the
            remote document did not match and was not changed.
        """
        assert self.etag is not None
        resp = helper.http_delete(
            self.collection.database.config,
            (
                f'/_db/{self.collection.database.name}'
                + f'/_api/document/{self.collection.name}/{self.key}'
            ),
            headers={
                'If-Match': self.etag
            }
        )
        if resp.status_code == 404 or resp.status_code == 412:
            return False
        resp.raise_for_status()
        if resp.status_code == 200 or resp.status_code == 202:
            self.etag = None
            return True
        raise Exception(f'unexpected status code {resp.status_code} for delete doc')

    def force_delete(self):
        """Forcibly delete the remote document, without checking its version.

        Returns:
            True if the remote document existed and was deleted, False when the
            remote document did not exist and was not changed.
        """
        resp = helper.http_delete(
            self.collection.database.config,
            (
                f'/_db/{self.collection.database.name}'
                + f'/_api/document/{self.collection.name}/{self.key}'
            )
        )
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        if resp.status_code == 200 or resp.status_code == 202:
            self.etag = None
            return True
        raise Exception(f'unexpected status code {resp.status_code} for delete doc')

    def _calculate_expires_at_str(self, ttl):
        """Calculate the expires at time as an iso-formatted string for the
        given ttl.

        Args:
            ttl (str, int, None): The string 'default', a time in seconds, or
                None to return None

        Returns:
            An iso-formatted date time string for expiration if ttl is not None
            (and either config ttl is not None or ttl is not default)
        """
        tus.check(ttl=(ttl, (str, int, type(None))))
        if ttl == 'default':
            ttl = self.collection.database.config.ttl_seconds
        elif isinstance(ttl, str):
            raise ValueError(f'ttl should be int, None, or \'default\', got \'{ttl}\'')

        if ttl is None:
            return None

        exp_at = datetime.utcnow() + timedelta(seconds=ttl)
        return exp_at.replace(tzinfo=timezone.utc).isoformat()
