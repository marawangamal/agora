from setuptools import setup, find_packages

setup(
    name="tjdnet",  # or whatever your project is called
    version="0.1.0",
    packages=find_packages(include=["jrun*"]),
    install_requires=["tabulate>=0.9.0", "PyYAML>=6.0"],
    entry_points={
        "console_scripts": ["jrun = jrun.main:main"],
    },
)
