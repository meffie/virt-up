virt-up
=======

**virt-up** is a command line tool for quickly creating virtual machines
on a local KVM hypervisor using **virt-builder**, **virt-sysprep**,
and **virt-install**.

Virtual machines are created from existing digitally signed OS images, which
are downloaded and cached. A template virtual machine is created from the
downloaded image. Virtual machines are cloned from the template machine to
create new virtual machines quickly.

A login user and the ssh keys to connect to the new virtual machines are
created automatically. The login user is given sudo access. Connection
information is stored in a json meta data file for each virtual machine
created.

System requirements
===================

* Python 3.6
* Local KVM (or XEN) libvirt hypervisor
* Python libvirt
* libguestfs-tools: virt-builder, virt-sysprep
* virt-manager: virt-install

Usage
=====

::

    usage: virt-up [--name] <name> [--template <template>] [options]
                --list [--all] | --list-templates
                --login [--name] <name> [--command "<command>"]
                --delete [--name] <name> | --delete --all

    positional arguments:
    <name>                instance name

    optional arguments:
    -h, --help            show this help message and exit
    --version             show program's version number and exit
    --list                list instances
    --list-templates      list template names
    --delete              delete the instance
    -t <template>, --template <template>
                            template name (default: <name>)
    --size <size>         instance disk size (default: image size)
    --memory <memory>     instance memory (default: 512)
    --vcpus <vcpus>       instance vcpus (default: 1)
    --graphics <graphics>
                            instance graphics type (default: none)
    --command <command>   --login ssh command
    --no-clone            build template instance only
    --all                 include template instances
    --images              show available images
    --quiet               show less output
    --debug               show debug tracing

Settings
========

**virt-up** will load settings from an INI formatted file
``/etc/virt-up/settings`` and ``$HOME/.config/virt-up/settings``.

See ``virt_up/config.py`` for available setting names and default values.
