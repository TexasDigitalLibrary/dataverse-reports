"""Class for email functions"""

import os
import smtplib
import logging
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

class DataverseEmail:
    """Class for email functions"""

    def __init__(self, config=None):
        self.config = config
        self.logger = logging.getLogger('dataverse-reports')

    def email_report_institution(self, report_file_paths=None, account_info=None):
        """Email reports to institutions"""

        if report_file_paths is None or len(report_file_paths) == 0:
            self.logger.error('At least one report file path is required.')
            return

        # Construct email information
        subject = 'Dataverse reports for ' + account_info['name']
        from_email = self.config['from_email']
        body = "The report in Excel format is attached."

        # Send email(s) to contact(s)
        if account_info is not None:
            for contact in account_info['contacts']:
                self.logger.info("Sending report to %s.", contact)
                self.email_report_internal(report_file_paths=report_file_paths,
                                        to_email=contact, from_email=from_email,
                                        subject=subject, body=body)

    def email_report_admin(self, report_file_paths=None):
        """Email reports to admins"""

        if report_file_paths is None or len(report_file_paths) == 0:
            self.logger.error('At least one report file path is required.')
            return

        # Construct email information
        subject = 'Dataverse reports for ' + self.config['dataverse_name']
        from_email = self.config['from_email']
        body = "The reports in Excel format are attached."

        # Send email(s) to admin email address(es)
        for admin_email in self.config['admin_emails']:
            self.logger.info("Sending reports to admin %s.", admin_email)
            self.email_report_internal(report_file_paths=report_file_paths,
                                       to_email=admin_email, from_email=from_email,
                                       subject=subject, body=body)


    def email_report_internal(self, report_file_paths=None, to_email=None,
                              from_email=None, subject=None, body=None):
        """Internal email report function"""

        if report_file_paths is None or len(report_file_paths) == 0:
            self.logger.error("At least one report file path is required.")
            return None
        if to_email is None or from_email is None or subject is None or body is None:
            self.logger.error("Required email information is missing.")
            return None

        # Create message with text fields
        message = MIMEMultipart()
        message['Subject'] = subject
        message['To'] = to_email
        message['From'] = from_email
        message.attach(MIMEText(body, 'plain'))

        # Attach report file(s)
        for report_file_path in report_file_paths:
            # Check that report file exists
            if not os.path.isfile(report_file_path):
                self.logger.warning("Report file doesn't exist: %s.", report_file_path)
                continue

            path, report_file_name = os.path.split(report_file_path)
            attachment = open(report_file_path, "rb")

            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {report_file_name}")
            message.attach(part)

        # Get SMTP configuration
        dataverse_smtp_config = self.config['smtp']
        smtp_host = dataverse_smtp_config['host']
        smtp_auth = dataverse_smtp_config['auth']
        smtp_port = dataverse_smtp_config['port']
        smtp_username = dataverse_smtp_config['username']
        smtp_password = dataverse_smtp_config['password']

        # Send email
        self.logger.info("Sending Dataverse report to %s.", to_email)
        server = smtplib.SMTP(smtp_host, smtp_port)
        if smtp_auth == 'tls':
            server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.send_message(message)
        server.quit()

        return True
