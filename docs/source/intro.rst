Introduction
============

**virt-up** is a command line tool for creating virtual machines quickly on a
libvirt based hypervisor. **virt-up** supports qemu/KVM and XEN virtualization.

**virt-up** runs the **libquestfs** tool **virt-builder** download (and cache)
digitally signed virtual machine images.  A *base virtual machine* is created
from the downloaded image and is customized with **virt-sysprep**.  Virtual
machines are then cloned from the base virtual machine to quickly create new
virtual machines.

**virt-up** automatically creates a login user and the ssh keys to connect to
the new virtual machines.  The login user is given sudo access. Connection
information is stored in a json meta data file for each virtual machine
created.

An ansible inventory file is created for the virtual machines to make it easier
to run ansible playbooks for further configuration.

By default, **virt_up** will create image files in the **default** libvirt
storage pool, e.g., ``/var/lib/libvirt/images``. See the ``pool`` option
Settings to change this. Be sure you have read and write access to the
configured libvirt storage pool.

Normally, you want to run ``virt_up`` as a regular user, not root.
