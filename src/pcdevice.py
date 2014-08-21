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
Class representing a PC-like Device with an IP.
"""

import os
import time
import logging

from aft.device import Device
from aft.plugins.pc.ssh import Ssh
from aft.plugins.pc.scp import Scp

VERSION = "0.1.0"


class PCDevice(Device):
    """
    Class representing a PC-like device.
    """
    _MODE_TEST_TIMEOUT = 240
    _POLLING_INTERVAL = 10
    _POWER_CYCLE_DELAY = 10
    _SSH_SHORT_GENERIC_TIMEOUT = 10
    _SSH_IMAGE_WRITING_TIMEOUT = 720

    @classmethod
    def init_class(cls, init_data):
        """
        Initializer for class variables and parent class.
        """
        try:
            cls._leases_file_name = init_data["leases_file_name"]
            cls._root_partition = init_data["root_partition"]
            cls._service_mode = init_data["service_mode"]
            cls._test_mode = init_data["test_mode"]
            return Ssh.init() and Scp.init()
        except KeyError as error:
            logging.critical("Error initializing PC Device Class {0}."
                             .format(error))
            return False

    def __init__(self, model, dev_id, channel, name):
        super(PCDevice, self).__init__(model=model, dev_id=dev_id,
                                       channel=channel, name=name)

    @classmethod
    def get_registered_leases(cls):
        """
        Returns all the current leases.
        """
        with open(cls._leases_file_name) as leases_file:
            return leases_file.readlines()

    @classmethod
    def get_registered_lease_by_mac(cls, mac):
        """
        Returns the leased ip for a specific mac.
        """
        for lease in cls.get_registered_leases():
            requestor_mac, leased_ip = lease.split()[1:3]
            if requestor_mac == mac:
                return leased_ip
        return None

    def get_registered_lease(self):
        """
        Returns the leased ip of the current device.
        """
        return self.get_registered_lease_by_mac(mac=self.dev_id)

    @classmethod
    def _by_ip_is_ready(cls, dev_ip, mode):
        """
        Check if the device with given ip is responsive to ssh
        and in the specified mode.
        """
        logging.debug("Trying to ssh into {0} .".format(dev_ip))
        retval = Ssh.execute(dev_ip=dev_ip,
                             command=("cat", "/proc/version", "|",
                                      "grep", mode),
                             timeout=cls._SSH_SHORT_GENERIC_TIMEOUT, )
        if retval is False:
            logging.debug("Ssh failed.")
        elif mode not in retval:
            logging.debug("Device not in \"{0}\" mode.".format(mode))
        else:
            logging.debug("Device in \"{0}\" mode.".format(mode))

        return retval is not False and mode in retval

    @classmethod
    def by_ip_is_in_service_mode(cls, dev_ip):
        """
        Check if the device is in service mode.
        """
        return cls._by_ip_is_ready(dev_ip=dev_ip, mode=cls._service_mode)

    @classmethod
    def by_ip_is_in_test_mode(cls, dev_ip):
        """
        Check if the device is in service mode.
        """
        return cls._by_ip_is_ready(dev_ip=dev_ip, mode=cls._test_mode)

    @classmethod
    def _by_ip_is_responsive(cls, dev_ip):
        """
        Check if the device is in service mode.
        """
        return cls.by_ip_is_in_test_mode(dev_ip) or \
            cls.by_ip_is_in_service_mode(dev_ip)

    def _is_ready(self, mode):
        """
        Check if the device is responsive to ssh
        and in specified mode.
        """
        return self._by_ip_is_ready(mode=mode,
                                    dev_ip=self.get_registered_lease())

    def is_in_service_mode(self):
        """
        Check if the device is in service mode.
        """
        return self._is_ready(mode=self._service_mode)

    def is_in_test_mode(self):
        """
        Check if the device is in service mode.
        """
        return self._is_ready(mode=self._test_mode)

    def _is_responsive(self):
        """
        Check if the device is responsive to ssh
        and in specified mode.
        """
        return self._by_ip_is_responsive(dev_ip=self.get_registered_lease())

    def _power_cycle(self):
        """
        Reboot the device.
        """
        logging.info("Attempting to reboot the device.")
        if not self.detach():
            logging.critical("Failed cutting power when attempting reboot.")
            return False
        time.sleep(self._POWER_CYCLE_DELAY)
        if not self.attach():
            logging.critical("Failed restoring power when attempting reboot.")
            return False
        logging.info("Completed rebooting the device.")
        return True

    def _wait_for_mode(self, mode):
        """
        For a limited amount of time, try to assess that the device
        is in the mode specified.
        """
        logging.info("Check if device {0} is in mode {1} ."
                     .format(self.get_registered_lease(), mode))
        for _ in range(self._MODE_TEST_TIMEOUT / self._POLLING_INTERVAL):
            if self._is_responsive():
                return self._is_ready(mode=mode)
            else:
                logging.info("Device not responding - waiting {0} seconds."
			     .format(self._POLLING_INTERVAL))
                time.sleep(self._POLLING_INTERVAL)
        logging.info("Device {0} is not in mode {1} ."
                     .format(self.get_registered_lease(), mode))
        return False

    def _enter_mode(self, mode):
        """
        Tries to put the device into the specified mode.
        """
        # Attempts twice: in the worst case the device boots
        # first in test mode, so a further power cycle is needed,
        # to get the device in service mode.
        # That was the theory - here's how it is in practice:
        # Somehow sometimes it gets stuck. Try 3 more times. Total 5.
        for _ in range(2):
            self._power_cycle()
            logging.info("Checking for device in mode \"{0}\" ."
                         .format(mode))
            if self._wait_for_mode(mode=mode):
                logging.info("Found device in mode \"{0}\" ."
                             .format(mode))
                return True
            else:
                logging.info("Devince in mode \"{0}\" was not found."
                             .format(mode))
        logging.critical("Unable to get device {0} in mode \"{1}.\""
                         .format(self.dev_id, mode))
        return False

    def _write_image(self, nfs_file_name):
        """
        Writes image into the internal storage of the device.
        """
        logging.info("Testing for availability of image {0} ."
                     .format(nfs_file_name))
        result = self.execute(
            command=("[", "-f", nfs_file_name, "]", "&&",
                     "echo", "found", "||", "echo", "missing"),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT,
        )
        if "found" in result:
            logging.info("Image found.")
        else:
            logging.critical("Image \"{0}\" not found."
                             .format(nfs_file_name))
            return False
        logging.info("Writing image {0} to internal storage."
                     .format(nfs_file_name))
        result = self.execute(command=("bmaptool", "copy", nfs_file_name,
                                       "/dev/sdb"),
                              timeout=self._SSH_IMAGE_WRITING_TIMEOUT,)
        if result or result is None:
            logging.info("Image written successfully.")
            return True
        else:
            logging.critical("Error while writing image to device.")
            return False

    def _install_tester_public_key(self):
        """
        Copy ssh public key to root user on the target device.
        """
        # update info about the partition table
        self.execute(command=("partprobe", "/dev/sdb"),
                     timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        logging.info("Copying ssh public key to internal storage.")
        if self.execute(command=("mount", self._root_partition,
                                 "/mnt/sdb_root"),
                        timeout=self._SSH_SHORT_GENERIC_TIMEOUT, ) is False:
            logging.critical("Failed mounting internal storage.")
            return False
        # Ignore return value: directory might exist
        self.execute(command=("mkdir", "/mnt/sdb_root/root/.ssh"),
                     timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if self.execute(command=("cat", "/root/.ssh/authorized_keys",
                                 ">>", "/mnt/sdb_root/root/" +
                                 ".ssh/authorized_keys"),
                        timeout=self._SSH_SHORT_GENERIC_TIMEOUT, ) is False:
            logging.critical("Failed writing public key to device.")
            return False
        if self.execute(command=("sync",),
                        timeout=self._SSH_SHORT_GENERIC_TIMEOUT, ) is False:
            logging.critical("Failed flushing internal storage.")
            return False
        if self.execute(command=("umount", "/mnt/sdb_root"),
                        timeout=self._SSH_SHORT_GENERIC_TIMEOUT, ) is False:
            logging.critical("Failed unmounting internal storage.")
            return False
        logging.info("Public key written successfully to device.")
        return True

    def _confirm_image(self, file_name):
        """
        Confirm that the image booted is the one the one received.
        """
        try:
            build_id_row = self.execute(
                command=("cat", "/etc/os-release", "|", "grep", "BUILD_ID"),
                timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
            # The string expected is in the format:
            # "BUILD_ID=xxxxx\n"
            # and we want to match the xxxxxx against file_name
            if build_id_row.split("=")[1].strip() in file_name:
                return True
        except (AttributeError, IndexError) as error:
            logging.warn("Error: {0}\n".format(error))
        logging.warn("Could not find correct build id:\n"
                     "Image used: {0}\n".format(file_name) +
                     "Found:\n {0}\n".format(build_id_row))
        return False

    def write_image(self, file_name):
        """
        Method for writing an image to a device.
        """
        # NOTE: it is expected that the image is located somewhere
        # underneath /home/jenkins therefore symlinks probably will not work
        # The /home/jenkins path is exported as nfs and mounted remotely as
        # /mnt/img_data_nfs
        if not os.path.isfile(file_name):
            logging.critical("File not found.\n{0}".format(file_name))
            return False
        return self._enter_mode(self._service_mode) and \
            self._write_image(nfs_file_name=os.path.abspath(file_name).
                              replace("home/jenkins", "mnt/img_data_nfs")) and \
            self._install_tester_public_key() and \
            self._enter_mode(self._test_mode) and \
            self._confirm_image(file_name)

    def execute(self, command, timeout, environment=(), user="root"):
        """
        Runs a command on the device and returns log and errorlevel.
        """
        return Ssh.execute(dev_ip=self.get_registered_lease(), timeout=timeout,
                           user=user, environment=environment, command=command)

    def push(self, source, destination, user="root"):
        """
        Deploys a file from the local filesystem to the device (remote).
        """
        return Scp.push(self.get_registered_lease(),
                        source=source, destination=destination, user=user)