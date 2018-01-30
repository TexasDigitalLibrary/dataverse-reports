import os
import sys
import csv
import pprint
import smtplib
import mimetypes
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class DatasetReports(object):
    def __init__(self, dataverse_api=None, dataverse_database=None, config=None):
        if dataverse_api is None:
            print('Dataverse API required to create dataset reports.')
            return
        if dataverse_database is None:
            print('Dataverse database required to create dataset reports.')
            return
        if config is None:
            print('Dataverse configuration required to create dataset reports.')
            return

        self.dataverse_api = dataverse_api
        self.dataverse_database = dataverse_database

        # Ensure trailing slash on work_dir
        if config['work_dir'][len(config['work_dir'])-1] != '/':
            config['work_dir'] = config['work_dir'] + '/'

        self.config = config

        # API and database fields used in reports
        root_fieldnames = ['dataverse', 'id', 'identifier', 'persistentUrl', 'protocol', 'authority', 'publisher', 'publicationDate']
        latest_fieldnames = ['versionState', 'lastUpdateTime', 'releaseTime', 'createTime', 'license', 'termsOfUse']
        metadata_fieldnames = ['title', 'author', 'datasetContact', 'dsDescription', 'notesText', 'subject', 'productionDate', 'productionPlace', 'depositor', 'dateOfDeposit']
        database_fieldnames = ['downloadCount']
        files_metadata = ['contentSize']
        self.fieldnames = root_fieldnames + latest_fieldnames + metadata_fieldnames + database_fieldnames + files_metadata

        self.logger = logging.getLogger('dataverse-reports')

    def generate_reports(self, type='all'):
        if type == 'all':
            self.logger.info("Generating report of all datasets for super admin.")
            self.report_datasets_admin_recursive()
        elif type == 'institutions':
            self.logger.info("Generating report of datasets for each institution.")
            for key in self.config['accounts']:
                account_info = self.config['accounts'][key]

                self.logger.info("Generating recursive report for %s.", account_info['name'])
                self.report_datasets_recursive(account_info)

    def report_datasets_admin_recursive(self):
        # List of Datasets
        datasets = []
        report_file_paths = []

        for key in self.config['accounts']:
            account_info = self.config['accounts'][key]
            self.logger.info("Generating dataset report for %s.", account_info['identifier'])
            self.load_datasets_recursive(datasets, account_info['identifier'])

            if len(datasets) > 0:
                # Write results to CSV file
                output_file = account_info['identifier'] + '-datasets.csv'
                self.save_report(output_file_path=self.config['work_dir'] + output_file, headers=self.fieldnames, data=datasets)

                # Add file to reports list
                report_file_paths.append(self.config['work_dir'] + output_file)

            # Reset list
            datasets = []

        # Send results to admin email addresses
        if len(report_file_paths) > 0:
            self.email_report_admin(report_file_paths=report_file_paths)

    def report_datasets_recursive(self, account_info):
        # List of Datasets
        datasets = []

        self.logger.info("Begin loading datasets for %s.", account_info['identifier'])
        self.load_datasets_recursive(datasets, account_info['identifier'])
        self.logger.info("Finished loading %s datasets for %s", str(len(datasets)), account_info['identifier'])

        if len(datasets) > 0:
            # Write results to CSV file
            output_file = account_info['identifier'] + '-datasets.csv'
            self.save_report(output_file_path=self.config['work_dir'] + output_file, headers=self.fieldnames, data=datasets)

            # Send results to contacts list
            self.email_report_institution(report_file_paths=[self.config['work_dir'] + output_file], account_info=account_info)

    def load_datasets_recursive(self, datasets={}, dataverse_identifier=None):
        if dataverse_identifier is None:
            self.logger.error("Dataverse identifier is required.")
            return

        # Retrieve datasets for this dataverse
        dataverse_contents = self.dataverse_api.get_dataverse_contents(dataverse_identifier)
        for dvObject in dataverse_contents:
            if dvObject['type'] == 'dataset':
                # Add dataset to this dataverse
                self.logger.info("Adding dataset %s to dataverse %s.", str(dvObject['id']), str(dataverse_identifier))
                self.add_dataset(datasets, dataverse_identifier, dvObject['id'])
            if dvObject['type'] == 'dataverse':
                self.logger.info("Found new datavserse %s.", str(dvObject['id']))
                self.load_datasets_recursive(datasets, dvObject['id'])

    def add_dataset(self, datasets, dataverse_identifier, dataset_id):
        # Load dataset
        dataset_response = self.dataverse_api.get_dataset(identifier=dataset_id)
        response_json = dataset_response.json()
        dataset = response_json['data']

        if 'latestVersion' in dataset:
            latest_version = dataset['latestVersion']
            metadata_blocks = latest_version['metadataBlocks']

            # Flatten the latest_version information
            for key, value in latest_version.items():
                if key != 'metadataBlocks':
                    dataset[key] = value

                # Flatten the nested citation fields information
                citation = metadata_blocks['citation']
                fields = citation['fields']
                for item in fields:
                    self.logger.debug("Looking at field: %s.", item['typeName'])
                    valuesString = self.get_value_recursive('', item)
                    if valuesString.endswith(' ; '):
                        valuesString = valuesString[:-len(' ; ')]

                    typeName = item['typeName']
                    dataset[typeName] = valuesString

            # Remove nested information
            dataset.pop('latestVersion')

        # Use dataverse_database to retrieve cumulative download count of file in this dataset
        download_count = self.dataverse_database.get_download_count(dataset_id=dataset_id)
        self.logger.info("Download count for dataset: %s", str(download_count))
        dataset['downloadCount'] = download_count

        if 'files' in dataset:
            contentSize = 0
            files = dataset['files']
            for file in files:
                if 'dataFile' in file:
                    dataFile = file['dataFile']
                    filesize = int(dataFile['filesize'])
                    contentSize += filesize
            self.logger.info('Totel size of all files in this dataset: %s', str(contentSize))
            dataset['contentSize'] = contentSize

        # Retrieve dataverse to get alias
        dataverse_response = self.dataverse_api.get_dataverse(identifier=dataverse_identifier)
        response_json = dataverse_response.json()
        dataverse = response_json['data']

        self.logger.info("Adding another dataset with alias: %s", str(dataverse['alias']))
        dataset['dataverse'] = dataverse['alias']
        datasets.append(dataset)

    def get_value_recursive(self, valuesString, field):
        if not field['multiple']:
            if field['typeClass'] == 'primitive':
                valuesString += field['value']
                self.logger.debug("New value of valuesString: %s", str(valuesString))
                return valuesString
            elif field['typeClass'] == 'controlledVocabulary':
                subValue = ''
                for value in field['value']:
                    subValue += value + ', '
                subValue = subValue[:-2]
                valuesString += subValue
                self.logger.debug("New value of valuesString: %s", str(valuesString))
                return valuesString
            elif field['typeClass'] == 'compound':
                subValue = ''
                if isinstance(field['value'], list):
                    for value in field['value']:
                        if isinstance(value, str):
                            self.logger.debug("Value: %s", value)
                        for key, elements in value.items():
                            if not elements['multiple']:
                                subValue += elements['value']
                            else:
                                subValue += self.get_value_recursive(valuesString, subValue, elements['value'])

                            self.logger.debug("New subValue: %s", subValue)
                            subValue += " - "

                        nick
                        valuesString += subValue + " ; "
                else:
                    value = field['value']
                    for key, elements in value.items():
                        if not elements['multiple']:
                            subValue += elements['value']
                        else:
                            subValue += self.get_value_recursive(valuesString, subValue, elements['value'])

                        self.logger.debug("New subValue: %s", subValue)
                        subValue += " - "

                    valuesString += subValue + " ; "

                if valuesString.endswith(' ; '):
                    valuesString = valuesString[:-len(' ; ')]
                self.logger.debug("New value of valuesString: %s", str(valuesString))
                return valuesString
            else:
                self.logger.debug("Unrecognized typeClass: %s", field['typeClass'])
        else:
            if field['typeClass'] == 'primitive':
                subValue = ''
                for value in field['value']:
                    subValue += value + ', '
                subValue = subValue[:-2]
                valuesString += subValue
                self.logger.debug("New value of valuesString: %s", str(valuesString))
                return valuesString
            elif field['typeClass'] == 'controlledVocabulary':
                subValue = ''
                for value in field['value']:
                    subValue += value + ', '
                subValue = subValue[:-2]
                valuesString += subValue
                self.logger.debug("New value of valuesString: %s", str(valuesString))
                return valuesString
            elif field['typeClass'] == 'compound':
                subValue = ''
                for value in field['value']:
                    for key, elements in value.items():
                        self.logger.debug("Key: %s", key)
                        if not elements['multiple']:
                            subValue += elements['value']
                        else:
                            subValue += self.get_value_recursive(valuesString, subValue, elements['value'])

                        self.logger.debug("New subValue: %s", subValue)
                        subValue += " - "

                    subValue = subValue[:-3]
                    valuesString += subValue + " ; "

                self.logger.debug("New value of valuesString: %s", str(valuesString))
                return valuesString
            else:
                self.logger.debug("Unrecognized typeClass: %s", field['typeClass'])

    def save_report(self, output_file_path=None, headers=[], data=[]):
        # Sanity checks
        if output_file_path is None:
            self.logger.error("Output file path is required.")
            return
        if not headers:
            self.logger.error("Report headers are required.")
            return
        if not data:
            self.logger.error("Report data are required.")
            return

        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore', dialect='excel', quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            for result in data:
                writer.writerow(result)

        self.logger.info("Saved report to file %s.", output_file_path)

    def email_report_institution(self, report_file_paths=[], account_info=[]):
        if len(report_file_paths) == 0:
            self.logger.error("At least one report file path is required.")
            return

        # Construct email information
        subject = 'Dataset report for ' + account_info['name']
        from_email = self.config['from_email']
        body = "The report in tab-delimited CSV format is attached."

        # Send email(s) to contact(s)
        for contact in account_info['contacts']:
            self.logger.info("Sending report to %s.", contact)
            self.email_report_internal(report_file_paths=report_file_paths, to_email=contact, from_email=from_email, subject=subject, body=body)

    def email_report_admin(self, report_file_paths=[]):
        if len(report_file_paths) == 0:
            self.logger.error("At least one report file path is required.")
            return

        # Construct email information
        subject = 'Dataset reports for ' + self.config['dataverse_api_host']
        from_email = self.config['from_email']
        body = "The reports in tab-delimited CSV format is attached."

        # Send email(s) to admin email address(es)
        for admin_email in self.config['admin_emails']:
            self.logger.info("Sending reports to admin %s.", admin_email)
            self.email_report_internal(report_file_paths=report_file_paths, to_email=admin_email, from_email=from_email, subject=subject, body=body)

    def email_report_internal(self, report_file_paths=[], to_email=None, from_email=None, subject=None, body=None):
        if len(report_file_paths) == 0:
            self.logger.error("At least one report file path is required.")
            return
        if to_email is None or from_email is None or subject is None or body is None:
            self.logger.error("Required email information is missing.")
            return

        # Create message with text fields
        message = MIMEMultipart()
        message['Subject'] = subject
        message['To'] = to_email
        message['From'] = from_email
        message.preamble = body

        # Attach report file(s)
        for report_file_path in report_file_paths:
            # Check that report file exists
            if not os.path.isfile(report_file_path):
                self.logger.warning("Report file doesn't exist: %s.", report_file_path)
                continue

            path, report_file_name = os.path.split(report_file_path)

            ctype, encoding = mimetypes.guess_type(report_file_path)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            # Attach report
            with open(report_file_path) as fp:
                attachment = MIMEText(fp.read(), _subtype=subtype)

            attachment.add_header('Content-Disposition', 'attachment', filename=report_file_name)
            message.attach(attachment)

        # Send email
        self.logger.info("Sending dataset report to %s.", to_email)
        with smtplib.SMTP('localhost') as s:
            s.send_message(message)
