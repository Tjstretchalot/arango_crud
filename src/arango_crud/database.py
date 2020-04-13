"""Provides an object-oriented interface of a database within ArangoDB. This
supports existence checks, creation, and deletion on the database directly.
Most of the time, however, it's just used to create a Collection instance
within the database with the same configuration.
"""

class Database:
    """A database within ArangoDB, which acts as a collection of Collections.

    Attributes:
        config (Config): The configuration details for connecting to the
            cluster.
        name (str): The unique name for this database.
    """
    def __init__(config, name):
        pass

    def create_if_not_exists(self):
        """Create this database if it does not exist remotely.

        Returns:
            True if the database did not exist and was created, False if it
            did exist and was not changed.
        """
        pass

    def check_if_exists(self):
        """Determines if this database exists remotely.

        Returns:
            True if the database exists remotely, False when it does not exist
            remotely.
        """
        pass

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
        pass

    def collection(self, name):
        """Initialize the Collection object within this Database with the given
        name. This performs no networking. The returned object provides access
        to a convenient object-oriented interface for the given collection.

        Args:
            name (str): The name of the collection to initialize

        Returns:
            The collection instance within this database with the given name.
        """
        pass
