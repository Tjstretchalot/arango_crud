"""Describes a single document within ArangoDB. This is what actually stores
the data. Amounts to a single JSON object with create/read/overwrite/delete
semantics with optional time-to-live."""


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
        pass

    def read(self):
        """Fetches the current value for this document from remote. If this
        document exists remotely, the body and etag are overwritten and this
        returns True. If the document does not exist remotely, the body is
        set to an empty dict, etag is set to None, and this returns False.

        Returns:
            True if the document was found and loaded from ArangoDB, False
            if the document did not exist.
        """
        pass

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
        pass

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
        pass

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
        pass

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
        pass

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
        pass

    def compare_and_delete(self):
        """If the remote document exists and has the same etag it is deleted.
        Otherwise this does nothing.

        Raises:
            AssertionError: If this does not have an etag set

        Returns:
            True if the remote document matched and was deleted. False when the
            remote document did not match and was not changed.
        """
        pass

    def force_delete(self):
        """Forcibly delete the remote document, without checking its version.

        Returns:
            True if the remote document existed and was deleted, False when the
            remote document did not exist and was not changed.
        """
        pass
