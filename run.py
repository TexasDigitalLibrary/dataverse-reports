import os
import sys
import json
import yaml
import csv
import pprint
import smtplib
import logging
import mimetypes
from optparse import OptionParser
from email.message import EmailMessage

from lib.api import DataverseApi
from lib.database import DataverseDatabase
from reports.dataverse import DataverseReports
from reports.dataset import DatasetReports


def main():
    parser = OptionParser()

    parser.add_option("-c", "--config", dest="config_file", default="config/application.yml", help="Configuration file")
    parser.add_option("-r", "--report", dest="report", help="Report to generate. Options = dataverse, dataset")
    parser.add_option("-g", "--group", dest="grouping", help="Grouping of results. Options = all, institutions")

    (options, args) = parser.parse_args()

    # Check required options fields
    if options.report != 'dataverse' and options.report != 'dataset':
        parser.print_help()
        parser.error("Must specify report from the following options: dataverse, dataset.")

    if options.grouping != 'all' and options.grouping != 'institutions':
        parser.print_help()
        parser.error("Must specify report grouping from the following options: all, institutions.")

    # Set up logging
    log_level = logging.INFO
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
    log_path = 'logs/'
    log_file = 'dataverse-reports.log'
    logger = logging.getLogger('dataverse-reports')
    logger.setLevel(log_level)

    file_handler = logging.FileHandler("{0}/{1}".format(log_path, log_file))
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    logger.info("Loading config from %s.", options.config_file)
    config = load_config(options.config_file)

    logger.info("Started creating reports.")

    # Create Dataverse API object test the connection
    dataverse_api = DataverseApi(host=config['dataverse_api_host'], token=config['dataverse_api_key'])
    if dataverse_api.test_connection() is False:
        logger.error("Cannot create reports because the connection to the Dataverse API failed.")
        sys.exit(0)

    # Create Dataverse database object and test the connection
    dataverse_database = DataverseDatabase(host=config['dataverse_db_host'], database=config['dataverse_db_name'], username=config['dataverse_db_username'], password=config['dataverse_db_password'])
    if dataverse_database.create_connection() is False:
        logger.error("Cannot create reports because the connection to the Dataverse database failed.")
        sys.exit(0)

    # Act based on report type and grouping
    if options.report == 'dataverse':
        logger.info('Creating dataverse reports.')

        # Create dataverse reports object
        dataverse_reports = DataverseReports(dataverse_api=dataverse_api, config=config)

        if options.grouping == 'all':
            dataverse_reports.generate_reports('all')
        elif options.grouping == 'institutions':
            dataverse_reports.generate_reports('institutions')
        else:
            logger.error("Unrecognized report grouping: %s.", options.grouping)
    elif options.report == 'dataset':
        logger.info('Creating dataset reports.')

        # Create datasets reports object
        dataset_reports = DatasetReports(dataverse_api=dataverse_api, dataverse_database=dataverse_database, config=config)

        if options.grouping == 'all':
            dataset_reports.generate_reports('all')
        elif options.grouping == 'institutions':
            dataset_reports.generate_reports('institutions')
        else:
            logger.error("Unrecognized report grouping: %s.", options.grouping)
    else:
        logger.error("Unrecognized report type: %s.", options.report)

    logger.info("Finished processing reports.")


def load_config(config_file):
    config = {}
    path = config_file

    if not path or not os.path.isfile(path):
        return {}

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    return config

if __name__ == "__main__":
    main()
