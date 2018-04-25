"""The setuptools setup for this package."""
from os.path import join as getpath
from os.path import dirname, realpath
from setuptools import setup
from git.repo.base import Repo


def read(*fname: str) -> str:
    """Get the contents of a file in the current directory."""
    return open(getpath(dirname(realpath(__file__)), *fname)).read()


vcs = Repo(dirname(realpath(__file__)))
versionnum = len([c for c in vcs.iter_commits()])


setup(
    name="Quick Deployments",
    version="0.0.%d" % versionnum,
    author="D. Scott Boggs",
    author_email="scott@tams.tech",
    description="Quick deployment scripts for various web services.",
    packages=["src", "test"],
    install_requires=["docker", 'requests', 'python-nmap', 'strict-hint'],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    license="GPLv3",
    keywords="containerization webservice microservice deployment",
    url="https://github.com/dscottboggs/docker-gui",
    long_description=read("README.md"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "Topic :: Containerization",
        "License :: OSI Approved :: GPLv3",
    ]
)
