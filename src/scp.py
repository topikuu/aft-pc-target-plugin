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
Class to exchange files with ssl-capable devices.
"""

from aft.plugins.pc.ssl import Ssl


# pylint: disable=no-init
class Scp(Ssl):
    """
    scp wrapper
    """
    DEFAULT_TIMEOUT = 5

    @classmethod
    def init(cls, timeout=DEFAULT_TIMEOUT):
        """
        Static initializer.
        """
        return super(Scp, cls).init_class(command="scp",
                                          timeout=timeout)

    @classmethod
    def run(cls, parms=()):
        """
        Executes scp with custom parameters.
        """
        return super(Scp, cls).run(parms=cls._default_parms + parms)

# pylint: disable=too-many-arguments
    @classmethod
    def push(cls, dev_ip, source, destination, user="root", timeout=-1):
        """
        Copy a file to the DUT.
        """
        return super(Scp, cls)._run(
            parms=cls._default_parms +
            (source, user + "@" + dev_ip + ":" + destination,),
            timeout=timeout)
# pylint: enable=too-many-arguments
# pylint: enable=no-init
