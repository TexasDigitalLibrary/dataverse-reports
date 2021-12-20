import codecs
import os
import re

from setuptools import setup

install_requires = ['dataverse-client-python']

setup(
    name = 'dataverse-reports',
    version='1.4.0-SNAPSHOT',
    url = 'https://www.tdl.org/',
    author = 'Nicholas Woodward',
    author_email = 'njw@austin.utexas.edu',
    license = 'MIT',
    packages = ['dataverse-reports'],
    install_requires = install_requires,
    description = 'Generate and email statistical reports for content stored in Dataverse - https://dataverse.org/',
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
    ],
    test_suite = 'test',
)
