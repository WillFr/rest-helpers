#!/usr/bin/env python3

import os
import pathlib
import subprocess
from uranium import task_requires


def main(build):
    build.packages.install(".", develop=True)


def test(build):
    import os
    main(build)
    build.packages.install("pytest")
    build.packages.install("pytest-cov")
    build.packages.install("mock")
    build.executables.run([
        "py.test", "--cov=rest_helpers",
        os.getcwd() + "/rest_helpers/tests",
        "--cov-report", "term-missing",
        "--cov-report", "xml:cov.xml"
    ] + build.options.args)


def publish(build):
    """ distribute the uranium package """
    build.packages.install("wheel")
    build.packages.install("twine")
    build.executables.run([
        "python3", os.getcwd() + "/setup.py",
        "sdist", "bdist_wheel", "--universal", "--release",
        "--dist-dir", os.getcwd() + "/dist"
    ])

    build.executables.run([
        "twine", "upload", os.getcwd() + "/dist/*"
    ])