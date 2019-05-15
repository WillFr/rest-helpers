#!/usr/bin/env python3

import os
import logging
import sys
try:
    import multiprocessing
except:
    pass
# nose requires multiprocessing and logging to be initialized before the setup
# call, or we'll get a spurious crash on exit.
from setuptools import setup, find_packages
from setuptools.dist import Distribution

is_release = False
if "--release" in sys.argv:
    is_release = True
    sys.argv.remove("--release")

base = os.path.dirname(os.path.abspath(__file__))


def read(fname):
    '''Utility function to read the README file.'''
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# figure out what the install will need
install_requires = [
    "setuptools >=0.5",
    "flask",
    "pyyaml",
    "requests",
    "schematics",
    "python-dateutil",
    "requests-futures",
    "httpretty",
    "aiohttp>=2.3.0",
    "aiotask_context",
    "pytest-aiohttp",
    "pytest-asyncio",
    'cryptography',
    'python-jose[cryptography]',
    'jinja2'
]

setup(
    name="rest-helpers",
    setup_requires=["vcver"],
    vcver={
        "is_release": is_release,
        "path": base
    },
    url="https://github.com/WillFr/rest-helpers",
    author="Guillaume Grosbois",
    author_email="grosbois.guillaume@gmail.com",
    description="A set of method to help creating rest services",
    packages=find_packages(),
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "Operating System :: OS Independent"],
    package_data={"rest_helpers": ["templates/swagger-ui.html"]},
    install_requires=install_requires,
    include_package_data=True,
    tests_require=[  "mock >=0.7.2",
                     "coverage",
                     "httpretty",
                     "httmock",
                    "pytest-aiohttp",
                    "pytest-cov"] + install_requires
    )
