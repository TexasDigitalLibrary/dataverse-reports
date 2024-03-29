import logging


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

        self.logger = logging.getLogger('dataverse-reports')

        self.all_users = self.load_all_users_list()

    def load_all_users_list(self):
        # List of all users
        all_users = []

        self.logger.info("Retrieving all Dataverse users...")
        current_page = 1
        users_count = 0

        while True:
            users_list_response = self.dataverse_api.get_admin_list_users(page=current_page)
            if users_list_response['status'] == 'OK':
                users_list_data = users_list_response['data']
                all_users = all_users + users_list_data['users']
                users_count = users_list_data['userCount']
                total_pages = users_list_data['pagination']['pageCount']
                if current_page == total_pages:
                    break
                current_page += 1
            else:
                break
        
        self.logger.info("Loaded " + str(len(all_users)) + " users.")
        if len(all_users) != users_count:
            self.logger.warn("Unable to load all users: " + str(users_count))
        
        return all_users

    def find_user_email(self, email):
        user = {}

        email_lower = email.casefold()

        for u in self.all_users:
            if 'email' in u and email_lower == u['email'].casefold():
                user = u

        return user

    def report_users_recursive(self, dataverse_identifier):
        # List of users
        users = []

        self.logger.info("Begin loading users for %s.", dataverse_identifier)
        self.load_users_recursive(users, dataverse_identifier)
        self.logger.info("Finished loading %s users for %s", str(len(users)), dataverse_identifier)

        # Get unique list of users
        users = list({v['id']:v for v in users}.values())

        return users

    def load_users_recursive(self, users={}, dataverse_identifier=None):
        if dataverse_identifier is None:
            self.logger.error("Dataverse identifier is required.")
            return

        self.logger.info("Loading dataverse: %s.", dataverse_identifier)

        # Add user to list
        self.logger.info('Adding contact of dataverse to report: %s', dataverse_identifier)
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
        # Vars
        new_user = {}

        # Load dataverse
        dataverse_response = self.dataverse_api.get_dataverse(identifier=dataverse_identifier)
        response_json = dataverse_response.json()
        if 'data' in response_json:
            dataverse = response_json['data']
            self.logger.info("Dataverse name: %s", dataverse['name'])

            # Add contact information
            if 'dataverseContacts' in dataverse:
                dataverseContacts = dataverse['dataverseContacts']
                self.logger.debug("The dataverseContacts list contains " + str(len(dataverseContacts)) + " contacts.")
                for dataverseContact in dataverseContacts:
                    if 'contactEmail' in dataverseContact:
                        contactEmail = dataverseContact['contactEmail'].strip()
                        self.logger.debug("Found email of dataverse contact: %s", str(contactEmail))
                        user = self.find_user_email(contactEmail)
                        if bool(user):
                            self.logger.debug("Adding contact information: %s", user)
                            new_user = user
                        else:
                            self.logger.warn("Unable to find user from dataverseContact email: " + str(contactEmail))
                    else:
                        self.logger.warn("First dataverseContact doesn't have an email.")
            elif 'creator' in dataverse:        # Legacy field in older Dataverse versions
                new_user = dataverse['contact']
                self.logger.debug("Adding contact of dataverse: %s", dataverse['contact'])
            else:
                self.logger.warn("Dataverse contact was empty.")
        else:
            self.logger.warn("Dataverse was empty.")

        # Add new user to users list if one was found
        if new_user:
            users.append(new_user)