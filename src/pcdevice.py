# Copyright (c) 2013, 2014, 2015 Intel, Inc.
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
import sys

from aft.device import Device
from aft.plugins.pc.ssh import Ssh
from aft.plugins.pc.scp import Scp

from pem.main import main as pem_main

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
    _IMG_NFS_MOUNT_POINT = "/mnt/img_data_nfs"
    _ROOT_PARTITION_MOUNT_POINT = "/mnt/target_root/"

    @classmethod
    def init_class(cls, init_data):
        """
        Initializer for class variables and parent class.
        """
        try:
            logging.debug("PCDevice class init_data: {0}".
                          format(init_data))
            cls._leases_file_name = init_data["leases_file_name"]
            cls._root_partition = init_data["root_partition"]
            cls._service_mode_name = init_data["service_mode"]
            cls._test_mode_name = init_data["test_mode"]
            cls._registered_lease = None
            return Ssh.init() and Scp.init()
        except KeyError as error:
            logging.critical("Error initializing PC Device Class {0}."
                             .format(error))
            return False

    def __init__(self, device_descriptor, channel):
        super(PCDevice, self).__init__(device_descriptor=
                                       device_descriptor,
                                       channel=channel)
        self.pem_interface = device_descriptor["pem_interface"]
        self.pem_port = device_descriptor["pem_port"]
        self._test_mode = {
            "name": self._test_mode_name,
            "sequence": device_descriptor["catalog_entry"]
                                         ["test_mode_keystrokes"]}
        self._service_mode = {
            "name": self._service_mode_name,
            "sequence": device_descriptor["catalog_entry"]
                                         ["service_mode_keystrokes"]}
        self._target_device = \
            device_descriptor["catalog_entry"]["target_device"]

    @classmethod
    def get_all_registered_leases(cls):
        """
        Returns all the current leases.
        """
        with open(cls._leases_file_name) as leases_file:
            return leases_file.readlines()

    @classmethod
    def get_registered_leases_by_mac(cls, mac):
        """
        Returns the leased ip for a specific mac.
        """
        leased_ips = []
        for lease in cls.get_all_registered_leases():
            requestor_mac, leased_ip = lease.split()[1:3]
            if requestor_mac == mac:
                logging.info("Found device with MAC {0}".format(mac) +
                             " and IP {0}".format(leased_ip))
                leased_ips.append(leased_ip)
        if len(leased_ips) is 0:
            logging.critical("Not found any IP lease for device with"
                             "MAC {0}".format(mac))
        return leased_ips

    def get_registered_leases(self):
        """
        Returns the leased ip of the current device.
        """
        return self.get_registered_leases_by_mac(mac=self.dev_id)

    @classmethod
    def _by_ip_is_in_mode(cls, dev_ip, mode):
        """
        Check if the device with given ip is responsive to ssh
        and in the specified mode.
        """
        logging.debug("Trying to ssh into {0} to test the mode.".format(dev_ip))
        retval = Ssh.execute(dev_ip=dev_ip,
                             command=("cat", "/proc/version", "|",
                                      "grep", mode["name"]),
                             timeout=cls._SSH_SHORT_GENERIC_TIMEOUT, )
        if retval is None or retval.returncode is not 0:
            logging.debug("Ssh failed.")
        elif mode["name"] not in retval.stdoutdata:
            logging.debug("Device not in \"{0}\" mode.".format(mode["name"]))
        else:
            logging.debug("Device in \"{0}\" mode.".format(mode["name"]))

        return retval is not None and \
               retval.returncode is 0 and \
               mode["name"] in retval.stdoutdata

    def by_ip_is_in_service_mode(self, dev_ip):
        """
        Check if the device is in service mode.
        """
        return self._by_ip_is_in_mode(dev_ip=dev_ip, mode=self._service_mode)

    def by_ip_is_in_test_mode(self, dev_ip):
        """
        Check if the device is in test mode.
        """
        return self._by_ip_is_in_mode(dev_ip=dev_ip, mode=self._test_mode)

    @classmethod
    def _by_ip_is_responsive(cls, dev_ip):
        """
        Check if the device is in service mode.
        """
        logging.debug("Trying to ssh into {0}.".format(dev_ip))
        result = Ssh.execute(dev_ip=dev_ip,
                             command=("echo", "$?"),
                             timeout=cls._SSH_SHORT_GENERIC_TIMEOUT, )
        logging.debug("result: {0}".format(result))
        if (result is None) or (result.returncode is not 0):
            logging.debug("Ssh failed.")
        else:
            logging.debug("Ssh successful.")
        return (result is not None) and (result.returncode is 0)

    def _is_in_mode(self, mode):
        """
        Check if the device is responsive to ssh
        and in specified mode.
        """
        return self._by_ip_is_in_mode(mode=mode,
                                    dev_ip=self.get_registered_leases())

    def is_in_service_mode(self):
        """
        Check if the device is in service mode.
        """
        return self._is_in_mode(mode=self._service_mode)

    def is_in_test_mode(self):
        """
        Check if the device is in service mode.
        """
        return self._is_in_mode(mode=self._test_mode)

    def _is_responsive(self):
        """
        Check if the device is responsive to ssh
        and in specified mode.
        """
        leases = self.get_registered_leases()
        for lease in leases:
            if self._by_ip_is_responsive(dev_ip=lease):
                return lease
        return None

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
        For a limited amount of time, try to assess if the device
        is in the mode requested.
        """
        logging.info("Check if device is in mode {0} .".format(mode["name"]))
        for _ in range(self._MODE_TEST_TIMEOUT / self._POLLING_INTERVAL):
            responsive_ip = self._is_responsive()
            if responsive_ip is not None:
                self._registered_lease = responsive_ip
                return self._by_ip_is_in_mode(mode=mode, dev_ip=responsive_ip)
            else:
                logging.info("Device not responding - waiting {0} seconds."
			     .format(self._POLLING_INTERVAL))
                time.sleep(self._POLLING_INTERVAL)
        logging.info("Device {0} is not in mode {1} ."
                     .format(self.get_registered_leases(), mode["name"]))
        return False

    def _enter_mode(self, mode):
        """
        Tries to put the device into the specified mode.
        """
        # Attempts twice but one should be sufficient.
        for _ in range(2):
            self._power_cycle()
            logging.debug("Going to execute:\n" +
			  "pem" +
                          " --interface {0}".format(self.pem_interface) +
                          " --port {0}".format(self.pem_port) +
                          " --playback {0}".format(mode["sequence"]))
            pem_main(["pem",
                      "--interface", self.pem_interface,
                      "--port", self.pem_port,
                      "--playback", mode["sequence"]])
            logging.info("Checking for device in mode \"{0}\" ."
                         .format(mode["name"]))
            if self._wait_for_mode(mode=mode):
                logging.info("Found device in mode \"{0}\" ."
                             .format(mode["name"]))
                return True
            else:
                logging.info("Device in mode \"{0}\" was not found."
                             .format(mode["name"]))
        logging.critical("Unable to get device {0} in mode \"{1}.\""
                         .format(self.dev_id, mode["name"]))
        return False

    def _write_image(self, nfs_file_name):
        """
        Writes image into the internal storage of the device.
        """
        time.sleep(7)
        logging.info("Mounting the nfs containing the image to flash.")
	result = self.execute(
            command=("mount", self._IMG_NFS_MOUNT_POINT),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT,
        )
        if result is None:
            logging.critical("Failed to interact with the device.")
            return False
        logging.info("Testing for availability of image {0} ."
                     .format(nfs_file_name))
        result = self.execute(
            command=("[", "-f", nfs_file_name, "]", "&&",
                     "echo", "found", "||", "echo", "missing"),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT,
            verbose=True,
        )
        logging.info(result)
        if result is not None and "found" in result.stdoutdata:
            logging.info("Image found.")
        else:
            logging.critical("Image \"{0}\" not found."
                             .format(nfs_file_name))
            return False
        logging.info("Writing image {0} to internal storage."
                     .format(nfs_file_name))
        result = self.execute(command=("bmaptool", "copy", "--nobmap",
                                       nfs_file_name, self._target_device),
                              timeout=self._SSH_IMAGE_WRITING_TIMEOUT,)
        if result is not None and result.returncode is 0:
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
        self.execute(command=("partprobe", self._target_device),
                     timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        logging.info("Copying ssh public key to internal storage.")
        result = self.execute(
            command=("mount", self._target_device + self._root_partition,
                     self._ROOT_PARTITION_MOUNT_POINT),
                     timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None or result.returncode is not 0:
            logging.critical("Failed mounting internal storage.\n{0}"
                             .format(result))
#            return False
        # Identify the home of the root user
        result = self.execute(
            command=("cat",
                     os.path.join(self._ROOT_PARTITION_MOUNT_POINT,
                                  "etc/passwd"), "|",
                     "grep", "-e", '"^root"', "|",
                     "sed", "-e" '"s/root:.*:root://"', "|",
                     "sed", "-e" '"s/:.*//"'),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None or result.returncode is not 0:
            logging.critical("Failed to identify the home of the root user.")
            return False
        else:
            root_user_home = result.stdoutdata.rstrip().strip("/")
        # Ignore return value: directory might exist
        result = self.execute(
            command=("mkdir", os.path.join(self._ROOT_PARTITION_MOUNT_POINT,
                     root_user_home, ".ssh")),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None:
            logging.critical("Failed to ssh into the device.")
        elif result.returncode is not 0:
            logging.info(".ssh directory already present for root user.")
        result = self.execute(
            command=("chmod", "700",
                     os.path.join(self._ROOT_PARTITION_MOUNT_POINT,
                     root_user_home, ".ssh")),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None:
            logging.critical("Failed to ssh into the device.")
        # replicate the public key used for logging in as root
        result = self.execute(
            command=("cat", "/root/.ssh/authorized_keys", ">>",
                     os.path.join(self._ROOT_PARTITION_MOUNT_POINT,
                     root_user_home, ".ssh/authorized_keys")),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None or result.returncode is not 0:
            logging.critical("Failed writing the public key to the device.")
            return False
        result = self.execute(
            command=("chmod", "600",
                     os.path.join(self._ROOT_PARTITION_MOUNT_POINT,
                                  root_user_home, ".ssh/authorized_keys")),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None:
            logging.critical("Failed to ssh into the device.")
            return False
        result = self.execute(
            command=("sync",), timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None or result.returncode is not 0:
            logging.critical("Failed flushing internal storage.")
            return False
        result = self.execute(
            command=("umount", self._ROOT_PARTITION_MOUNT_POINT),
            timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
        if result is None or result.returncode is not 0:
            logging.critical("Failed unmounting internal storage.")
            return False
        logging.info("Public key written successfully to device.")
        return True

    def _confirm_image(self, file_name):
        """
        Confirm that the image booted is the one the one received.
        """
        try:
            result = self.execute(
                command=("cat", "/etc/os-release", "|", "grep", "BUILD_ID"),
                timeout=self._SSH_SHORT_GENERIC_TIMEOUT, )
            if result is None or result.returncode is not 0:
                logging.critical("Failed locating the BUILD_ID value")
                return False
            build_id_row = result.stdoutdata
            # The string expected is in the format:
            # "BUILD_ID=xxxxx\n"
            # and we want to match the xxxxxx against file_name
            if file_name.split(".")[0] in build_id_row.split("=")[1].strip():
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
        # underneath /home/testeri, therefore symlinks outside of it
        # will not work
        # The /home/tester path is exported as nfs and mounted remotely as
        # _IMG_NFS_MOUNT_POINT
        if not os.path.isfile(file_name):
            logging.critical("Test file {0} not found.".format(file_name))
        elif not self._enter_mode(self._service_mode):
            logging.critical("Could not put device in service mode.")
        elif not self._write_image(nfs_file_name=
                                   os.path.abspath(file_name).
                                     replace("home/tester",
                                             self._IMG_NFS_MOUNT_POINT)):
            logging.critical("Could not write image to storage.")
        elif not self._install_tester_public_key():
            logging.critical("Could not install tester public key.")
        elif not self._enter_mode(self._test_mode):
            logging.critical("Could not enter test mode.")
#        elif not self._confirm_image(file_name):
#            logging.critical("Could not confirm image.")
        else:
            logging.info("Image {0} written.".format(file_name))
            return True
        return False

    def execute(self, command, timeout, environment=(),
                user="root", verbose=False):
        """
        Runs a command on the device and returns log and errorlevel.
        """
        return Ssh.execute(dev_ip=self._registered_lease, timeout=timeout,
                           user=user, environment=environment, command=command,
                           verbose=verbose)

    def push(self, source, destination, user="root"):
        """
        Deploys a file from the local filesystem to the device (remote).
        """
        return Scp.push(self._registered_lease, source=source,
                        destination=destination, user=user)
