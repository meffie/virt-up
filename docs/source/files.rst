Files
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
