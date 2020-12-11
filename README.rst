virt-up
=======

**virt-up** is a command line tool for creating virtual machines
quickly on a local KVM hypervisor using **virt-builder**, **virt-sysprep**,
and **virt-install**.

Virtual machines are created from existing digitally signed OS images, which
are downloaded and cached. A template virtual machine is created from the
downloaded image. Optionally, an ansible playbook is executed to further
customize the templates. Virtual machines are cloned from the templates
to quickly create new instances.

A login user and the ssh keys to connect to the new virtual machines are
created automatically. The login user is given sudo access. Connection
information is stored in a json meta data file for each virtual machine
created.  An ansible inventory file is created for the templates and
instances to make it easier to run ansible playbooks for further
configuration.

Normally you should run **virt-up** as a regular user, not root.

By default, **virt-up** will create image files in the ``default`` libvirt
storage pool (``/var/lib/libvirt/images``). See the ``pool`` option Settings to
change this.  Be sure you have read and write access to the configured libvirt
storage pool.

System requirements
===================

* Python 3.6 or better
* Local KVM hypervisor
* Python libvirt package
* ``qemu-img``, ``virt-builder``, ``virt-sysprep``, ``virt-install``

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
                            template definition name (default: <name>)
      --root-password <root-password>
                            root password (default: random)
      --user <user>         username (default: virt)
      --password <password>
                            password (default: random)
      --size <size>         instance disk size (default: image size)
      --memory <memory>     instance memory (default: 512)
      --vcpus <vcpus>       instance vcpus (default: 1)
      --graphics <graphics>
                            instance graphics type (default: none)
      --command <command>   --login ssh command
      --no-clone            build template instance only, --name is ignored
      --all                 include template instances
      --yes                 answer yes to interactive questions
      --quiet               show less output
      --debug               show debug tracing


Ubuntu installation notes
=========================

Linux images are not readable by regular users on recent Ubuntu distributions,
which breaks the ability of libguestfs to modify guest images. Update the
permissions with the `dpkg-statoverride` command to be able to run the
libguestfs tools as a regular user:

    $ for image in /boot/vmlinu*; do sudo dpkg-statoverride --update --add root root 0644 $image || true; done

You will need to run this *everytime* the kernel is updated.

Settings
========

**virt-up** reads settings for INI formatted configuration files.
The following files are read in order, when present.

* ``/etc/virt-up/settings.cfg``
* ``$XDG_CONFIG_HOME/virt-up/settings.cfg`` (``$XDG_CONFIG_HOME`` is ``$HOME/.config`` if not set)

The ``settings.cfg`` should contain one section called ``[site]``. The following fields are supported:

pool
  The libvirt storage pool to write images. (default: ``default``)

username
  The username of the user account created by **virt-up** when creating
  new template instances (default: ``virt``)

dns-domain
  The DNS domain used for new template instance hostnames. (default: None)

address-source
  The method used to detect the instance IP address. Supported values are
  ``agent``, ``lease``, ``arp``, ``dns``. (default: ``agent``)

image-format
  The image format. Supported values are ``qcow2``, and ``raw``. (default: ``qcow2``)

virt-builder-args
  Extra arguments for ``virt-builder``. (default: None)

virt-sysprep-args
  Extra arguments for ``virt-sysprep``. (default: None)

virt-install-args
  Extra arguments for ``virt-install``. (default: None)

template-playbook
  Optional ansible playbook to be executed on newly created template instances. (default: None)

instance-playbook
  Optional ansible playbook to be executed on newly created instances. (default: None)

Template definitions
====================

Additional template-definitions can be created with **virt-up** by providing template defintions
in the following files:

* ``/etc/virt-up/templates.cfg``
* ``$XDG_CONFIG_HOME/virt-up/templates.cfg`` (``$XDG_CONFIG_HOME`` is ``$HOME/.config`` if not set)

The ``templates.cfg`` files are INI formatted text files. Provide one section
for each template definition. The section name is the template definition name used in
virt-up ``--template`` option. The following fields are supported:

desc
  A text description, show by ``--list-templates``.

os-version
  The **virt-builder** ``<os_version>`` name. See ``virt-builder --list`` for available names.

os-type
  The **virt-install** ``--os-type``

os-variant
  The **virt-install** ``--os-variant``. See ``osquery-info os`` for available names.

arch
  The target architecture.

virt-builder-args
  Template specific extra arguments for ``virt-builder``. (default: None)

virt-sysprep-args
  Template specific extra arguments for ``virt-sysprep``. (default: None)

virt-install-args =
  Template specific extra arguments for ``virt-install``. (default: None)

template-playbook
  Optional ansible playbook to be executed on newly created template instances. (default: None)

instance-playbook
  Optional ansible playbook to be executed on newly created instances. (default: None)
