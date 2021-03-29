Introduction
============

``virt_up`` creates virtual machines existing digitally signed OS images,
which are downloaded and cached. A *template virtual machine* is created from
the downloaded image. Optionally, an ansible playbook may be executed to
further customize the templates. Virtual machines are then cloned from the
templates to quickly create new instances.

A login user is created and the ssh keys to connect to the new virtual
machines are automatically generated. The login user is given sudo access.
Connection information is stored in a json meta data file for each virtual
machine created. An ansible inventory file is created for the templates and
instances to make it easier to run ansible playbooks for further
configuration.

Normally, you want to run ``virt_up`` as a regular user, not root.

By default, ``virt_up`` will create image files in the ``default`` libvirt
storage pool (``/var/lib/libvirt/images``). See the ``pool`` option Settings
to change this. Be sure you have read and write access to the configured
libvirt storage pool.
