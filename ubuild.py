#!/usr/bin/env python3

import os
import subprocess
from uranium import task_requires


def main(build):
    build.packages.install(".", develop=True)


def test(build):
    main(build)
    build.packages.install("pytest")
    build.packages.install("pytest-cov")
    build.packages.install("mock")
    build.executables.run([
        "py.test", "--cov", "rest_helpers",
        "rest_helpers/tests",
        "--cov-report", "term-missing"
    ] + build.options.args)


def publish(build):
    """ distribute the uranium package """
    build.packages.install("wheel")
    build.packages.install("twine")
    build.executables.run([
        "python", "setup.py",
        "sdist", "bdist_wheel", "--universal", "upload", "--release"
    ])

    build.executables.run([
        "twine", "upload", "dist/*"
    ])