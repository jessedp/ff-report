from setuptools import setup, find_packages

setup(
    name="fantasy-football-reports",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "espn_api",
        "jinja2",
        "python-dotenv",
        "click",
    ],
    entry_points={
        "console_scripts": [
            "ff=ff.__main__:cli",
        ],
    },
)