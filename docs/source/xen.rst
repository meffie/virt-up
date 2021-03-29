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
