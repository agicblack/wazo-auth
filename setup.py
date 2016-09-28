#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages
from setuptools import setup

setup(
    name='xivo_auth',
    version='0.1',

    description='XiVO auth',

    author='Avencall',
    author_email='dev@proformatique.com',

    url='https://github.com/xivo-pbx/xivo-auth',

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    package_data={
        'xivo_auth.swagger': ['*.json'],
    },

    scripts=['bin/xivo-auth'],

    entry_points={
        'xivo_auth.backends': [
            'xivo_admin = xivo_auth.plugins.backends:XiVOAdmin',
            'xivo_service = xivo_auth.plugins.backends:XiVOService',
            'xivo_user = xivo_auth.plugins.backends:XiVOUser',
            'ldap_user = xivo_auth.plugins.backends:LDAPUser',
            'mock = xivo_auth.plugins.backends:BackendMock',
            'mock_with_uuid = xivo_auth.plugins.backends:BackendMockWithUUID',
            'broken_init = xivo_auth.plugins.backends:BrokenInitBackend',
            'broken_verify_password = xivo_auth.plugins.backends:BrokenVerifyPasswordBackend',
        ],
    }
)
