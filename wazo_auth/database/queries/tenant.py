# -*- coding: utf-8 -*-
# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import and_, exc, text
from wazo_auth import schemas
from .base import BaseDAO, PaginatorMixin
from ..models import (
    Address,
    Email,
    Policy,
    Tenant,
    TenantPolicy,
    TenantUser,
    User,
    UserEmail,
)
from . import filters
from ... import exceptions


class TenantDAO(filters.FilterMixin, PaginatorMixin, BaseDAO):

    constraint_to_column_map = {
        'auth_tenant_name_key': 'name',
    }
    search_filter = filters.tenant_search_filter
    strict_filter = filters.tenant_strict_filter
    column_map = {'name': Tenant.name}

    def exists(self, tenant_uuid):
        return self.count(uuid=tenant_uuid) > 0

    def add_policy(self, tenant_uuid, policy_uuid):
        tenant_policy = TenantPolicy(tenant_uuid=str(tenant_uuid), policy_uuid=str(policy_uuid))
        with self.new_session() as s:
            s.add(tenant_policy)
            try:
                s.commit()
            except exc.IntegrityError as e:
                if e.orig.pgcode == self._UNIQUE_CONSTRAINT_CODE:
                    # This association already exists.
                    s.rollback()
                    return
                if e.orig.pgcode == self._FKEY_CONSTRAINT_CODE:
                    constraint = e.orig.diag.constraint_name
                    if constraint == 'auth_tenant_policy_tenant_uuid_fkey':
                        raise exceptions.UnknownTenantException(tenant_uuid)
                    elif constraint == 'auth_tenant_policy_policy_uuid_fkey':
                        raise exceptions.UnknownPolicyException(policy_uuid)
                raise

    def add_user(self, tenant_uuid, user_uuid):
        tenant_user = TenantUser(tenant_uuid=str(tenant_uuid), user_uuid=str(user_uuid))
        with self.new_session() as s:
            s.add(tenant_user)
            try:
                s.commit()
            except exc.IntegrityError as e:
                if e.orig.pgcode == self._UNIQUE_CONSTRAINT_CODE:
                    # This association already exists.
                    s.rollback()
                    return
                if e.orig.pgcode == self._FKEY_CONSTRAINT_CODE:
                    constraint = e.orig.diag.constraint_name
                    if constraint == 'auth_tenant_user_tenant_uuid_fkey':
                        raise exceptions.UnknownTenantException(tenant_uuid)
                    elif constraint == 'auth_tenant_user_user_uuid_fkey':
                        raise exceptions.UnknownUserException(user_uuid)
                raise

    def count(self, **kwargs):
        filtered = kwargs.get('filtered')
        if filtered is not False:
            strict_filter = self.new_strict_filter(**kwargs)
            search_filter = self.new_search_filter(**kwargs)
            filter_ = and_(strict_filter, search_filter)
        else:
            filter_ = text('true')

        with self.new_session() as s:
            return s.query(Tenant).filter(filter_).count()

    def count_policies(self, tenant_uuid, **kwargs):
        filtered = kwargs.get('filtered')
        if filtered is not False:
            strict_filter = filters.policy_strict_filter.new_filter(**kwargs)
            search_filter = filters.policy_search_filter.new_filter(**kwargs)
            filter_ = and_(strict_filter, search_filter)
        else:
            filter_ = text('true')

        filter_ = and_(filter_, TenantPolicy.tenant_uuid == str(tenant_uuid))

        with self.new_session() as s:
            return s.query(Policy.uuid).join(TenantPolicy).filter(filter_).count()

    def count_users(self, tenant_uuid, **kwargs):
        filtered = kwargs.get('filtered')
        if filtered is not False:
            strict_filter = filters.user_strict_filter.new_filter(**kwargs)
            search_filter = filters.user_search_filter.new_filter(**kwargs)
            filter_ = and_(strict_filter, search_filter)
        else:
            filter_ = text('true')

        filter_ = and_(filter_, TenantUser.tenant_uuid == str(tenant_uuid))

        with self.new_session() as s:
            return s.query(
                TenantUser
            ).join(
                User
            ).join(
                UserEmail
            ).join(
                Email
            ).filter(filter_).count()

    def create(self, **kwargs):
        parent_uuid = kwargs.get('parent_uuid')
        if not parent_uuid:
            kwargs['parent_uuid'] = self.find_top_tenant()

        tenant = Tenant(
            name=kwargs['name'],
            phone=kwargs['phone'],
            contact_uuid=kwargs['contact_uuid'],
            address_id=kwargs['address_id'],
            parent_uuid=kwargs['parent_uuid'],
        )
        uuid_ = kwargs.get('uuid')
        if uuid_:
            tenant.uuid = str(uuid_)

        with self.new_session() as s:
            s.add(tenant)
            try:
                s.commit()
            except exc.IntegrityError as e:
                if e.orig.pgcode == self._UNIQUE_CONSTRAINT_CODE:
                    column = self.constraint_to_column_map.get(e.orig.diag.constraint_name)
                    value = locals().get(column)
                    if column:
                        raise exceptions.ConflictException('tenants', column, value)
                elif e.orig.pgcode == self._FKEY_CONSTRAINT_CODE:
                    constraint = e.orig.diag.constraint_name
                    if constraint == 'auth_tenant_contact_uuid_fkey':
                        raise exceptions.UnknownUserException(kwargs['contact_uuid'])
                raise
            return tenant.uuid

    def find_top_tenant(self):
        with self.new_session() as s:
            return s.query(Tenant).filter(Tenant.uuid == Tenant.parent_uuid).first().uuid

    def delete(self, uuid):
        with self.new_session() as s:
            nb_deleted = s.query(Tenant).filter(Tenant.uuid == str(uuid)).delete()

        if not nb_deleted:
            if not self.list_(uuid=uuid):
                raise exceptions.UnknownTenantException(uuid)
            else:
                raise exceptions.UnknownUserException(uuid)

    def get_address_id(self, tenant_uuid):
        with self.new_session() as s:
            return s.query(Tenant.address_id).filter(Tenant.uuid == str(tenant_uuid)).scalar()

    def list_(self, **kwargs):
        schema = schemas.TenantSchema()

        search_filter = self.new_search_filter(**kwargs)
        strict_filter = self.new_strict_filter(**kwargs)
        filter_ = and_(strict_filter, search_filter)

        with self.new_session() as s:
            query = s.query(
                Tenant,
                Address,
            ).outerjoin(
                Address
            ).outerjoin(
                TenantUser
            ).outerjoin(
                TenantPolicy
            ).filter(filter_).group_by(Tenant, Address)
            query = self._paginator.update_query(query, **kwargs)

            def to_dict(tenant, address):
                tenant.address = address
                return schema.dump(tenant).data

            return [to_dict(*row) for row in query.all()]

    def remove_policy(self, tenant_uuid, policy_uuid):
        filter_ = and_(
            TenantPolicy.policy_uuid == str(policy_uuid),
            TenantPolicy.tenant_uuid == str(tenant_uuid),
        )

        with self.new_session() as s:
            return s.query(TenantPolicy).filter(filter_).delete()

    def remove_user(self, tenant_uuid, user_uuid):
        filter_ = and_(
            TenantUser.user_uuid == str(user_uuid),
            TenantUser.tenant_uuid == str(tenant_uuid),
        )

        with self.new_session() as s:
            return s.query(TenantUser).filter(filter_).delete()

    def update(self, tenant_uuid, **kwargs):
        filter_ = Tenant.uuid == str(tenant_uuid)
        values = {
            'name': kwargs.get('name'),
            'contact_uuid': kwargs.get('contact_uuid'),
            'phone': kwargs.get('phone'),
            'address_id': kwargs.get('address_id'),
        }

        with self.new_session() as s:
            try:
                s.query(Tenant).filter(filter_).update(values)
            except exc.IntegrityError as e:
                if e.orig.pgcode == self._FKEY_CONSTRAINT_CODE:
                    constraint = e.orig.diag.constraint_name
                    if constraint == 'auth_tenant_contact_uuid_fkey':
                        raise exceptions.UnknownUserException(kwargs['contact_uuid'])
                raise
