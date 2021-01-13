virt-up
=======

**virt-up** is a command line tool for creating virtual machines
quickly on a local KVM hypervisor using **virt-builder**, **virt-sysprep**,
and **virt-install**.

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

    usage: virt-up [--name] <name> --template <template> [create-options]
           virt-up [--name] <name> --login [--sftp|--command "<command>"]
           virt-up [--name] <name> --playbook <playbook>
           virt-up [--name] <name> --delete | --delete --all
           virt-up --init [--force]
           virt-up --list [--all]
           virt-up --show-templates | --show-paths

    positional arguments:
      <name>                instance name

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      --init                initialize configuration files
      --list                list instances
      --show-templates      show template definitions
      --show-paths          show configuration and data paths
      --delete              delete the instance
      --login               login to a running instance
      --playbook PLAYBOOK   run ansible playbook on instance
      -t <template>, --template <template>
                            template name (default: <name>)
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
      --dns-domain <dns-domain>
                            dns domain name
      --sftp                --login with sftp
      --command <command>   --login ssh command
      --no-clone            build template instance only
      --no-inventory        exclude instance from the virt-up ansible inventory
                            file
      --all                 include template instances
      --yes                 answer yes to interactive questions
      --quiet               show less output
      --debug               show debug tracing
      --force               overwrite files


Configuration files
===================

**virt-up** reads settings from INI formatted configuration files.  The settings
are divided into common settings and template definitions.

System defined configurations are located in the directory '/etc/virt-up'.

User defined configurations are located via a path set by an environment
variable (see _virt_config_ below).

Common Settings
---------------

The ``settings.cfg`` file contains settings that are used when creating any
virtual machine. The file should contain one section called ``[common]``.

The following fields are supported:

**pool**
  The libvirt storage pool to write images. (default: ``default``)

**username**
  The username of the user account created by **virt-up** when creating
  new template instances (default: ``virt``)

**dns-domain**
  The DNS domain used for new template instance hostnames. (default: None)

**address-source**
  The method used to detect the instance IP address. Supported values are:

*  ``agent`` - Queries the qemu guest agent to obtain the IP address (``default``)
*  ``lease`` - Parses the DHCP lease file to obtain the IP address (requires a libvirt managed DHCP server in the hypvervisor host)
*  ``arp``   - Examines the arp table on the hypvervisor host
*  ``dns``   - Uses the result of a DNS lookup for the guest host name.

**image-format**
  The image format. Supported values are ``qcow2``, and ``raw``. (default: ``qcow2``)

**virt-builder-args**
  Extra arguments for ``virt-builder``. (default: None)

**virt-sysprep-args**
  Extra arguments for ``virt-sysprep``. (default: None)

**virt-install-args**
  Extra arguments for ``virt-install``. (default: None)

**template-playbook**
  Optional ansible playbook to be executed on newly created template instances. (default: None)

**instance-playbook**
  Optional ansible playbook to be executed on newly created instances. (default: None)

These fields can be overridden by individual template definitions.

Template definitions
--------------------

Template definitions are read from the files located in the ``templates.d``
sub-directory.

Provide one section for each template definition. The section name is the name
for the template definition and is used for the **virt-up** ``--template``
option. The following fields are supported:

**desc**
  A text description, show by ``--list-templates``.

**os-version**
  The **virt-builder** ``<os_version>`` name. See ``virt-builder --list`` for available names.

**os-type**
  The **virt-install** ``--os-type``

**os-variant**
  The **virt-install** ``--os-variant``. See ``osquery-info os`` for available names.

**arch**
  The target architecture.

**virt-builder-args**
  Template specific extra arguments for ``virt-builder``. (default: None)

**virt-sysprep-args**
  Template specific extra arguments for ``virt-sysprep``. (default: None)

**virt-install-args**
  Template specific extra arguments for ``virt-install``. (default: None)

**template-playbook**
  Optional ansible playbook to be executed on newly created template instances. (default: None)

**instance-playbook**
  Optional ansible playbook to be executed on newly created instances. (default: None)

In addition, the template configuration can override fields set in the ``common``
section of the settings.cfg file.


Additional Notes
================

General notes
-------------

* If the hypvervisor host uses a bridged network or a seperate network adapter
  for guest systems, the host's arp table may not contain the ip address of the
  guest.

* Values set in the template configuration sections will override the common
  settings

Ubuntu installation notes
-------------------------

Linux images are not readable by regular users on recent Ubuntu distributions,
which breaks the ability of libguestfs to modify guest images. Update the
permissions with the `dpkg-statoverride` command to be able to run the
libguestfs tools as a regular user:

    $ for image in /boot/vmlinu*; do sudo dpkg-statoverride --update --add root root 0644 $image || true; done

You will need to run this *everytime* the kernel is updated.

Xen
---

virt-up can create and manage guests using the Xen hypervisor.

* To use a Xen hypervisor, set the LIBVIRT_DEFAULT_URI to use the xen system

        LIBVIRT_DEFAULT_URI=xen:///system

  and set ``virt-install-args`` to include '--hvm'.

        virt-install-args = '--hvm ...'

* Xen does not support accessing guest information via the qemu-agent

* Some guest images are built with Xen support, but their device configurations
  are unloaded during initial boot processinmg. A boot parameter
  `xen_emul_unplug=never` must be added to the guest boot cmdline.  This is usually
  done by updating the grub configuration when building the template.

        virt-builder-args = ...
          --edit "/etc/default/grub:s/GRUB_CMDLINE_LINUX=\"\"/GRUB_CMDLINE_LINUX=\"xen_emul_unplug=never\"/"
          --run-command 'grub-mkconfig -o /boot/grub/grub.cfg'
          ...

Environment Variables
=====================

The following environment variables are used by **virt-up**

**LIBVIRT_DEFAULT_URI**
  URI to access libvirt. Defaults to ``qemu://session``

*virt_config*

**VIRTUP_CONFIG_HOME**
  Path to **virt-up** configuration files. Defaults to
  ``$XDG_CONFIG_HOME/virt-up``

**XDG_CONFIG_HOME**
  Path to **virt-up** configuration files. Defaults to the xdg standard location
    ``$HOME/.local/share/virt-up``

*virt_data*

**VIRTUP_DATA_HOME**
  Path to **virt-up** run-data files created by virt-up.  Defaults to
  ``$XDG_DATA_HOME/virt-up``

**XDG_DATA_HOME**
  Path to **virt-up** run-data files created by virt-up.  Defaults to the xdg
  standard location ``$HOME/.local/share/virt-up``

FILES
=====

The following files are created or referenced by **virt-up**

Configuration related
---------------------

- /etc/virt-up/settings.cfg
- /etc/virt-up/templates.d/*
- /etc/virt-up/scripts/*
- /etc/virt-up/playbooks/*

The following override the files found in /etc/virt-up

- *virtup_config*/settings.cfg
- *virtup_config*/templates.d/*
- *virtup_config*/scripts/*
- *virtup_config*/playbooks/*

Runtime persistent data files
-----------------------------

- *virtup_data*/sshkeys/*``name``*
- *virtup_data*/macaddrs.json
- *virtup_data*/instance/*``name``*.json
- *virtup_data*/inventory.yaml

Guest system image files
------------------------

- *pool*/TEMPLATE-*template disk images*
- *pool*/*virtual guest disk images*

Transient runtime
-----------------

- /var/run/user/*uid*/virt-up.lock
  If the above directory is not available
- /tmp/virt-up.lock

See Also
========

  virt-builder
  virt-install
  virt-sysprep
  libvirt
