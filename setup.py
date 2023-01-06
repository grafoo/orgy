from setuptools import find_packages, setup

setup(
    name="orgy",
    version="0.1.2",
    entry_points={
        "console_scripts": [
            "orgy = orgy:main",
        ]
    },
    install_requires=[
        "mutagen==1.46.0",
        "tqdm==4.64.1",
        "youtube-dl==2021.12.17",
    ],
)
