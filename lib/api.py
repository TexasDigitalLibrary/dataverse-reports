"""Class for communicating with the Dataverse APIs"""

import requests
import logging

from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree

class DataverseApi:
    """Class for communicating with the Dataverse APIs"""

    def __init__(self, config=None):
        if config is None:
            return None

        self.config = config

        if config['host'][len(config['host'])-1] != '/':
            self.host = config['host'] + '/'
        else:
            self.host = config['host']

        self.token = config['token']

        self.version = 'v1'

        self.logger = logging.getLogger('dataverse-reports')
        self.logger.debug("Setting Dataverse API host  %s.", self.host)
        self.logger.debug("Setting Dataverse API token %s.", self.token)

        self.headers = {'X-Dataverse-key': self.token}

    def test_connection(self):
        """Test connection to Dataverse API"""

        url = self.host + 'api/info/version/'
        self.logger.debug("Testing API connection: %s.", url)
        response = requests.get(url)
        if response.status_code == 200:
            return True

        return False

    def construct_url(self, command):
        """Create URL"""

        new_url = self.host + '-H "X-Dataverse-key: ' + self.token + '"' + command
        return new_url

    def search(self, term='*', search_type='dataverse', options=None):
        """Search Dataverse API"""

        if search_type is not None:
            url = self.host + 'api/' + self.version + '/search?q=' + term + '&type=' + type
        else:
            url = self.host + 'api/' + self.version + '/search?q=' + term

        self.logger.debug("Searching Dataverse: %s.", url)
        response = requests.get(url)
        self.logger.debug("Return status: %s", str(response.status_code))
        return response

    def get_dataverse(self, identifier=''):
        """Retrieve dataverse from the API"""

        if identifier is None:
            self.logger.error("Must specify identifer.")
            return None

        url = self.host + 'api/' + self.version + '/dataverses/' + str(identifier)
        self.logger.debug("Retrieving dataverse: %s.", url)
        response = requests.get(url, headers=self.headers)
        self.logger.debug("Return status: %s.", str(response.status_code))
        return response

    def get_dataverse_contents(self, identifier=''):
        """Retrieve dataverse contents from API"""

        if identifier is None:
            self.logger.error("Must specify identifer.")
            return None

        url = self.host + 'api/' + self.version + '/dataverses/' + str(identifier) + '/contents'
        self.logger.debug("Retrieving dataverse contents: %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.debug("Return status: %s", str(response.status_code))

        response_json = response.json()
        return response_json['data']

    def get_dataverse_size(self, identifier='', includeCached=False):
        """Get size of dataverse"""

        if identifier is None:
            self.logger.error("Must specify identifer.")
            return None

        url = self.host + 'api/' + self.version + '/dataverses/' + str(identifier) + '/storagesize'
        if includeCached is True:
            url += '?includeCache=true'
        self.logger.debug("Retrieving dataverse storage size: %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.debug("Return status: %s", str(response.status_code))
        return response

    def sword_get_dataverse(self, alias=''):
        """"Retrieve SWORD dataverse"""

        if alias is None:
            self.logger.error("Must specify an alias.")
            return None

        url = self.host + '/dvn/api/data-deposit/' + self.version + '/swordv2/collection/dataverse/' + alias
        self.logger.debug("Retrieving SWORD dataverse: %s", url)
        response = requests.get(url, auth=HTTPBasicAuth(self.token, ''))
        self.logger.debug("Return status: %s", str(response.status_code))

        tree = ElementTree.fromstring(response.content)
        return tree

    def get_dataset(self, identifier=''):
        """Retrieve dataset from API"""

        if identifier is None:
            self.logger.error("Must specify an identifer.")
            return None

        url = self.host + 'api/' + self.version + '/datasets/' + str(identifier)
        self.logger.debug("Retrieving dataset: %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.debug("Return status: %s", str(response.status_code))
        return response

    def get_dataset_metric(self, identifier='', option='', doi='', date=None):
        """Retrieve metric of dataset"""

        if identifier is None or option is None or doi is None:
            self.logger.error("Must specify an identifer, option and DOI.")
            return None

        # Include date parameter if specified
        if date is not None:
            url = self.host + 'api/' + self.version + '/datasets/' + str(identifier) + '/makeDataCount/' + str(option) + '/' + date + '?persistentId=' + doi
        else:
            url = self.host + 'api/' + self.version + '/datasets/' + str(identifier) + '/makeDataCount/' + str(option) + '?persistentId=' + doi

        self.logger.debug("Retrieving dataset_metric: %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.debug("Return status: %s", str(response.status_code))        
        return response

    def get_admin_list_users(self, page=1):
        """"Get list of admin users"""

        url = self.host + 'api/' + self.version + '/admin/list-users/?selectedPage=' + str(page)
        self.logger.debug("Retrieving users list: %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.debug("Return status: %s", str(response.status_code))
        return response.json()

    def construct_parameters(self, params=None):
        """Construct parameters for URL"""

        parameters_string = ''
        first = True

        if params is not None:
            for key, value in params.items():
                if first:
                    parameters_string += key + '=' + value
                    first = False
                else:
                    parameters_string += '&' + key + '=' + value

        return parameters_string

    def make_call(self, http_type='GET', url=''):
        """Make call to Dataverse API"""

        if http_type == 'GET':
            r = requests.get(url, headers=self.headers)
        elif http_type == 'POST':
            r = requests.put(url, headers=self.headers)
        else:
            r = requests.get(url, headers=self.headers)

        return r.json

    def set_token(self, new_token=''):
        """Set Dataverse API token"""

        if new_token:
            self.token = new_token
