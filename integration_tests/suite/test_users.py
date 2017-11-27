# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests
from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    empty,
    has_entries,
    has_items,
    has_properties,
)
from contextlib import contextmanager
from xivo_auth_client import Client
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from xivo_test_helpers.hamcrest.raises import raises
from .helpers import fixtures
from .helpers.base import (
    assert_http_error,
    assert_no_error,
    MockBackendTestCase,
)

UNKNOWN_UUID = '00000000-0000-0000-0000-000000000000'


class TestUsers(MockBackendTestCase):

    @fixtures.http_user()
    def test_delete(self, user):
        assert_http_error(404, self.client.users.delete, UNKNOWN_UUID)
        assert_no_error(self.client.users.delete, user['uuid'])
        assert_http_error(404, self.client.users.delete, user['uuid'])

    def test_post(self):
        args = dict(
            username='foobar',
            email_address='foobar@example.com',
            password='s3cr37',
        )

        with self.auto_remove_user(self.client.users.new, **args) as user:
            assert_that(
                user,
                has_entries(
                    'uuid', uuid_(),
                    'username', 'foobar',
                    'emails', contains_inanyorder(
                        has_entries(
                            'address', 'foobar@example.com',
                            'main', True,
                            'confirmed', False))))

    def test_register_post(self):
        args = dict(
            username='foobar',
            email_address='foobar@example.com',
            password='s3cr37',
        )

        with self.auto_remove_user(self.client.users.register, **args) as user:
            assert_that(
                user,
                has_entries(
                    'uuid', uuid_(),
                    'username', 'foobar',
                    'emails', contains_inanyorder(
                        has_entries(
                            'address', 'foobar@example.com',
                            'main', True,
                            'confirmed', False))))

    @fixtures.http_user(username='foo', email_address='foo@example.com')
    @fixtures.http_user(username='bar', email_address='bar@example.com')
    @fixtures.http_user(username='baz', email_address='baz@example.com')
    def test_list(self, *users):
        def check_list_result(result, filtered, item_matcher, *usernames):
            items = item_matcher(*[has_entries('username', username) for username in usernames])
            expected = has_entries('total', 3, 'filtered', filtered, 'items', items)
            assert_that(result, expected)

        result = self.client.users.list(search='ba')
        check_list_result(result, 2, contains_inanyorder, 'bar', 'baz')

        result = self.client.users.list(username='baz')
        check_list_result(result, 1, contains_inanyorder, 'baz')

        result = self.client.users.list(order='username', direction='desc')
        check_list_result(result, 3, contains, 'foo', 'baz', 'bar')

        result = self.client.users.list(limit=1, offset=1, order='username', direction='asc')
        check_list_result(result, 3, contains, 'baz')

    @fixtures.http_user(username='foo', email_address='foo@example.com')
    def test_get(self, user):
        result = self.client.users.get(user['uuid'])
        assert_that(
            result,
            has_entries(
                'uuid', user['uuid'],
                'username', 'foo',
                'emails', contains_inanyorder(
                    has_entries(
                        'address', 'foo@example.com',
                        'confirmed', False,
                        'main', True))))

    @fixtures.http_user(username='foo', password='bar')
    @fixtures.http_policy(name='two', acl_templates=['acl.one.{{ username }}', 'acl.two'])
    @fixtures.http_policy(name='one', acl_templates=['this.is.a.test.acl'])
    def test_user_policy(self, policy_1, policy_2, user):
        assert_no_error(self.client.users.remove_policy, user['uuid'], policy_1['uuid'])

        result = self.client.users.get_policies(user['uuid'])
        assert_that(
            result,
            has_entries(
                'total', 0,
                'items', empty(),
                'filtered', 0,
            ),
            'not associated',
        )

        self.client.users.add_policy(user['uuid'], policy_1['uuid'])
        self.client.users.add_policy(user['uuid'], policy_2['uuid'])

        user_client = Client(
            self.get_host(), port=self.service_port(9497, 'auth'), verify_certificate=False,
            username='foo', password='bar')
        token_data = user_client.token.new('wazo_user', expiration=5)
        assert_that(
            token_data,
            has_entries(
                'acls', has_items(
                    'acl.one.foo',
                    'this.is.a.test.acl',
                    'acl.two',
                ),
            ),
            'generated acl',
        )

        self.client.users.remove_policy(user['uuid'], policy_2['uuid'])

        assert_that(
            calling(
                self.client.users.add_policy
            ).with_args('8ee4e6a3-533e-4b00-99b2-33b2e55102f2', policy_2['uuid']),
            raises(requests.HTTPError).matching(
                has_properties('response', has_properties('status_code', 404)),
            ),
            'unknown user',
        )

        assert_that(
            calling(
                self.client.users.add_policy
            ).with_args(user['uuid'], '113bb403-7914-4685-a0ec-330676e61f7c'),
            raises(requests.HTTPError).matching(
                has_properties('response', has_properties('status_code', 404)),
            ),
            'unknown policy',
        )

        result = self.client.users.get_policies(user['uuid'])
        assert_that(
            result,
            has_entries(
                'total', 1,
                'items', contains(has_entries('name', 'one')),
                'filtered', 1,
            ),
            'not associated',
        )

        result = self.client.users.get_policies(user['uuid'], search='two')
        assert_that(
            result,
            has_entries(
                'total', 1,
                'items', empty(),
                'filtered', 0,
            ),
            'not associated',
        )

        assert_no_error(self.client.users.remove_policy, user['uuid'], policy_1['uuid'])

    @contextmanager
    def auto_remove_user(self, fn, *args, **kwargs):
        user = fn(*args, **kwargs)
        try:
            yield user
        finally:
            self.client.users.delete(user['uuid'])
