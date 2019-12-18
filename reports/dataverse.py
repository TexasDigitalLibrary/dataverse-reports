import os
import sys
import csv
import pprint
import re
import smtplib
import mimetypes
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .user import UserReports

class DataverseReports(object):
    def __init__(self, dataverse_api=None, config=None):
        if dataverse_api is None:
            print('Dataverse API required to create dataverse reports.')
            return

        if config is None:
            print('Dataverse configuration required to create dataverse reports.')
            return

        self.dataverse_api = dataverse_api
        self.config = config
        self.dataverse_size_pattern = re.compile('dataverse:\s(.*)\sbyte')
        self.logger = logging.getLogger('dataverse-reports')

        # Create UserReports object to retrieve user metadata
        self.user_reports = UserReports(dataverse_api=dataverse_api, config=config)

        # Ensure trailing slash on work_dir
        if config['work_dir'][len(config['work_dir'])-1] != '/':
            config['work_dir'] = config['work_dir'] + '/'

        # Load namespaces for Sword API
        self.ns = {'atom': 'http://www.w3.org/2005/Atom',
                    'sword': 'http://purl.org/net/sword/terms/state'}

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
            if 'dataverseContacts' in dataverse:
                dataverseContacts = dataverse['dataverseContacts']
                if len(dataverseContacts) > 0:
                    dataverseContact = dataverseContacts[0]
                    if 'contactEmail' in dataverseContact:
                        contactEmail = dataverseContact['contactEmail'].strip()
                        self.logger.debug("Found email of dataverse contact: %s", str(contactEmail))
                        user = self.user_reports.find_user_email(contactEmail)
                        if bool(user):
                            self.logger.debug("Adding contact information: %s", user)
                            if 'userIdentifier' in user:
                                dataverse['creatorIdentifier'] = user['userIdentifier']
                            if 'firstName' in user:
                                dataverse['creatorFirstName'] = user['firstName']
                            if 'lastName' in user:
                                dataverse['creatorLastName'] = user['lastName']
                            if 'email' in user:
                                dataverse['creatorEmail'] = user['email']
                            if 'affiliation' in user:
                                dataverse['creatorAffiliation'] = user['affiliation']
                            if 'roles' in user:
                                dataverse['creatorRoles'] = user['roles']
                        else:
                            self.logger.warn("Unable to find user from dataverseContact email: " + contactEmail)
                            dataverse['creatorEmail'] = contactEmail
                    else:
                        self.logger.warn("First dataverseContact doesn't have an email.")
                else:
                    self.logger.warn("List of dataverseContacts is empty.")
            elif 'creator' in dataverse:        # Legacy field in older Dataverse versions
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
            else:
                self.logger.warn("Unable to find dataverse creator information.")

            # Add the data (file) size of the dataverse and all its sub-dataverses
            dataverse_size_response = self.dataverse_api.get_dataverse_size(identifier=dataverse_identifier, includeCached=True)
            response_size_json = dataverse_size_response.json()
            if response_size_json['status'] == 'OK' and 'data' in response_size_json:
                dataverse_size = response_size_json['data']
                if 'message' in dataverse_size:
                    size_message = dataverse_size['message']
                    self.logger.debug("The message element from storagesize endpoint: " + size_message)
                    size_bytes_match = re.search(self.dataverse_size_pattern, size_message)
                    if size_bytes_match is not None:
                        size_bytes_string = size_bytes_match.group(1)
                        size_bytes = int(size_bytes_string.replace(',',''))
                        dataverse['contentSize (MB)'] = (size_bytes/1048576)
                    else:
                        self.logger.warning("Unable to find the bytes value in the message.")
                else:
                    self.logger.warning("No message element in response from storagesize endpoint.")

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
