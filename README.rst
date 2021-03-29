virt-up
=======

``virt-up`` is a command line tool for creating virtual machines quickly on a
local KVM hypervisor using ``virt-builder`` and ``virt-install``

Virtual machines are created from existing digitally signed OS images, which
are downloaded and cached. A *template virtual machine* is created from the
downloaded image. Optionally, an ansible playbook is executed to further
customize the templates. Virtual machines are then cloned from the templates
to quickly create new instances.

A login user and the ssh keys to connect to the new virtual machines are
created automatically. The login user is given sudo access. Connection
information is stored in a json meta data file for each virtual machine
created.  An ansible inventory file is created for the templates and
instances to make it easier to run ansible playbooks for further
configuration.

`Complete documentation here <https://virt-up.readthedocs.io/en/latest/index.html>`_

System requirements
===================

* Python 3.6+
* libvirt based hypervisor (qemu/KVM)
* libvirt, python-libvirt
* libguestfs-tools (``virt-builder``, ``virt-sysprep``, ``virt-clone``)
* libosinfo (``osinfo-db``)
* qemu-utils (``qemu-img``)
* virt-manager (``virt-install``)
