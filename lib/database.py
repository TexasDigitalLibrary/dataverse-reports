"""Class to communicate with Dataverse database"""

import logging
import psycopg

class DataverseDatabase(object):
    """Class to communicate with Dataverse database"""

    def __init__(self, config=None):
        if config is None:
            return None

        self.config = config

        self._connection_uri = f"dbname={config['name']} user={config['username']} password={config['password']} host={config['host']} port={config['port']}"
        self.logger = logging.getLogger('dataverse-reports')

    def __enter__(self):
        try:
            self._connection = psycopg.connect(
                self._connection_uri, cursor_factory=psycopg.ClientCursor
            )
        except psycopg.OperationalError as err:
            self.logger.error("Cannot connect to database. Please check connection information.")
            self.logger.error("Error: %s, %s", err, type(err))

        return self._connection

    def create_connection(self):
        """Create database connection"""

        # Debug information
        self.logger.info("Attempting to connect to Dataverse database: %s (host), %s (database), %s (username) ******** (password).", self.host, self.database, self.username)

        # Create connection to database
        try:
            connect_str = "dbname='" + self.database + "' user='" + self.username + "' host='" + self.host + "' " + "password='" + self.password + "'"
            self.conn = psycopg.connect(connect_str)
            return True
        psycopg.OperationalError as e:
            self.logger.error("Cannot connect to database. Please check connection information and try again. %s", e)
            return False

    def get_download_count(self, dataset_id=None):
        """Get download count"""

        if dataset_id is None:
            print("Dataset ID is required.")
            return None

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(g.id) FROM guestbookresponse g LEFT JOIN fileaccessrequests f on g.id = f.guestbookresponse_id WHERE g.dataset_id = %s;", [str(dataset_id)])
        result = cursor.fetchone()
        count = result[0]
        return count
