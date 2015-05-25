AFT - Automated Flasher & Tester- PC Plugin - Documentation
===========================================================

Overview
--------
AFT is a tool for automated provisioning and testing.
Its goal is to both standardize and simplify the testing on a variety
of devices, while keeping minimal the cost and complexity of the setup.
In particular, it strives to use only inexpensive off-the shelf
HW components and to keep one single configuration that can be used
by both large testing farms and individual testers/developers.

This plugin deals with DUTs that either are or can be treated
like PCs, iow they meet the following criteria:
* can receive input from an USB keyboard
* obtain an IP from a DHCP server on the local network
* run an ssh server
* can boot from 2 different devices (can be any combination of internal
  storage, USB disk, SD card)

For overall documentation on aft, please refer to the aft-core
package, found in the same location as this plugin.



How it works
------------

From somewhere (typically a separate package), the testing harness
has received a catalog file, which describes the HW models that are
supported.

During the harness configuration phase, a topology file was created.
It describes the individual units connected to the testing harness
and how to identify/operate them: 
id, model, corresponding ports, power cutter, etc.

DUTs are addressed by an unique identifier. In this case the MAC address.
DUTs are connected to a dedicated local network where the testing harness
runs a DNS/DHCP server (dnsmasquerade).

When the tester is given the name of a file containing SW to verify,
it uses the catalog descriptor to check if any of the know models
matches the sw image provided.

In case of positive answer, it looks up the topology file, to assess
if any of the devices that are present belongs to the model identified
during the previous step. 

Then it tries to power up the DUT, using the plugin that controls the cutter
associated with the device.

Following power-on, the testing harness uses the Peripheral EMulator
to set the BIOS of the DUT to a known state, in particular by setting the
boot device to be the one containing a specialized boot image.

Such supporting image will provide the stable environment for deploying
the image to be tested.

Once the support image has booted, it mounts an nfs share provided by
the testing harness. This nfs share contains the image to be written
to the DUT.

After writing the image, the final step before booting in it, is to
inject an ssh public key for the root user, so that the testing harness
will be able to log into the DUT regardless if the original build contained
a usable key.

The final phase is to execute the test cases, according to the test plan
specified.
