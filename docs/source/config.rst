Configuration
=============

``virt-up`` reads settings from INI formatted configuration files.  The settings
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

**network**
  The libvirt network, for example ``bridge=br0``. (default: None)

**username**
  The username of the user account created by **virt-up** when creating
  new template instances (default: ``virt``)

**memory**
  Instance memory, in KB. Default is 512.

**vcpus**
  Number of virtual cpus. Default is 1.

**graphics**
  Graphics type. Default is 1.

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

**memory**
  Instance memory, in KB. Default is set in the common section.

**vcpus**
  Number of virtual cpus. Default is set in the common section.

**graphics**
  Graphics type. Default is set in the common section.

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
