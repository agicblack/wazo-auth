# -*- coding: utf-8 -*-
# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from functools import partial
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    has_entries,
    has_items,
)
from .helpers import base, fixtures


class TestUserGroupList(base.WazoAuthTestCase):

    def setUp(self):
        super(TestUserGroupList, self).setUp()
        self.foo = self.client.groups.new(name='foo')
        self.bar = self.client.groups.new(name='bar')
        self.baz = self.client.groups.new(name='baz')
        self.ignored = self.client.groups.new(name='ignored')
        self.user = self.client.users.new(username='alice')
        for group in (self.foo, self.bar, self.baz):
            self.client.groups.add_user(group['uuid'], self.user['uuid'])
        self.action = partial(self.client.users.get_groups, self.user['uuid'])

    def tearDown(self):
        self.client.users.delete(self.user['uuid'])
        for group in (self.ignored, self.baz, self.bar, self.foo):
            self.client.groups.delete(group['uuid'])

    def test_group_list(self):
        result = self.action()
        self.then(result, 3, 3, contains_inanyorder, 'foo', 'bar', 'baz')

        result = self.action(search='ba')
        self.then(result, 3, 2, contains_inanyorder, 'bar', 'baz')

        result = self.action(name='foo')
        self.then(result, 3, 1, contains_inanyorder, 'foo')

        # user not in a visible tenant
        with self.client_in_subtenant() as (client, _, __):
            base.assert_http_error(404, client.users.get_groups, self.user['uuid'])

    def test_group_list_sorting(self):
        expected = [self.bar, self.baz, self.foo]
        base.assert_sorted(self.action, order='name', expected=expected)

    def test_group_list_pagination(self):
        result = self.action(order='name', offset=1)
        self.then(result, 3, 3, contains, 'baz', 'foo')

        result = self.action(order='name', limit=2)
        self.then(result, 3, 3, contains, 'bar', 'baz')

    @staticmethod
    def then(result, total, filtered, matcher, *names):
        items = matcher(*[has_entries(name=name) for name in names])
        assert_that(result, has_entries(total=total, filtered=filtered, items=items))


class TestUserGroupAssociation(base.WazoAuthTestCase):

    @fixtures.http_user_register()
    @fixtures.http_user_register()
    @fixtures.http_group()
    def test_delete(self, group, user1, user2):
        action = self.client.groups.remove_user

        self.client.groups.add_user(group['uuid'], user1['uuid'])
        self.client.groups.add_user(group['uuid'], user2['uuid'])

        base.assert_http_error(404, action, base.UNKNOWN_UUID, user1['uuid'])
        base.assert_http_error(404, action, group['uuid'], base.UNKNOWN_UUID)
        base.assert_no_error(action, group['uuid'], user2['uuid'])
        base.assert_no_error(action, group['uuid'], user2['uuid'])  # Twice

        result = self.client.groups.get_users(group['uuid'])
        assert_that(result, has_entries('items', contains_inanyorder(user1)))

        with self.client_in_subtenant() as (client, user3, _):
            action = client.groups.remove_user

            self.client.groups.add_user(group['uuid'], user3['uuid'])

            # group not visible to this sub tenant
            base.assert_http_error(404, action, group['uuid'], user3['uuid'])

            # user not visible to this sub tenant can be deleted
            with self.group(client, name='foo') as visible_group:
                self.client.groups.add_user(visible_group['uuid'], user1['uuid'])
                base.assert_no_error(action, visible_group['uuid'], user1['uuid'])

    @fixtures.http_user_register()
    @fixtures.http_user_register()
    @fixtures.http_group()
    def test_put(self, group, user1, user2):
        action = self.client.groups.add_user

        base.assert_http_error(404, action, base.UNKNOWN_UUID, user1['uuid'])
        base.assert_http_error(404, action, group['uuid'], base.UNKNOWN_UUID)
        base.assert_no_error(action, group['uuid'], user1['uuid'])
        base.assert_no_error(action, group['uuid'], user1['uuid'])  # Twice

        result = self.client.groups.get_users(group['uuid'])
        assert_that(result, has_entries('items', contains_inanyorder(user1)))

        with self.client_in_subtenant() as (client, user3, __):
            action = client.groups.add_user

            # group not visible to this sub tenant
            base.assert_http_error(404, action, group['uuid'], user3['uuid'])

            # user not visible to this sub tenant
            with self.group(client, name='foo') as visible_group:
                base.assert_http_error(404, action, visible_group['uuid'], user1['uuid'])

                base.assert_no_error(action, visible_group['uuid'], user3['uuid'])

    @fixtures.http_user_register(username='ignored')
    @fixtures.http_user_register(username='baz')
    @fixtures.http_user_register(username='bar')
    @fixtures.http_user_register(username='foo')
    @fixtures.http_group()
    def test_user_list(self, group, foo, bar, baz, ignored):
        for user in (foo, bar, baz):
            self.client.groups.add_user(group['uuid'], user['uuid'])

        result = self.client.groups.get_users(group['uuid'])
        assert_that(result, has_entries(
            'total', 3,
            'filtered', 3,
            'items', contains_inanyorder(
                has_entries('username', 'foo'),
                has_entries('username', 'bar'),
                has_entries('username', 'baz'))))

        result = self.client.groups.get_users(group['uuid'], search='ba')
        assert_that(result, has_entries(
            'total', 3,
            'filtered', 2,
            'items', contains_inanyorder(
                has_entries('username', 'bar'),
                has_entries('username', 'baz'))))

        result = self.client.groups.get_users(group['uuid'], username='foo')
        assert_that(result, has_entries(
            'total', 3,
            'filtered', 1,
            'items', contains_inanyorder(
                has_entries('username', 'foo'))))

        result = self.client.groups.get_users(group['uuid'], order='username', direction='desc')
        assert_that(result, has_entries(
            'total', 3,
            'filtered', 3,
            'items', contains(
                has_entries('username', 'foo'),
                has_entries('username', 'baz'),
                has_entries('username', 'bar'))))

        result = self.client.groups.get_users(group['uuid'], order='username', direction='desc', offset=1)
        assert_that(result, has_entries(
            'total', 3,
            'filtered', 3,
            'items', contains(
                has_entries('username', 'baz'),
                has_entries('username', 'bar'))))

        result = self.client.groups.get_users(group['uuid'], order='username', direction='desc', limit=2)
        assert_that(result, has_entries(
            'total', 3,
            'filtered', 3,
            'items', contains(
                has_entries('username', 'foo'),
                has_entries('username', 'baz'))))

    @fixtures.http_user_register(username='foo', password='bar')
    @fixtures.http_group(name='two')
    @fixtures.http_group(name='one')
    @fixtures.http_policy(name='main', acl_templates=[
        '{% for group in groups %}\nmain.{{ group.name }}.*\n{% endfor %}',
        '{% for group in groups %}\nmain.{{ group.uuid }}\n{% endfor %}',
    ])
    def test_generated_acl(self, policy, group_1, group_2, user):
        self.client.groups.add_user(group_1['uuid'], user['uuid'])
        self.client.groups.add_user(group_2['uuid'], user['uuid'])
        self.client.users.add_policy(user['uuid'], policy['uuid'])

        user_client = self.new_auth_client('foo', 'bar')

        expected_acls = [
            'main.one.*',
            'main.two.*',
            'main.{}'.format(group_1['uuid']),
            'main.{}'.format(group_2['uuid']),
        ]
        token_data = user_client.token.new('wazo_user', expiration=5)
        assert_that(token_data, has_entries('acls', has_items(*expected_acls)))
