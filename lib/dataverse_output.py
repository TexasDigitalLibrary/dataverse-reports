"""Class for output functions"""

import os
import csv
import logging
import xlsxwriter


class DataverseOutput:
    """Class for output functions"""

    def __init__(self, config=None):
        self.config = config
        self.logger = logging.getLogger('dataverse-reports')

    def save_report_csv_file(self, output_file_path=None, headers=None, data=None):
        """Save report to CSV file"""

        # Sanity checks
        if output_file_path is None:
            self.logger.error("Output file path is required.")
            return False
        if headers is None:
            self.logger.error("Report headers are required.")
            return False
        if not self.ensure_directory_exists(output_file_path):
            self.logger.error("Output directory doesn't exist and can't be created.")
            return False

        if data is not None:
            with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore',
                                        dialect='excel', quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
                for result in data:
                    writer.writerow(result)

            self.logger.info("Saved report to CSV file %s.", output_file_path)
            return output_file_path

        return None

    def save_report_excel_file(self, output_file_path=None, worksheet_files=None):
        """Save report to Excel file"""

        # Sanity checks
        if output_file_path is None:
            self.logger.error("Output file path is required.")
            return False
        if worksheet_files is None or len(worksheet_files) == 0:
            self.logger.error("Worksheets files list is empty.")
            return False
        if not self.ensure_directory_exists(output_file_path):
            self.logger.error("Output directory doesn't exist and can't be created.")
            return False

        # Create Excel workbook
        self.logger.info("Creating Excel file: %s", output_file_path)
        workbook = xlsxwriter.Workbook(output_file_path, {'strings_to_numbers': True})

        # Add worksheet(s)
        for worksheet_file in worksheet_files:
            # Get worksheet title from filename
            filename_w_ext = os.path.basename(worksheet_file)
            filename, file_extension = os.path.splitext(filename_w_ext)
            filename_parts = filename.split("-")
            if len(filename_parts) == 2:
                workbook_name = filename_parts[1]
            else:
                workbook_name = filename

            worksheet = workbook.add_worksheet(workbook_name)
            worksheet.freeze_panes(1, 0)
            with open(worksheet_file, 'rt', encoding='utf8') as f:
                reader = csv.reader(f)
                for r, row in enumerate(reader):
                    for c, col in enumerate(row):
                        worksheet.write(r, c, col)

        workbook.close()

        self.logger.info("Saved report to Excel file %s.", output_file_path)
        return output_file_path

    def ensure_directory_exists(self, output_file_path=None):
        """Ensure directory exists"""

        if output_file_path is None:
            self.logger.warning('Output file path is empty.')
            return False

        directory = os.path.dirname(output_file_path)

        if os.path.isdir(directory) and os.path.exists(directory):
            return True

        os.mkdir(directory)
        return True
