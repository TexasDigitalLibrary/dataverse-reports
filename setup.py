import codecs
import os
import re
import sys

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        version_file,
        re.M,
    )
    if version_match:
        return version_match.group(1)

    raise RuntimeError("Unable to find version string.")

install_requires = ['dataverse-client-python']

setup(
    name = 'dataverse-reports',
    version=find_version("lib", "__init__.py"),
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
