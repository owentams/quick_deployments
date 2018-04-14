from setuptools import setup

setup(
    name="Quick Deployments",
    version="0.0.1",
    author="D. Scott Boggs",
    author_email="scott@tams.tech",
    description="Quick deployment scripts for various web services.",
    packages=["src", "test"],
    install_requires=["docker"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"]
)
