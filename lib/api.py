import requests
import logging

class DataverseApi(object):
    def __init__(self, host=None, token=None):
        if host[len(host)-1] != '/':
            self.host = host + '/'
        else:
            self.host = host

        self.token = token
        self.version = 'v1'

        self.logger = logging.getLogger('dataverse-reports')
        self.logger.debug("Setting Dataverse API host  %s.", self.host)
        self.logger.debug("Setting Dataverse API token %s.", self.token)


    def test_connection(self):
        url = self.host + 'api/info/version/'
        self.logger.debug("Testing API connection: %s.", url)
        response = requests.get(url)
        if response.status_code == 200:
            return True
        else:
            return False

    def construct_url(self, command):
        new_url = self.host + '-H "X-Dataverse-key: ' + self.token + '"' + command
        return new_url

    def search(self, term='*', type='dataverse', options={}):
        if type is not None:
            url = self.host + 'api/' + self.version + '/search?q=' + term + '&type=' + type
        else:
            url = self.host + 'api/' + self.version + '/search?q=' + term

        self.logger.debug("Searching Dataverse: %s.", url)
        response = requests.get(url)
        self.logger.debug("Return status: %s", str(response.status_code))
        return response

    def get_dataverse(self, identifier=''):
        if identifier is None:
            self.logger.error("Must specify identifer.")
            return

        url = self.host + 'api/' + self.version + '/dataverses/' + str(identifier)
        self.logger.debug("Retrieving dataverse: %s.", url)
        response = requests.get(url)
        self.logger.debug("Return status: %s.", str(response.status_code))
        return response

    def get_dataverse_contents(self, identifier=''):
        if identifier is None:
            self.logger.error("Must specify identifer.")
            return

        url = self.host + 'api/' + self.version + '/dataverses/' + str(identifier) + '/contents'
        self.logger.debug("Retrieving dataverse contents: %s", url)
        response = requests.get(url)
        self.logger.debug("Return status: %s", str(response.status_code))

        response_json = response.json()
        return response_json['data']

    def get_dataset(self, identifier=''):
        if identifier is None:
            self.logger.error("Must specify identifer.")
            return

        url = self.host + 'api/' + self.version + '/datasets/' + str(identifier)
        self.logger.debug("Retrieving dataset: %s", url)
        response = requests.get(url)
        self.logger.debug("Return status: %s", str(response.status_code))
        return response

    def construct_parameters(self, params={}):
        parameters = ''
        first = True

        for key, value in dict.items():
            if first:
                parameters += key + '=' + value
                first = False
            else:
                parameters += '&' + key + '=' + value

        return parameters

    def make_call(self, type='GET', url=''):
        if type == 'GET':
            r = requests.get(url, auth=self.token)
        elif type == 'POST':
            r = requests.put(url, auth=self.token)
        else:
            r = requests.get(url, auth=self.token)

        return r.json

    def set_token(self, new_token=''):
        if new_token:
            self.token = new_token
