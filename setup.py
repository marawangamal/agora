from setuptools import setup, find_packages

setup(
    # name="slurm-dag"
    name="jrun",
    description="Job management tool for running and monitoring jobs with dependencies",
    version="1.0.0",
    packages=find_packages(include=["jrun*"]),
    install_requires=[
        "tabulate>=0.9.0",
        "PyYAML>=6.0",
        "appdirs>=1.4.4",
    ],
    entry_points={
        "console_scripts": ["jrun = jrun.main:main"],
    },
)
