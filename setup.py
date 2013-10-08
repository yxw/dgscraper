# -*- coding: utf-8 -*-
import os

from setuptools import setup
from io import open

long_description = open(os.path.join(os.path.dirname(__file__), "README"), encoding='utf-8').read().encode('ascii', 'ignore')

dependencies = [
    #"beautifulsoup4",
    "lxml==3.2.3"
]

setup(
    name = "dgscraper",
    version = "0.1.0",
    author = "Will Yang",
    author_email = "yang.xiaowei@gmail.com",
    description = "Web (html) content scraper",
    license = "See LICENSE file",
    install_requires = dependencies,
    packages = ['dgscraper'],
    long_description = long_description
)


