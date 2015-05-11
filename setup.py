#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
#
# Copyright (c) 2013, 2014, 2015 Intel, Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2 of the License
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Setup for Automated Flasher and Tester Tool."""

from setuptools import setup

BASE_PROJECT_NAME = "aft"
PROJECT_NAME = "pc"
PACKAGE_NAME = ".".join([BASE_PROJECT_NAME, "plugins", PROJECT_NAME])

setup(name=PROJECT_NAME,
      version="0.4.0",
      description="AFT plugin for PC-like devices",
      author="Igor Stoppa",
      author_email="igor.stoppa@intel.com",
      package_dir={PACKAGE_NAME: "src"},
      packages=[PACKAGE_NAME],
      entry_points={
          "aft_plugins": [
              "pcdevice = aft.plugins.pc.pcdevice:PCDevice",
              "pcstopology = aft.plugins.pc.pcstopology:PCsTopology",
          ],
      },
     )
