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
from lib.output import Output
from lib.email import Email

from reports.dataverse import DataverseReports
from reports.dataset import DatasetReports
from reports.user import UserReports


def main():
    parser = OptionParser()

    parser.add_option("-c", "--config", dest="config_file", default="config/application.yml", help="Configuration file")
    parser.add_option("-r", "--report(s)", dest="reports", default='all', help="Report type(s) to generate. Options = dataverse, dataset, user, all.")
    parser.add_option("-g", "--group", dest="grouping", help="Grouping of results. Options = institutions, all")
    parser.add_option("-o", "--output_dir", dest="output_dir", help="Directory for results files.")
    parser.add_option("-e", "--email", action="store_true", dest="email", default=False, help="Email reports to liaisons?")

    (options, args) = parser.parse_args()

    # Check required options fields
    if options.reports != 'all' and options.reports != 'dataverse' and options.reports != 'dataset' and options.reports != 'user':
        parser.print_help()
        parser.error("Must specify report type(s) from the following options: dataverse, dataset, user, or all.")

    if options.grouping != 'all' and options.grouping != 'institutions':
        parser.print_help()
        parser.error("Must specify report grouping from the following options: all, institutions.")

    if options.output_dir is None:
        parser.print_help()
        parser.error("Must specify an output directory.")

    # Load config
    print("Loading configuration from file: %s", options.config_file)
    config = load_config(options.config_file)
    if not config:
        print("Unable to load configuration.")
        sys.exit(0)

    # Set up logging
    logger = load_logger(config=config)

    # Ensure work_dir has trailing slash
    work_dir = config['work_dir']
    if work_dir[len(work_dir)-1] != '/':
        work_dir = work_dir + '/'

    # Ensure output_dir has trailing slash
    output_dir = options.output_dir
    if output_dir[len(output_dir)-1] != '/':
        output_dir = output_dir + '/'

    # Ensure output_dir exists
    ensure_directory_exists(output_dir, logger)

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

    # Dataverse fieldnames for CSV reports
    root_fieldnames = ['alias', 'name', 'id', 'affiliation', 'dataverseType', 'creationDate']
    creator_fieldnames = ['creatorIdentifier', 'creatorName', 'creatorEmail', 'creatorAffiliation', 'creatorPosition']
    sword_fieldnames = ['released']
    dataverse_fieldnames = root_fieldnames + creator_fieldnames + sword_fieldnames

    # Dataset fieldnames for CSV reports
    root_fieldnames = ['dataverse', 'id', 'identifier', 'persistentUrl', 'protocol', 'authority', 'publisher', 'publicationDate']
    latest_fieldnames = ['versionState', 'lastUpdateTime', 'releaseTime', 'createTime', 'license', 'termsOfUse']
    metadata_fieldnames = ['title', 'author', 'datasetContact', 'dsDescription', 'notesText', 'subject', 'productionDate', 'productionPlace', 'depositor', 'dateOfDeposit']
    database_fieldnames = ['downloadCount']
    files_fieldnames = ['contentSize (MB)', 'totalFiles', 'totalRestrictedFiles']
    dataset_metrics_fieldnames = []
    if (config['include_dataset_metrics']):
        dataset_metrics_fieldnames = ['viewsUnique', 'viewsTotal','downloadsUnique', 'downloadsTotal']
    dataset_fieldnames = root_fieldnames + latest_fieldnames + metadata_fieldnames + database_fieldnames + files_fieldnames + dataset_metrics_fieldnames

    # User fieldnames for CSV reports
    creator_fieldnames = ['id', 'identifier', 'displayName', 'firstName', 'lastName', 'email', 'superuser', 'affiliation', 'position', 'persistentUserId', 'createdTime', 'lastLoginTime']
    user_fieldnames = creator_fieldnames

    # Create dataverse reports object
    dataverse_reports = DataverseReports(dataverse_api=dataverse_api, config=config)

    # Create datasets reports object
    dataset_reports = DatasetReports(dataverse_api=dataverse_api, dataverse_database=dataverse_database, config=config)

    # Create user reports object
    user_reports = UserReports(dataverse_api=dataverse_api, config=config)

    # Create output object
    output = Output(config=config)

    # Create email object
    email = Email(config=config)

    # Start reports
    logger.info("Started creating reports...")
    
    # Check for any configured accounts
    if 'accounts' in config and config['accounts'] is not None and len(config['accounts']) > 0:
        # Group reports by institution or all together
        if options.grouping == 'all':
            # Store list of Excel report(s)
            excel_reports = []

            for key in config['accounts']:
                account_info = config['accounts'][key]
                logger.info("Generating reports for %s.",  account_info['name'])

                # Generate CSV report(s) based on command line option
                csv_reports = []

                if options.reports == 'dataverse':
                    dv_report = dataverse_reports.report_dataverses_recursive(dataverse_identifier=account_info['identifier'])
                    dv_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-dataverses.csv', headers=dataverse_fieldnames, data=dv_report)
                    csv_reports.append(dv_report_file)
                elif options.reports == 'dataset':
                    ds_report = dataset_reports.report_datasets_recursive(dataverse_identifier=account_info['identifier'])
                    # Only save report if there are datasets
                    if ds_report is not None:
                        ds_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-datasets.csv', headers=dataset_fieldnames, data=ds_report)
                        csv_reports.append(ds_report_file)
                elif options.reports == 'user':
                    user_report = user_reports.report_users_recursive(dataverse_identifier=account_info['identifier'])
                    # Only save report if there are users
                    if user_report is not None:
                        user_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-users.csv', headers=user_fieldnames, data=user_report)
                        csv_reports.append(user_report_file)
                else:   # Default option is all reports
                    dv_report = dataverse_reports.report_dataverses_recursive(dataverse_identifier=account_info['identifier'])
                    dv_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-dataverses.csv', headers=dataverse_fieldnames, data=dv_report)
                    csv_reports.append(dv_report_file)

                    ds_report = dataset_reports.report_datasets_recursive(dataverse_identifier=account_info['identifier'])
                    ds_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-datasets.csv', headers=dataset_fieldnames, data=ds_report)
                    csv_reports.append(ds_report_file)

                    user_report = user_reports.report_users_recursive(dataverse_identifier=account_info['identifier'])
                    user_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-users.csv', headers=user_fieldnames, data=user_report)
                    csv_reports.append(user_report_file)

                # Combine CSV report(s) to an Excel spreadsheet
                if len(csv_reports) > 0:
                    output_file_path = output_dir + account_info['identifier'] + '-dataverse-reports.xlsx'
                    excel_report_file = output.save_report_excel_file(output_file_path=output_file_path, worksheet_files=csv_reports)
                    if excel_report_file:
                        logger.info("Finished saving Excel file to %s.", excel_report_file)
                        excel_reports.append(excel_report_file)
                    else:
                        logger.error("There was an error saving the Excel file.")

            if options.email:
                logger.info("Sending email to super admin with the report.")
                email.email_report_admin(report_file_paths=excel_reports)

        elif options.grouping == 'institutions':
            for key in config['accounts']:
                account_info = config['accounts'][key]
                logger.info("Generating reports for %s.",  account_info['name'])

                # Generate CSV report(s) based on command line option
                csv_reports = []

                if options.reports == 'dataverse':
                    dv_report = dataverse_reports.report_dataverses_recursive(dataverse_identifier=account_info['identifier'])
                    dv_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-dataverses.csv', headers=dataverse_fieldnames, data=dv_report)
                    csv_reports.append(dv_report_file)
                elif options.reports == 'dataset':
                    ds_report = dataset_reports.report_datasets_recursive(dataverse_identifier=account_info['identifier'])
                    # Only save report if there are datasets
                    if ds_report is not None:
                        ds_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-datasets.csv', headers=dataset_fieldnames, data=ds_report)
                        csv_reports.append(ds_report_file)
                elif options.reports == 'user':
                    user_report = user_reports.report_users_recursive(dataverse_identifier=account_info['identifier'])
                    # Only save report if there are users
                    if user_report is not None:
                        user_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-users.csv', headers=user_fieldnames, data=user_report)
                        csv_reports.append(user_report_file)
                else:   # Default option is all reports
                    dv_report = dataverse_reports.report_dataverses_recursive(dataverse_identifier=account_info['identifier'])
                    dv_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-dataverses.csv', headers=dataverse_fieldnames, data=dv_report)
                    csv_reports.append(dv_report_file)

                    ds_report = dataset_reports.report_datasets_recursive(dataverse_identifier=account_info['identifier'])
                    ds_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-datasets.csv', headers=dataset_fieldnames, data=ds_report)
                    csv_reports.append(ds_report_file)

                    user_report = user_reports.report_users_recursive(dataverse_identifier=account_info['identifier'])
                    user_report_file = output.save_report_csv_file(output_file_path=work_dir + account_info['identifier'] + '-users.csv', headers=user_fieldnames, data=user_report)
                    csv_reports.append(user_report_file)

                # Combine CSV report(s) to an Excel spreadsheet
                if len(csv_reports) > 0:
                    output_file_path = output_dir + account_info['identifier'] + '-dataverse-reports.xlsx'
                    excel_report_file = output.save_report_excel_file(output_file_path=output_file_path, worksheet_files=csv_reports)
                    if excel_report_file:
                        logger.info("Finished saving Excel file to %s.", excel_report_file)
                        if options.email:
                            logger.info("Sending email to institutional liaison with the report.")
                            email.email_report_institution(report_file_paths=[excel_report_file], account_info=account_info)
                    else:
                        logger.error("There was an error saving the Excel file.")
        else:
            logger.error("Unrecognized report grouping: %s.", options.grouping)
    else:
        # Start generating reports at the root dataverse 
        logger.info('Generating reports from the root dataverse')
        # Generate CSV report(s) based on command line option
        csv_reports = []

        if options.reports == 'dataverse':
            dv_report = dataverse_reports.report_dataverses_recursive(dataverse_identifier='root')
            dv_report_file = output.save_report_csv_file(output_file_path=work_dir + 'dataverses.csv', headers=dataverse_fieldnames, data=dv_report)
            csv_reports.append(dv_report_file)
        elif options.reports == 'dataset':
            ds_report = dataset_reports.report_datasets_recursive(dataverse_identifier='root')
            # Only save report if there are datasets
            if ds_report is not None:
                ds_report_file = output.save_report_csv_file(output_file_path=work_dir + 'datasets.csv', headers=dataset_fieldnames, data=ds_report)
                csv_reports.append(ds_report_file)
        elif options.reports == 'user':
            user_report = user_reports.report_users_recursive(dataverse_identifier='root')
            # Only save report if there are users
            if user_report is not None:
                user_report_file = output.save_report_csv_file(output_file_path=work_dir + 'users.csv', headers=user_fieldnames, data=user_report)
                csv_reports.append(user_report_file)
        else:   # Default option is all reports
            dv_report = dataverse_reports.report_dataverses_recursive(dataverse_identifier='root')
            dv_report_file = output.save_report_csv_file(output_file_path=work_dir + 'dataverses.csv', headers=dataverse_fieldnames, data=dv_report)
            csv_reports.append(dv_report_file)

            ds_report = dataset_reports.report_datasets_recursive(dataverse_identifier='root')
            ds_report_file = output.save_report_csv_file(output_file_path=work_dir + 'datasets.csv', headers=dataset_fieldnames, data=ds_report)
            csv_reports.append(ds_report_file)

            user_report = user_reports.report_users_recursive(dataverse_identifier='root')
            user_report_file = output.save_report_csv_file(output_file_path=work_dir + 'users.csv', headers=user_fieldnames, data=user_report)
            csv_reports.append(user_report_file)

        # Combine CSV report(s) to an Excel spreadsheet
        if len(csv_reports) > 0:
            # Store list of Excel report(s)
            excel_reports = []

            output_file_path = output_dir +  'dataverse-reports.xlsx'
            excel_report_file = output.save_report_excel_file(output_file_path=output_file_path, worksheet_files=csv_reports)
            if excel_report_file:
                logger.info("Finished saving Excel file to %s.", excel_report_file)
                excel_reports.append(excel_report_file)
            else:
                logger.error("There was an error saving the Excel file.")

        if options.email:
            logger.info("Sending email to super admin with the report.")
            email.email_report_admin(report_file_paths=excel_reports)


    logger.info("Finished processing reports.")

