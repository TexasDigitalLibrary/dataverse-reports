import os
import csv
import xlsxwriter
import logging


class Output(object):
    def __init__(self, config=None):
        self.config = config
        self.logger = logging.getLogger('dataverse-reports')

    def save_report_csv_file(self, output_file_path=None, headers=[], data=[]):
        # Sanity checks
        if output_file_path is None:
            self.logger.error("Output file path is required.")
            return False
        if not headers:
            self.logger.error("Report headers are required.")
            return False
        if not self.ensure_directory_exists(output_file_path):
            self.logger.error("Output directory doesn't exist and can't be created.")
            return False

        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore', dialect='excel', quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            for result in data:
                writer.writerow(result)

        self.logger.info("Saved report to CSV file %s.", output_file_path)
        return output_file_path

    def save_report_excel_file(self, output_file_path=None, worksheet_files=[]):
        # Sanity checks
        if output_file_path is None:
            self.logger.error("Output file path is required.")
            return False
        if len(worksheet_files) == 0:
            self.logger.error("Worksheets files list is empty.")
            return False
        if not self.ensure_directory_exists(output_file_path):
            self.logger.error("Output directory doesn't exist and can't be created.")
            return False

        # Create Excel workbook
        self.logger.info("Creating Excel file: %s", output_file_path)
        workbook = xlsxwriter.Workbook(output_file_path)

        # Add worksheet(s)
        for worksheet_file in worksheet_files:
            # Get worksheet title from filename
            filename_w_ext = os.path.basename(worksheet_file)
            filename, file_extension = os.path.splitext(filename_w_ext)
            filename_parts = filename.split("-")
            if len(filename_parts) == 2:
                workbook_name = filename_parts[1]
            else:
                workbook_name = ''

            worksheet = workbook.add_worksheet(workbook_name)
            with open(worksheet_file, 'rt', encoding='utf8') as f:
                reader = csv.reader(f)
                for r, row in enumerate(reader):
                    for c, col in enumerate(row):
                        worksheet.write(r, c, col)

        workbook.close()

        self.logger.info("Saved report to Excel file %s.", output_file_path)
        return output_file_path

    def ensure_directory_exists(self, output_file_path=None):
        if output_file_path is None:
            self.logger.warning('Output file path is empty.')
            return False

        directory = os.path.dirname(output_file_path)

        if os.path.isdir(directory) and os.path.exists(directory):
            return True
        else:
            os.mkdir(directory)
            return True
