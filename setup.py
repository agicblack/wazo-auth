#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages
from setuptools import setup


setup(
    name='xivo_auth',
    version='0.1',

    description='XiVO auth',

    author='Sylvain Boily',
    author_email='sboily@avencall.com',

    url='https://github.com/sboily/xivo-auth',

    packages=find_packages(),
    install_requires=[open('requirements.txt').read()],
    include_package_data = True,
    zip_safe = False,

    scripts=['bin/xivo-auth'],
    data_files = [('/etc/xivo-auth', ['etc/xivo-auth/config.yml'])],

    entry_points={
        'xivo_auth.plugins': [
            'auth = xivo_auth.plugins.auth:XiVOAuth',
        ],
    }
)