def load_config(config_file):
    config = {}
    path = config_file

    if not path or not os.path.isfile(path):
        print('Configuration file is missing.')
        return False

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    return config

def load_logger(config=None):
    if config is None:
        print('No configuration given, cannot create logger.')
        return False

    # Set variables
    log_path = config['log_path'] or 'logs/'
    if log_path[len(log_path)-1] != '/':
        log_path = log_path + '/'

    log_file = config['log_file'] or 'dataverse-reports.log'

    log_level_string = config['log_level'] or 'INFO'
    if log_level_string == 'INFO':
        log_level = logging.INFO
    elif log_level_string == 'DEBUG':
        log_level = logging.DEBUG
    elif log_level_string == 'WARNING':
        log_level = logging.WARNING
    elif log_level_string == 'ERROR':
        log_level = logging.ERROR
    else:
        log_level = logging.INFO

    # Create logger
    logger = logging.getLogger('dataverse-reports')
    logger.setLevel(log_level)
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")

    file_handler = logging.FileHandler("{0}/{1}".format(log_path, log_file))
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    return logger

def ensure_directory_exists(output_file_path=None, logger=None):
    if output_file_path is None:
        if logger:
            logger.warning('Output file path is empty.')
        return False

    directory = os.path.dirname(output_file_path)

    if os.path.isdir(directory) and os.path.exists(directory):
        return True
    else:
        os.mkdir(directory)
        return True

if __name__ == "__main__":
    main()
