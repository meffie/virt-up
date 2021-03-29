Installation
============


Debian/Ubuntu
^^^^^^^^^^^^^

Ubuntu installation notes
-------------------------

Linux images are not readable by regular users on Ubuntu distributions.  This
breaks the ability of libguestfs to modify guest images unless running as root.

Fix the kernel image permissions with the `dpkg-statoverride` command::

    $ sudo dpkg-statoverride --update --add root root 0644 /boot/vmlinuz-$(uname -r)

To fix all of the installed images::

    $ for i in /boot/vmlinuz-*; do sudo dpkg-statoverride --update --add root root 0644 $i; done

To fix the permissions automatically with each new kernel version, create the file
`/etc/kernel/postinst.d/statoverride`::

    #!/bin/sh
    version="$1"
    # passing the kernel version is required
    [ -z "${version}" ] && exit 0
    dpkg-statoverride --update --add root root 0644 /boot/vmlinuz-${version}

For more information see `Ubuntu bug 759725`_.

.. _Ubuntu bug 759725: https://bugs.launchpad.net/ubuntu/+source/linux/+bug/759725
