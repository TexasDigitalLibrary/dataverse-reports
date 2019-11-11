import os
import sys
import csv
import pprint
import smtplib
import mimetypes
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class UserReports(object):
    def __init__(self, dataverse_api=None, config=None):
        if dataverse_api is None:
            print('Dataverse API required to create user reports.')
            return
        if config is None:
            print('Dataverse configuration required to create user reports.')
            return

        self.dataverse_api = dataverse_api

        # Ensure trailing slash on work_dir
        if config['work_dir'][len(config['work_dir'])-1] != '/':
            config['work_dir'] = config['work_dir'] + '/'

        self.config = config

        self.logger = logging.getLogger('dataverse-reports')

    def report_users_recursive(self, dataverse_identifier):
        # List of users
        users = []

        self.logger.info("Begin loading users for %s.", dataverse_identifier)
        self.load_users_recursive(users, dataverse_identifier)
        self.logger.info("Finished loading %s users for %s", str(len(users)), dataverse_identifier)

        # Get unique list of users
        users = list({v['id']:v for v in users}.values())

        return users

    def load_users_recursive(self, users={}, dataverse_identifier=None):
        if dataverse_identifier is None:
            self.logger.error("Dataverse identifier is required.")
            return

        self.logger.info("Loading dataverse: %s.", dataverse_identifier)

        # Add user to list
        self.logger.info('Adding creator of dataverse to report: %s', dataverse_identifier)
        self.load_user_dataverse(users, dataverse_identifier)

        # Retrieve dvObjects for this dataverse
        dataverse_contents = self.dataverse_api.get_dataverse_contents(identifier=dataverse_identifier)
        self.logger.info('Total dvObjects in this dataverse: ' + str(len(dataverse_contents)))
        for dvObject in dataverse_contents:
            if dvObject['type'] == 'dataverse':
                # Continue down the dataverse tree
                self.logger.info("Found new dataverse %s.", str(dvObject['id']))
                self.load_users_recursive(users, dvObject['id'])

    def load_user_dataverse(self, users, dataverse_identifier):
        # Load dataverse
        dataverse_response = self.dataverse_api.get_dataverse(identifier=dataverse_identifier)
        response_json = dataverse_response.json()
        if 'data' in response_json:
            dataverse = response_json['data']
            self.logger.info("Dataverse name: %s", dataverse['name'])

            # Add creator information
            if 'creator' in dataverse:
                creator = dataverse['creator']
                self.logger.debug("Adding user of dataverse: %s", creator['displayName'])
                users.append(creator)
        else:
            self.logger.warn("Dataverse was empty.")