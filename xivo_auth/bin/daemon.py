# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
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

import sys
import logging

from xivo.daemonize import pidfile_context
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging
from xivo_auth.config import get_config
from xivo_auth.controller import Controller


def main():
    spamming_loggers = ['urllib3', 'Flask-Cors', 'amqp', 'kombu.common', 'kombu.pidbox', 'celery.worker.strategy', 'celery.bootsteps']
    for logger_name in spamming_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)

    config = get_config(sys.argv[1:])

    setup_logging(config['log_filename'], config['foreground'], config['debug'], config['log_level'])
    user = config.get('user')
    if user:
        change_user(user)

    controller = Controller(config)
    with pidfile_context(config['pid_filename'], config['foreground']):
        controller.run()
