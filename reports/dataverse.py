import os
import sys
import csv
import pprint
import smtplib
import mimetypes
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class DataverseReports(object):
    def __init__(self, dataverse_api=None, config=None):
        if dataverse_api is None:
            print('Dataverse API required to create dataverse reports.')
            return

        if config is None:
            print('Dataverse configuration required to create dataverse reports.')
            return

        self.dataverse_api = dataverse_api

        # Ensure trailing slash on work_dir
        if config['work_dir'][len(config['work_dir'])-1] != '/':
            config['work_dir'] = config['work_dir'] + '/'

        # Load namespaces for Sword API
        self.ns = {'atom': 'http://www.w3.org/2005/Atom',
                    'sword': 'http://purl.org/net/sword/terms/state'}

        self.config = config
        self.logger = logging.getLogger('dataverse-reports')

    def report_dataverses_recursive(self, dataverse_identifier):
        # List of dataverses
        dataverses = []

        # Load dataverses
        self.load_dataverses_recursive(dataverses, dataverse_identifier)

        return dataverses

    def load_dataverses_recursive(self, dataverses=[], dataverse_identifier=None):
        if dataverse_identifier is None:
            return

        # Add Dataverse to list
        self.logger.info('Adding dataverse to report: %s', dataverse_identifier)
        self.load_dataverse(dataverses, dataverse_identifier)

        # Load child objects
        dataverse_contents = self.dataverse_api.get_dataverse_contents(identifier=dataverse_identifier)
        for dvObject in dataverse_contents:
            if dvObject['type'] == 'dataverse':
                self.load_dataverses_recursive(dataverses, dvObject['id'])

    def load_dataverse(self, dataverses, dataverse_identifier):
        # Load dataverse
        self.logger.info("Dataverse identifier: %s", dataverse_identifier)
        dataverse_response = self.dataverse_api.get_dataverse(identifier=dataverse_identifier)
        response_json = dataverse_response.json()
        if 'data' in response_json:
            dataverse = response_json['data']            

            self.logger.info("Dataverse name: %s", dataverse['name'])

            # Flatten the nested creator information
            if 'creator' in dataverse:
                self.logger.debug("Replacing creator array.")
                creator = dataverse['creator']
                if 'identifier' in creator:
                    dataverse['creatorIdentifier'] = creator['identifier']
                if 'displayName' in creator:
                    dataverse['creatorName'] = creator['displayName']
                if 'email' in creator:
                    dataverse['creatorEmail'] = creator['email']
                if 'affiliation' in creator:
                    dataverse['creatorAffiliation'] = creator['affiliation']
                if 'position' in creator:
                    dataverse['creatorPosition'] = creator['position']
                dataverse.pop('creator')

            # Add the 'dataverseHasBeenReleased' field from the Sword API
            if 'alias' in dataverse:
                sword_dataverse = self.dataverse_api.sword_get_dataverse(dataverse['alias'])
                dataverse_has_been_released = sword_dataverse.find('sword:dataverseHasBeenReleased', self.ns)
                if dataverse_has_been_released is not None:
                    if dataverse_has_been_released.text == 'true':
                        self.logger.debug("Element 'dataverseHasBeenReleased' is true.")
                        dataverse['released'] = 'Yes'
                    else:
                        self.logger.debug("Element 'dataverseHasBeenReleased' is false.")
                        dataverse['released'] = 'No'
                else:
                    self.logger.debug("Element 'dataverseHasBeenReleased' is not present in XML.")

            # Load datasets
            #dataverse_contents = self.dataverse_api.get_dataverse_contents(identifier=dataverse_identifier)
            #for dvObject in dataverse_contents:
                #if dvObject['type'] == 'dataset':
                    #self.load_dataset(dataverse, dvObject['id']) 

            dataverses.append(dataverse)
        else:
            self.logger.warn("Dataverse was empty.")
