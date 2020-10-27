import psycopg2
import logging


class DataverseDatabase(object):
    def __init__(self, host=None, database=None, username=None, password=None):
        self.conn = None
        self.host = host
        self.database = database
        self.username = username
        self.password = password

        self.logger = logging.getLogger('dataverse-reports')

    def create_connection(self):
        # Debug information
        self.logger.info("Attempting to connect to Dataverse database: %s (host), %s (database), %s (username) ******** (password).", self.host, self.database, self.username)

        # Create connection to database
        try:
            connect_str = "dbname='" + self.database + "' user='" + self.username + "' host='" + self.host + "' " + "password='" + self.password + "'"
            self.conn = psycopg2.connect(connect_str)
            return True
        except Exception as e:
            self.logger.error("Cannot connect to database. Please check connection information and try again.")
            return False

    def get_download_count(self, dataset_id=None):
        if dataset_id is None:
            print("Dataset ID is required.")
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(g.id) FROM guestbookresponse g LEFT JOIN filedownload f on g.id = f.guestbookresponse_id WHERE g.dataset_id = %s;", [str(dataset_id)])
        result = cursor.fetchone()
        count = result[0]
        return count
