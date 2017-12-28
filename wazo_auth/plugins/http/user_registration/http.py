# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from flask import request
from wazo_auth import exceptions, http
from .schemas import UserRegisterPostSchema


class Register(http.ErrorCatchingResource):

    def __init__(self, user_service, email_service):
        self.user_service = user_service
        self.email_service = email_service

    def post(self):
        args, errors = UserRegisterPostSchema().load(request.get_json())
        if errors:
            raise exceptions.UserParamException.from_errors(errors)
        result = self.user_service.new_user(**args)

        try:
            address = args['email_address']
            for e in result['emails']:
                if e['address'] != address:
                    continue
                self.email_service.send_confirmation_email(result['username'], e['uuid'], address)
        except Exception:
            self.user_service.delete_user(result['uuid'])
            raise

        return result, 200
