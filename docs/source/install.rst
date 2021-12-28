Installation guide
==================

Verify your system supports virtualization. On Intel based systems, run ``grep
-c vmx /proc/cpuinfo`` to verify the presence of the **vmx** flags. On AMD
based systems, run ``grep -c svm /proc/cpuinfo``. See `KVM processor support
<https://www.linux-kvm.org/page/Processor_support>`_ for more information.

Debian/Ubuntu
-------------

This guide shows how to install KVM virtualization and **virt-up** on Debian
and Ubuntu systems.  Virtualization maybe installed on graphical desktop or a
non-graphical server.

See `Debian KVM <https://wiki.debian.org/KVM>`_ for more information.

Installing KVM
^^^^^^^^^^^^^^^^

Install virtualization packages with **apt**::

    $ sudo apt install \
        qemu-system libvirt-clients libvirt-daemon-system \
        virtinst qemu-utils libguestfs-tools libvirt-dev \
        osinfo-db-tools

Tip: Specify the ``--no-install-recommends`` apt option to avoid installing
graphical packages when installing a server.

Add users to the **libvirt** and **kvm** groups to grant them permission to
manage virtual machines on the hypervisor::

    $ sudo useradd -a -G libvirt <username>
    $ sudo useradd -a -G kvm <username>

This takes affect on your next login.

Download and install the most recent OS Info Database::

    $ wget https://releases.pagure.org/libosinfo/osinfo-db-<VERSION>.tar.xz
    $ sudo osinfo-db-import --local osinfo-db-<VERSION>.tar.xz

The graphical **virt-manager** tool is useful to have on a desktop system. If
the kvm hypervisor is running on a server, you can install **virt-manager** on
your desktop and connect to the server via ssh::

    $ sudo apt install virt-manager   # on your desktop

Set your ``LIBVIRT_DEFAULT_URI`` environment variable if you are using a non
default path.

At this point, verify you are able to create new guests with **virt-manager**
and be able to manage the guests with **virsh**.

Linux kernel image permissions on Ubuntu
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linux images are not readable by regular users on Ubuntu distributions.  This
breaks the ability of libguestfs to modify guest images unless running as root.

Fix the kernel image permissions with the `dpkg-statoverride` command::

    $ sudo dpkg-statoverride --update --add root root 0644 /boot/vmlinuz-$(uname -r)

To fix all of the installed images::

    $ for i in /boot/vmlinuz-*; do sudo dpkg-statoverride --update --add root root 0644 $i; done

To fix the permissions automatically with each new kernel version, create the
file `/etc/kernel/postinst.d/statoverride` script. Be sure the ``statoverride``
script is executable::

    #!/bin/sh
    version="$1"
    [ -z "${version}" ] && exit 0
    dpkg-statoverride --update --add root root 0644 /boot/vmlinuz-${version}

For more information see `Ubuntu bug 759725`_.

.. _Ubuntu bug 759725: https://bugs.launchpad.net/ubuntu/+source/linux/+bug/759725

Installing **virt-up**
^^^^^^^^^^^^^^^^^^^^^^

**virt-up** must be installed on the system running the KVM virtualization
since it uses the **libguestfs** tools to prepare the virtual machine image
files.

Install Python **pip**::

    # apt install python3-pip

Install **virt-up** with Python **pip**.  This can be installed as root for
all users, or installed with **pip** as a regular user. If installed as a
regular user, be sure ``$HOME/.local/bin`` is included in your ``$PATH``::

    $ pip3 install virt-up

Create **virt-up** setting and template files. The path of the configuration
files can be found by running::

    $ virt-up show paths | grep CONFIG

The per-user configuration files are written to the directory
``~/.config/virt-up/``. Set the ``VIRTUP_CONFIG_HOME`` environment variable to
select an alternate location.

Run ``virt-up show templates`` to see the available template names.

Run ``virt-up create <name> --template <name>`` to create a virtual machine.

