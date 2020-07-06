import setuptools
from vscodl import constants

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="vsco-dl",
    version=constants.VERSION,
    description="Tool for downloading VSCO user images and journals",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="tecome",
    author_email="tecome@protonmail.com",
    url="https://github.com/tecome/vsco-dl",
    packages=setuptools.find_packages(),
    install_requires=[
        "tqdm",
        "requests",
        "beautifulsoup4",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    entry_points={
        "console_scripts": [
            "vsco-dl = vscodl:main"
        ]
    },
    keywords="vsco dl scrape download image",
    python_requires=">=3.5"
)
