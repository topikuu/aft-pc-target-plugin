# Copyright (c) 2013-14 Intel, Inc.
# Author igor.stoppa@intel.com
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; version 2 of the License
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

"""
Class to interface with ssh-capable devices.
"""

import os
from aft.plugins.pc.ssl import Ssl


# pylint: disable=no-init
class Ssh(Ssl):
    """
    ssh wrapper
    """
    DEFAULT_TIMEOUT = 5

    @classmethod
    def init(cls, timeout=DEFAULT_TIMEOUT):
        """
        Initialized for class variables
        """
        return super(Ssh, cls).init_class(command="ssh",
                                          timeout=timeout)

    @staticmethod
    def _get_env(var):
        """
        Fetches settings from the environment.
        """
        val = os.getenv(var)
        if val is not "":
            return "export " + var + '="' + val + '";'
        return ""

    @staticmethod
    def _get_proxy_settings():
        """
        Fetches proxy settings from the environment.
        """
        PROXY_ENV = ["http_proxy", "https_proxy", "ftp_proxy", "no_proxy"]

        proxy_env = ""
        for env in PROXY_ENV:
            proxy_env += Ssh._get_env(env)
        return (proxy_env,)

# pylint: disable=too-many-arguments
    @classmethod
    def execute(cls, dev_ip, timeout=-1,
                command=(), environment=(), user="root"):
        """
        Executes ssh with custom parameters.
        """
        return super(Ssh, cls)._run(parms=cls._default_parms +
                                    (user + "@" + str(dev_ip),) +
                                    Ssh._get_proxy_settings() +
                                    environment +
                                    command, timeout=timeout)
# pylint: enable=too-many-arguments
# pylint: enable=no-init
