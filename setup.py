from setuptools import find_packages, setup

setup(
    name="orgy",
    version="0.1.1",
    entry_points={
        "console_scripts": [
            "orgy = orgy:main",
        ]
    },
    install_requires=[
        "mutagen==1.46.0",
        "youtube-dl==2021.12.17",
    ],
)
