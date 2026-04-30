"""Class to communicate with Dataverse database"""

import logging
import psycopg

class DataverseDatabase(object):
    """Class to communicate with Dataverse database"""

    def __init__(self, config=None):
        if config is None:
            return None

        self.logger = logging.getLogger('dataverse-reports')

        self.config = config
        self._connection_string = f"dbname={config['name']} user={config['username']} password={config['password']} host={config['host']} port={config['port']}"

        # Debug information
        self.logger.info("Attempting to connect to Dataverse database: %s (host), %s (database), %s (username) ******** (password).", self.config['host'], self.config['name'], self.config['username'])

        try:
            self._connection = psycopg.connect(
                self._connection_string, cursor_factory=psycopg.ClientCursor
            )
        except psycopg.OperationalError as err:
            self.logger.error("Cannot connect to database. Please check connection information.")
            self.logger.error("Error: %s, %s", err, type(err))
            return None

    def get_download_count(self, dataset_id=None):
        """Get download count"""

        if dataset_id is None:
            print("Dataset ID is required.")
            return None

        try:
            # Use context manager to ensure the connection is closed automatically
            with psycopg.connect(self._connection_string) as conn:
                # Perform database operations
                cursor = conn.execute("SELECT COUNT(g.id) FROM guestbookresponse g LEFT JOIN fileaccessrequests f on g.id = f.guestbookresponse_id WHERE g.dataset_id = %s;", [str(dataset_id)])
                result = cursor.fetchone()
                count = result[0]
                return count
        except psycopg.OperationalError as e:
            self.logger.error("Cannot connect to database. Please check connection information.")
            self.logger.error("Error: %s, %s", e, type(e))

        return None
