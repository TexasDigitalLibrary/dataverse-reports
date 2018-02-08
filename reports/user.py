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

        # API fields used in reports
        creator_fieldnames = ['id', 'displayName', 'firstName', 'lastName', 'email', 'superuser', 'affiliation', 'position', 'persistentUserId', 'createdTime', 'lastLoginTime']
        self.fieldnames = creator_fieldnames

        self.logger = logging.getLogger('dataverse-reports')

    def generate_reports(self, type='all'):
        if type == 'all':
            self.logger.info("Generating report of all users for super admin.")
            self.report_users_admin_recursive()
        elif type == 'institutions':
            self.logger.info("Generating report of users for each institution.")
            for key in self.config['accounts']:
                account_info = self.config['accounts'][key]

                self.logger.info("Generating recursive report for %s.", account_info['name'])
                self.report_users_recursive(account_info)

    def report_users_admin_recursive(self):
        # List of Users
        users = []
        report_file_paths = []

        for key in self.config['accounts']:
            account_info = self.config['accounts'][key]
            self.logger.info("Generating user report for %s.", account_info['identifier'])
            self.load_users_recursive(users, account_info['identifier'])

            # Get unique list of users
            users = list({v['id']:v for v in users}.values())

            if len(users) > 0:
                # Write results to CSV file
                output_file = account_info['identifier'] + '-users.csv'
                self.save_report(output_file_path=self.config['work_dir'] + output_file, headers=self.fieldnames, data=users)

                # Add file to reports list
                report_file_paths.append(self.config['work_dir'] + output_file)

            # Reset list
            users = []

        # Send results to admin email addresses
        if len(report_file_paths) > 0:
            self.email_report_admin(report_file_paths=report_file_paths)

    def report_users_recursive(self, account_info):
        # List of Users
        users = []

        self.logger.info("Begin loading users for %s.", account_info['identifier'])
        self.load_users_recursive(users, account_info['identifier'])
        self.logger.info("Finished loading %s users for %s", str(len(users)), account_info['identifier'])

        # Get unique list of users
        users = list({v['id']:v for v in users}.values())

        if len(users) > 0:
            # Write results to CSV file
            output_file = account_info['identifier'] + '-users.csv'
            self.save_report(output_file_path=self.config['work_dir'] + output_file, headers=self.fieldnames, data=users)

            # Send results to contacts list
            self.email_report_institution(report_file_paths=[self.config['work_dir'] + output_file], account_info=account_info)

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
        dataverse = response_json['data']
        self.logger.info("Dataverse name: %s", dataverse['name'])

        # Add creator information
        if 'creator' in dataverse:
            creator = dataverse['creator']
            self.logger.debug("Adding user of dataverse: %s", creator['displayName'])
            users.append(creator)

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
        subject = 'User report for ' + account_info['name']
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
        subject = 'User reports for ' + self.config['dataverse_api_host']
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
        self.logger.info("Sending user report to %s.", to_email)
        with smtplib.SMTP('localhost') as s:
            s.send_message(message)
