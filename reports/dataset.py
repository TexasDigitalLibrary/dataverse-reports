"""Class for dataset reports"""

import logging
import datetime
import time

class DatasetReports:
    """Class for dataset reports"""

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

        self.logger = logging.getLogger('dataverse-reports')

    def report_datasets_recursive(self, dataverse_identifier):
        """Load all datasets"""

        # List of datasets
        datasets = []

        self.logger.info("Begin loading datasets for %s.", dataverse_identifier)
        self.load_datasets_recursive(datasets, dataverse_identifier)
        self.logger.info("Finished loading %s datasets for %s",
                         str(len(datasets)), dataverse_identifier)

        return datasets

    def load_datasets_recursive(self, datasets=None, dataverse_identifier=None):
        """Load datasets recursively"""

        if dataverse_identifier is None:
            self.logger.error("Dataverse identifier is required.")
            return

        self.logger.info("Loading dataverse: %s.", dataverse_identifier)

        # Load dataverse
        dataverse_response = self.dataverse_api.get_dataverse(identifier=dataverse_identifier)
        response_json = dataverse_response.json()
        if 'data' in response_json:
            dataverse = response_json['data']

            self.logger.info("Dataverse name: %s", dataverse['name'])

            # Retrieve dv_objects for this dataverse
            dataverse_contents = self.dataverse_api.get_dataverse_contents(
                identifier=dataverse_identifier)
            self.logger.info('Total dv_objects in this dataverse: %s', str(len(dataverse_contents)))
            for dv_object in dataverse_contents:
                if dv_object['type'] == 'dataset':
                    # Add dataset to this dataverse
                    self.logger.info("Adding dataset %s to dataverse %s.",
                                     str(dv_object['id']), str(dataverse_identifier))
                    self.add_dataset(datasets, dataverse_identifier, dv_object['id'],
                                     dv_object['identifier'])
                if dv_object['type'] == 'dataverse':
                    self.logger.info("Found new dataverse %s.", str(dv_object['id']))
                    self.load_datasets_recursive(datasets, dv_object['id'])
        else:
            self.logger.warning('Dataverse was empty.')

    def add_dataset(self, datasets, dataverse_identifier, dataset_id, dataset_identifier):
        """Add dataset"""
        time.sleep(5)

        # Load dataset
        self.logger.info("Dataset id: %s", dataset_id)
        self.logger.info("Dataset identifier: %s", dataset_identifier)
        dataset_response = self.dataverse_api.get_dataset(identifier=dataset_id)
        response_json = dataset_response.json()
        if 'data' in response_json:
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
                        values_string = self.get_value_recursive('', item)
                        if values_string.endswith(' ; '):
                            values_string = values_string[:-len(' ; ')]

                        type_name = item['typeName']
                        dataset[type_name] = values_string

                # Remove nested information
                dataset.pop('latestVersion')

            if self.config['include_dataset_metrics']:
                # Calculate previous month
                last_month = self.get_last_month()

                # Use Make Data Count endpoints to gather views and downloads statistics
                dataset_metrics_options = ['viewsUnique', 'viewsMonth', 'viewsTotal',
                                           'downloadsUnique', 'downloadsMonth', 'downloadsTotal']
                for dataset_metrics_option in dataset_metrics_options:
                    self.logger.debug("Calling endpoint for dataset metric: %s",
                                      dataset_metrics_option)
                    if dataset_metrics_option == 'viewsMonth':
                        dataset_metrics_response = self.dataverse_api.get_dataset_metric(
                            identifier=dataset_id,
                            option='viewsTotal',
                            doi=dataset_identifier,date=last_month)
                    elif dataset_metrics_option == 'downloadsMonth':
                        dataset_metrics_response = self.dataverse_api.get_dataset_metric(
                            identifier=dataset_id,
                            option='downloadsTotal',
                            doi=dataset_identifier,date=last_month)
                    else:
                        dataset_metrics_response = self.dataverse_api.get_dataset_metric(
                            identifier=dataset_id,
                            option=dataset_metrics_option,
                            doi=dataset_identifier)

                    dataset_metrics_json = dataset_metrics_response.json()
                    if dataset_metrics_json['status'] == 'OK':
                        if dataset_metrics_option == 'viewsMonth':
                            if 'viewsTotal' in dataset_metrics_json['data']:
                                self.logger.info("MDC metric (%s): %s", dataset_metrics_option,  str(dataset_metrics_json['data']['viewsTotal']))
                                dataset[dataset_metrics_option] = dataset_metrics_json['data']['viewsTotal']
                            else:
                                self.logger.debug("Unable to find viewsTotal in response.")
                        elif dataset_metrics_option == 'downloadsMonth':
                            if 'downloadsTotal' in dataset_metrics_json['data']:
                                self.logger.info("MDC metric (%s): %s", dataset_metrics_option, str(dataset_metrics_json['data']['downloadsTotal']))
                                dataset[dataset_metrics_option] = dataset_metrics_json['data']['downloadsTotal']
                            else:
                                self.logger.debug("Unable to find downloadsTotal in response.")
                        elif dataset_metrics_option in dataset_metrics_json['data']:
                            self.logger.info("MDC metric (%s): %s", dataset_metrics_option, str(dataset_metrics_json['data'][dataset_metrics_option]))
                            dataset[dataset_metrics_option] = dataset_metrics_json['data'][dataset_metrics_option]
                        else:
                            self.logger.error("Unable to find dataset metric in response: %s",
                                              dataset_metrics_option)
                    else:
                        self.logger.error("API call was unsuccessful.")
                        self.logger.error(dataset_metrics_json)
                        dataset[dataset_metrics_option] = 0

            # Get download count for this dataset from the API
            self.logger.debug("Retrieving download count for dataset: %s", dataset_identifier)
            download_count_response = self.dataverse_api.get_dataset_download_count(
                dataset_identifier=dataset_identifier)
            if download_count_response is not None and 'downloadCount' in download_count_response:
                download_count = download_count_response['downloadCount']
                self.logger.info("Download count for dataset: %s", str(download_count))
                dataset['downloadCount'] = download_count
            else:
                self.logger.warning("Unable to retrieve download count for dataset: %s", dataset_identifier)

            # Use dataverse_database to retrieve cumulative download count of files in this dataset
            file_download_count = self.dataverse_database.get_download_count(dataset_id=dataset_id)
            self.logger.info("File download count for dataset: %s", str(file_download_count))
            dataset['fileDownloads'] = file_download_count

            if 'files' in dataset:
                content_size = 0
                count_restricted = 0
                files = dataset['files']
                for file in files:
                    if 'dataFile' in file:
                        if file['restricted']:
                            count_restricted += 1
                        data_file = file['dataFile']
                        filesize = int(data_file['filesize'])
                        content_size += filesize
                self.logger.info('Totel size (bytes) of all files in this dataset: %s',
                                 str(content_size))
                # Convert to megabytes for reports
                dataset['contentSize (MB)'] = content_size/1048576

                dataset['totalFiles'] = len(files)
                dataset['totalRestrictedFiles'] = count_restricted

            # Retrieve dataverse to get alias
            dataverse_response = self.dataverse_api.get_dataverse(identifier=dataverse_identifier)
            response_json = dataverse_response.json()
            dataverse = response_json['data']

            self.logger.info("Adding dataset to dataverse with alias: %s", str(dataverse['alias']))
            dataset['dataverse'] = dataverse['alias']
            datasets.append(dataset)
        else:
            self.logger.warning('Dataset was empty.')

        self.logger.info("Finished adding dataset: %s", dataset_identifier)

    def get_value_recursive(self, values_string, field):
        """Get metadata value recursively"""

        if not field['multiple']:
            if field['typeClass'] == 'primitive':
                values_string += field['value']
                self.logger.debug("New value of values_string: %s", str(values_string))
                return values_string
            elif field['typeClass'] == 'controlledVocabulary':
                sub_value = ''
                for value in field['value']:
                    sub_value += value + ', '
                sub_value = sub_value[:-2]
                values_string += sub_value
                self.logger.debug("New value of values_string: %s", str(values_string))
                return values_string
            elif field['typeClass'] == 'compound':
                self.logger.debug("Looking at single compound field...")
                sub_value = ''
                if isinstance(field['value'], list):
                    for value in field['value']:
                        compound_value = self.create_compound_value(value)
                        if compound_value.endswith(' - '):
                            compound_value = compound_value[:-len(' - ')]
                        self.logger.debug("New compound_value: %s", compound_value)

                        values_string += compound_value + " ; "
                else:
                    self.logger.debug("Compound field has single value")
                    value = field['value']

                    compound_value = self.create_compound_value(value)
                    if compound_value.endswith(' - '):
                        compound_value = compound_value[:-len(' - ')]
                    self.logger.debug("New compound_value: %s", compound_value)

                    values_string += compound_value + " ; "

                if values_string.endswith(' ; '):
                    values_string = values_string[:-len(' ; ')]
                self.logger.debug("New value of values_string: %s", str(values_string))
                return values_string
            else:
                self.logger.debug("Unrecognized typeClass: %s", field['typeClass'])
        else:
            if field['typeClass'] == 'primitive':
                sub_value = ''
                for value in field['value']:
                    sub_value += value + ', '
                sub_value = sub_value[:-2]
                values_string += sub_value
                self.logger.debug("New value of values_string: %s", str(values_string))
                return values_string
            elif field['typeClass'] == 'controlledVocabulary':
                sub_value = ''
                for value in field['value']:
                    sub_value += value + ', '
                sub_value = sub_value[:-2]
                values_string += sub_value
                self.logger.debug("New value of values_string: %s", str(values_string))
                return values_string
            elif field['typeClass'] == 'compound':
                self.logger.debug("Looking at multiple compound field...")
                compound_value = ''
                if isinstance(field['value'], list):
                    for value in field['value']:
                        compound_value = self.create_compound_value(value)
                        if compound_value.endswith(' - '):
                            compound_value = compound_value[:-len(' - ')]
                        self.logger.debug("New compound_value: %s", compound_value)

                        values_string += compound_value + " ; "
                else:
                    self.logger.debug("Compound field has single value")
                    value = field['value']

                    compound_value = self.create_compound_value(value)
                    if compound_value.endswith(' - '):
                        compound_value = compound_value[:-len(' - ')]
                    self.logger.debug("New compound_value: %s", compound_value)

                    values_string += compound_value + " ; "

                if values_string.endswith(' ; '):
                    values_string = values_string[:-len(' ; ')]
                self.logger.debug("New value of values_string: %s", str(values_string))
                return values_string
            else:
                self.logger.debug("Unrecognized typeClass: %s", field['typeClass'])

    def create_compound_value(self, fields):
        """Create compound value"""

        self.logger.debug("Creating compound string...")

        compound_value = ''
        for key, elements in fields.items():
            if isinstance(elements['value'], str):
                compound_value += elements['value'] + " - "
            else:
                self.logger.error("Compound object contains field with mulitple values.")

            self.logger.info("New compound value: %s", compound_value)

        if compound_value.endswith(' - '):
            compound_value = compound_value[:-len(' - ')]

        self.logger.debug("Final compound string: %s", compound_value)
        return compound_value

    def get_last_month(self):
        """Get last month"""

        now = datetime.datetime.now()
        previous = now.date().replace(day=1) - datetime.timedelta(days=1)
        last_month = previous.strftime("%Y-%m")
        return last_month
