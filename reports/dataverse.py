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

    def report_dataverses_recursive(self, account_info):
        # List of dataverses
        dataverses = []

        # Load dataverses
        self.load_dataverses_recursive(dataverses, account_info['identifier'])

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

            self.load_subdataverse(dataverse, dataverse_identifier)
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
            # print (dataverse) 
            dataverses.append(dataverse)

        else:
            self.logger.warn("Dataverse was empty.")

    def load_subdataverse(self, dataverse, dataverse_identifier):
        # Load child objects to check total counts of dataverses and datasets
        dataverse_contents = self.dataverse_api.get_dataverse_contents(identifier=dataverse_identifier)
        #print (dataverse_contents)
	# count dataverse and datasets
        type_by_dataverse = {}
        # list to hold different categories of dataverse
        type_of_dataverses = {}
        count_dataverses = 0
        contentSize = 0
        count_files = 0
        dt_released = 0
        dt_draft = 0
        # loop through and count no of dataverse and datasets 
        for dtype in dataverse_contents:
            if dtype["type"]:
                try:
                    # Increment the existing type  count.
                    type_by_dataverse[dtype["type"]] += 1
                except KeyError:
                    # This type  has not been seen. Set their count to 1.
                    type_by_dataverse[dtype["type"]] = 1
             # Check for the categories of dataverse by id 
            if 'dataverse' in dtype["type"]:
                dataverse_get = self.dataverse_api.get_dataverse(identifier=dtype["id"])
                dataverse_response = dataverse_get.json()
                if 'data' in dataverse_response:
                   ds = dataverse_response['data']
                   try:
                       type_of_dataverses[ds["dataverseType"]] += 1
                   except KeyError:
                       type_of_dataverses[ds["dataverseType"]] = 1
            if 'dataset' in dtype["type"]:
                dataset_get = self.dataverse_api.get_dataset(identifier=dtype["id"])
                dataset_response = dataset_get.json()
                if 'data' in dataset_response:
                   if 'latestVersion' in dataset_response['data']:
                       dset = dataset_response['data']['latestVersion']
                       if 'RELEASED' in dset['versionState']:
                          dt_released += 1
                       if 'DRAFT' in dset['versionState']:
                          dt_draft += 1
                       if 'files' in dset:
                           files = dset['files']
                           count_files += len(files)
                           for file in files:
                               if 'dataFile' in file:
                                   dataFile = file['dataFile']
                                   filesize = int(dataFile['filesize'])
                                   contentSize += filesize
                           self.logger.info('Totel size (bytes) of all files in this dataset: %s', str(contentSize))
                       # Convert to megabytes for reports
        dataverse['Total no of files'] = count_files
        dataverse['Total content size'] = (contentSize/1048576)
        dataverse['no of published datasets'] = dt_released
        dataverse['no of unpublished datasets'] = dt_draft

        if 'RESEARCHERS' in type_of_dataverses:
             dataverse['SubDVCat_Researcher']=type_of_dataverses["RESEARCHERS"]
             count_dataverses += type_of_dataverses['RESEARCHERS'] 
        if 'RESEARCH_PROJECT' in type_of_dataverses:
             dataverse['SubDVCat_Research_Project']=type_of_dataverses["RESEARCH_PROJECT"] 
             count_dataverses += type_of_dataverses['RESEARCH_PROJECT']
        if 'RESEARCH_GROUP' in type_of_dataverses:
             dataverse['SubDVCat_Research_Group']=type_of_dataverses["RESEARCH_GROUP"] 
             count_dataverses += type_of_dataverses['RESEARCH_GROUP']
        if 'LABORATORY' in type_of_dataverses:
             dataverse['SubDVCat_Laboratory']=type_of_dataverses["LABORATORY"] 
             count_dataverses += type_of_dataverses['LABORATORY']
        if 'ORGANIZATION_INSTITUTION' in type_of_dataverses:
             dataverse['SubDVCat_Organization_or_Institutions']=type_of_dataverses["ORGANIZATION_INSTITUTION"] 
             count_dataverses += type_of_dataverses['ORGANIZATION_INSTITUTION'] 
        if 'DEPARTMENT' in type_of_dataverses:
             dataverse['SubDVCat_Department']=type_of_dataverses["DEPARTMENT"] 
             count_dataverses += type_of_dataverses['DEPARTMENT']
        if 'TEACHING_COURSE' in type_of_dataverses:
             dataverse['SubDVCat_Teaching_Course']=type_of_dataverses["TEACHING_COURSE"] 
             count_dataverses += type_of_dataverses['TEACHING_COURSE'] 
        if 'UNCATEGORIZED' in type_of_dataverses:
             dataverse['SubDVCat_Uncategorized']=type_of_dataverses["UNCATEGORIZED"] 
             count_dataverses += type_of_dataverses['UNCATEGORIZED'] 
        dataverse['No of published subdataverses'] = count_dataverses
        if 'dataverse' in type_by_dataverse:
             dataverse['no of subdataverses']=int(type_by_dataverse["dataverse"])
             dataverse['No of unpublished subdataverses'] = type_by_dataverse["dataverse"] - count_dataverses
        if 'dataset' in type_by_dataverse:
             dataverse['no of datasets']=int(type_by_dataverse["dataset"])
