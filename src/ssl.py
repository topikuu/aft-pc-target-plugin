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
Abstract Class providing shared ssl options
"""

import abc
from os.path import expanduser
from aft.cmdlinetool import CmdLineTool


# pylint: disable=too-few-public-methods
# pylint: disable=no-init
class Ssl(CmdLineTool):
    """
    ssl wrapper
    """
    __metaclass__ = abc.ABCMeta
    DEFAULT_TIMEOUT = 5
    CONNECT_TIMEOUT = 5
    _default_parms = (
        "-i", "".join([expanduser("~"), "/.ssh/id_rsa_testing_harness"]),
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout={0}".format(CONNECT_TIMEOUT))

    @classmethod
    def init_class(cls, command=None, timeout=DEFAULT_TIMEOUT,
                   exit_on_error=False):
        """
        Init function for class variables.
        """
        return super(Ssl, cls).init_class(command=command, timeout=timeout,
                                          exit_on_error=exit_on_error)
# pylint: enable=too-few-public-methods
# pylint: enable=no-init
