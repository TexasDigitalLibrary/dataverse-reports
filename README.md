# dataverse-reports
A python3-based tool to generate and email statistical reports from Dataverse (https://dataverse.org/) using the native API and database queries.

As with Miniverse (https://github.com/IQSS/miniverse), the reports require access to the Dataverse database.

Configuration
-----

```bash
$ cp config/application.yml.sample config/application.yml
```

Example
```yaml
dataverse_api_host: ''
dataverse_api_key: ''
dataverse_db_host: ''
dataverse_db_username: ''
dataverse_db_password: ''
work_dir: '/tmp'
log_path: 'logs'
log_file: 'dataverse-reports.log'
log_level: 'INFO'
from_email: ''
admin_emails:
        - email1
        - email2
from_email: ''
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

Set parameters for API and database connections. Accounts list refers to top-level dataverses on which reports based at the institutional level will begin.

NOTE: The accounts section can be left blank if your Dataverse instance is not set up with separate institutions as top-level dataverses. In that case, your reports will be for everything from the root dataverse on down and sent to all admins.


Virtual Environment Setup
-----
```bash
pip install virtualenv
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
```

NOTE: In some Linux environments pip will not install the underlying requirements for psycopg2 and PyYAML. If you see errors related to these packages at runtime, then run `easy_install psycopg2` and `easy_install PyYAML`.


Usage
-----
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

<h5>Launch virtual environment</h5>

```bash
$ source venv/bin/activate
```

<h5>Sample commands run inside the virtual environment.</h5>

Generate and email a report of all dataverses, datasets and users for super admin(s).
```bash
$ python run.py -c config/application.yml -r all -g all -o $HOME/reports -e
```

Generate and email reports of dataverses for each institution beginning at a top-level dataverse.
```bash
$ python run.py -c config/application.yml -r dataverse -g institutions -o $HOME/reports -e
```

Generate and email a report of all datasets for super admin(s).
```bash
$ python run.py -c config/application.yml -r dataset -g all -o $HOME/reports -e
```

Generate and email reports of users for each institution beginning at a top-level dataverse.
```bash
$ python run.py -c config/application.yml -r user -g institutions -o $HOME/reports -e
```
