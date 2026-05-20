# dataverse-reports

A Python tool to generate and email statistical reports from [Dataverse](https://dataverse.org/) using the native API and database queries.

## Requirements

- Python 3.12+
- Dataverse 5.1+

## Python Virtual Environment Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

```bash
cp config/application.yml.sample config/application.yml
```

### Example

```yaml
dataverse_name: 'My data repository'
api:
     host: 'http://localhost:8080'
     token: 'sample_key'
     timeout: 60
database:
     host: 'localhost'
     port: 5432
     name: 'dataverse'
     username: 'db_user'
     password: 'db_password'
smtp:
     host: 'localhost'
     auth: ''
     port: 25
     username: 'username'
     password: 'password'
include_dataset_metrics: false
work_dir: '/tmp'
log_path: 'logs'
log_file: 'dataverse-reports.log'
log_level: 'INFO'
from_email: ''
admin_emails:
        - email1
        - email2
accounts:
     account1:
          name: Account 1
          identifier: account1_identifier
          contacts:
               - email1
               - email2
     account2:
          name: Account 2
          identifier: account2_identifier
          contacts:
               - email1
```

Set parameters for API and database connections, as well as the SMTP configuration. Accounts list refers to top-level dataverses on which reports based at the institutional level will begin.

NOTE: The accounts section can be left blank if your Dataverse instance is not set up with separate institutions as top-level dataverses. In that case, your reports will be for everything from the root dataverse on down and sent to all admins.

## Usage

**NOTE: All of the following commands assume that the user is in the virtual environment.**

```bash
Usage: run.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config=CONFIG_FILE
                        Configuration file
  -r REPORTS, --report(s)=REPORTS
                        Report type(s) to generate. Options = dataverse,
                        dataset, user, all.
  -g GROUPING, --group=GROUPING
                        Grouping of results. Options = institutions, all
  -o OUTPUT_DIR, --output_dir=OUTPUT_DIR
                        Directory for results files.
  -e, --email           Email reports to liaisons?
```

### Sample commands

- Generate and email a report of all dataverses, datasets and users for super admin(s).

```bash
python run.py -c config/application.yml -r all -g all -o $HOME/reports -e
```

- Generate and email reports of dataverses for each institution beginning at a top-level dataverse.

```bash
python run.py -c config/application.yml -r dataverse -g institutions -o $HOME/reports -e
```

- Generate and email a report of all datasets for super admin(s).

```bash
python run.py -c config/application.yml -r dataset -g all -o $HOME/reports -e
```

- Generate and email reports of users for each institution beginning at a top-level dataverse.

```bash
python run.py -c config/application.yml -r user -g institutions -o $HOME/reports -e
```
