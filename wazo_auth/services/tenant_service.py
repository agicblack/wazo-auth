# -*- coding: utf-8 -*-
# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_bus.resources.auth import events
from wazo_auth import exceptions
from wazo_auth.services.helpers import BaseService


class TenantService(BaseService):

    def __init__(self, dao, bus_publisher=None):
        super(TenantService, self).__init__(dao)
        self._bus_publisher = bus_publisher

    def add_policy(self, tenant_uuid, policy_uuid):
        return self._dao.tenant.add_policy(tenant_uuid, policy_uuid)

    def add_user(self, tenant_uuid, user_uuid):
        return self._dao.tenant.add_user(tenant_uuid, user_uuid)

    def count_policies(self, tenant_uuid, **kwargs):
        return self._dao.tenant.count_policies(tenant_uuid, **kwargs)

    def count_users(self, tenant_uuid, **kwargs):
        return self._dao.tenant.count_users(tenant_uuid, **kwargs)

    def count(self, **kwargs):
        return self._dao.tenant.count(**kwargs)

    def delete(self, uuid):
        result = self._dao.tenant.delete(uuid)
        event = events.TenantDeletedEvent(uuid)
        self._bus_publisher.publish(event)
        return result

    def get(self, uuid):
        tenants = self._dao.tenant.list_(uuid=uuid, limit=1)
        for tenant in tenants:
            return tenant
        raise exceptions.UnknownTenantException(uuid)

    def list_(self, **kwargs):
        return self._dao.tenant.list_(**kwargs)

    def list_policies(self, tenant_uuid, **kwargs):
        return self._dao.policy.list_(tenant_uuid=tenant_uuid, **kwargs)

    def list_users(self, tenant_uuid, **kwargs):
        return self._dao.user.list_(tenant_uuid=tenant_uuid, **kwargs)

    def new(self, **kwargs):
        address_id = self._dao.address.new(**kwargs['address'])
        uuid = self._dao.tenant.create(address_id=address_id, **kwargs)
        result = self.get(uuid)
        event = events.TenantCreatedEvent(uuid, kwargs.get('name'))
        self._bus_publisher.publish(event)
        return result

    def remove_policy(self, tenant_uuid, policy_uuid):
        nb_deleted = self._dao.tenant.remove_policy(tenant_uuid, policy_uuid)
        if nb_deleted:
            return

        if not self._dao.tenant.exists(tenant_uuid):
            raise exceptions.UnknownTenantException(tenant_uuid)

        if not self._dao.policy.exists(policy_uuid):
            raise exceptions.UnknownPolicyException(policy_uuid)

    def remove_user(self, tenant_uuid, user_uuid):
        nb_deleted = self._dao.tenant.remove_user(tenant_uuid, user_uuid)
        if nb_deleted:
            return

        if not self._dao.tenant.exists(tenant_uuid):
            raise exceptions.UnknownTenantException(tenant_uuid)

        if not self._dao.user.exists(user_uuid):
            raise exceptions.UnknownUserException(user_uuid)

    def update(self, tenant_uuid, **kwargs):
        address_id = self._dao.tenant.get_address_id(tenant_uuid)
        if not address_id:
            address_id = self._dao.address.new(**kwargs['address'])
        else:
            address_id, self._dao.address.update(address_id, **kwargs['address'])

        self._dao.tenant.update(tenant_uuid, address_id=address_id, **kwargs)

        return self.get(tenant_uuid)
