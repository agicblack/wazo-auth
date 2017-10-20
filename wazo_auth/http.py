# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import functools
import logging
import time

from flask import current_app, Flask, request, make_response
from flask.ext.cors import CORS
from flask_restful import Api, Resource
from xivo.rest_api_helpers import handle_api_exception
from pkg_resources import resource_string
from xivo import http_helpers

from . import exceptions, schemas

logger = logging.getLogger(__name__)


def _error(code, msg):
    return {'reason': [msg],
            'timestamp': [time.time()],
            'status_code': code}, code


def required_acl(scope):
    def wrap(f):
        @functools.wraps(f)
        def wrapped_f(*args, **kwargs):
            try:
                token = request.headers.get('X-Auth-Token', '')
                current_app.config['token_manager'].get(token, scope)
            except exceptions.ManagerException:
                return _error(401, 'Unauthorized')
            return f(*args, **kwargs)
        return wrapped_f
    return wrap


def handle_manager_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions.ManagerException as error:
            return _error(error.code, str(error))
    return wrapper


class ErrorCatchingResource(Resource):
    method_decorators = (
        [
            handle_manager_exception,
            handle_api_exception,
        ] + Resource.method_decorators
    )


class Policies(ErrorCatchingResource):

    @required_acl('auth.policies.create')
    def post(self):
        data = request.get_json()
        policy_service = current_app.config['policy_service']
        policy = policy_service.create(data)
        return policy, 200

    @required_acl('auth.policies.read')
    def get(self):
        ListSchema = schemas.new_list_schema('name')
        list_params, errors = ListSchema().load(request.args)
        if errors:
            raise exceptions.InvalidListParamException(errors)

        policy_service = current_app.config['policy_service']
        policies = policy_service.list(**list_params)
        total = policy_service.count(**list_params)
        return {'items': policies, 'total': total}, 200


class Policy(ErrorCatchingResource):

    @required_acl('auth.policies.{policy_uuid}.read')
    def get(self, policy_uuid):
        policy_service = current_app.config['policy_service']
        policy = policy_service.get(policy_uuid)
        return policy, 200

    @required_acl('auth.policies.{policy_uuid}.delete')
    def delete(self, policy_uuid):
        policy_service = current_app.config['policy_service']
        policy_service.delete(policy_uuid)
        return '', 204

    @required_acl('auth.policies.{policy_uuid}.edit')
    def put(self, policy_uuid):
        data = request.get_json()
        policy_service = current_app.config['policy_service']
        policy = policy_service.update(policy_uuid, data)
        return policy, 200


class PolicyTemplate(ErrorCatchingResource):

    @required_acl('auth.policies.{policy_uuid}.edit')
    def delete(self, policy_uuid, template):
        policy_service = current_app.config['policy_service']
        policy_service.delete_acl_template(policy_uuid, template)
        return '', 204

    @required_acl('auth.policies.{policy_uuid}.edit')
    def put(self, policy_uuid, template):
        policy_service = current_app.config['policy_service']
        policy_service.add_acl_template(policy_uuid, template)
        return '', 204


class Tokens(ErrorCatchingResource):

    def post(self):
        if request.authorization:
            login = request.authorization.username
            password = request.authorization.password
        else:
            login = ''
            password = ''

        args, error = schemas.TokenRequestSchema().load(request.get_json(force=True))
        if error:
            return _error(400, unicode(error))

        backend_name = args['backend']
        try:
            backend = current_app.config['backends'][backend_name].obj
        except KeyError:
            return _error(401, 'Authentication Failed')

        if not backend.verify_password(login, password, args):
            return _error(401, 'Authentication Failed')

        token = current_app.config['token_manager'].new_token(backend, login, args)

        return {'data': token.to_dict()}, 200


class Token(ErrorCatchingResource):

    def delete(self, token):
        current_app.config['token_manager'].remove_token(token)

        return {'data': {'message': 'success'}}

    def get(self, token):
        scope = request.args.get('scope')
        token = current_app.config['token_manager'].get(token, scope)
        return {'data': token.to_dict()}

    def head(self, token):
        scope = request.args.get('scope')
        token = current_app.config['token_manager'].get(token, scope)
        return '', 204


class User(ErrorCatchingResource):

    @required_acl('auth.users.{user_uuid}.read')
    def get(self, user_uuid):
        user_service = current_app.config['user_service']
        return user_service.get_user(user_uuid)

    @required_acl('auth.users.{user_uuid}.delete')
    def delete(self, user_uuid):
        user_service = current_app.config['user_service']
        user_service.delete_user(user_uuid)
        return '', 204


class Users(ErrorCatchingResource):

    @required_acl('auth.users.read')
    def get(self):
        ListSchema = schemas.new_list_schema('username')
        list_params, errors = ListSchema().load(request.args)
        if errors:
            raise exceptions.InvalidListParamException(errors)

        for key, value in request.args.iteritems():
            if key in list_params:
                continue
            list_params[key] = value

        user_service = current_app.config['user_service']

        users = user_service.list_users(**list_params)
        total = user_service.count_users(filtered=False, **list_params)
        filtered = user_service.count_users(filtered=True, **list_params)

        response = dict(
            filtered=filtered,
            total=total,
            items=users,
        )

        return response, 200

    def post(self):
        user_service = current_app.config['user_service']
        args, errors = schemas.UserRequestSchema().load(request.get_json(force=True))
        if errors:
            raise exceptions.UserParamException.from_errors(errors)
        result = user_service.new_user(**args)
        return result, 200


class Backends(ErrorCatchingResource):

    def get(self):
        return {'data': current_app.config['loaded_plugins']}


class Swagger(Resource):

    api_package = "wazo_auth.swagger"
    api_filename = "api.yml"
    api_path = "/api/api.yml"

    @classmethod
    def add_resource(cls, api):
        api.add_resource(cls, cls.api_path)

    def get(self):
        try:
            api_spec = resource_string(self.api_package, self.api_filename)
        except IOError:
            return {'error': "API spec does not exist"}, 404

        return make_response(api_spec, 200, {'Content-Type': 'application/x-yaml'})


def new_app(config, backends, policy_service, token_manager, user_service):
    cors_config = dict(config['rest_api']['cors'])
    cors_enabled = cors_config.pop('enabled')
    app = Flask('wazo-auth')
    http_helpers.add_logger(app, logger)
    api = Api(app, prefix='/0.1')
    api.add_resource(Policies, '/policies')
    api.add_resource(Policy, '/policies/<string:policy_uuid>')
    api.add_resource(PolicyTemplate, '/policies/<string:policy_uuid>/acl_templates/<template>')
    api.add_resource(Tokens, '/token')
    api.add_resource(Token, '/token/<string:token>')
    api.add_resource(Users, '/users')
    api.add_resource(User, '/users/<string:user_uuid>')
    api.add_resource(Backends, '/backends')
    api.add_resource(Swagger, '/api/api.yml')
    app.config.update(config)
    if cors_enabled:
        CORS(app, **cors_config)

    app.config['policy_service'] = policy_service
    app.config['token_manager'] = token_manager
    app.config['backends'] = backends
    app.config['user_service'] = user_service
    app.after_request(http_helpers.log_request)

    return app
