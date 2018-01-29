from setuptools import setup

install_requires = ['dataverse-client-python']

setup(
    name = 'dataverse-reports',
    version = 0.0.1,
    url = 'https://www.tdl.org/',
    author = 'Nicholas Woodward',
    author_email = 'njw@austin.utexas.edu',
    license = 'http://www.opensource.org/licenses/bsd-license.php',
    packages = ['dataverse-reports'],
    install_requires = install_requires,
    description = 'Generate and email statistical reports for content stored in Dataverse - https://dataverse.org/',
    classifiers = list(filter(None, classifiers.split('\n'))),
    test_suite = 'test',
)
