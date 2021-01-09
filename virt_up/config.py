# Copyright (c) 2020 Sine Nomine Associates
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Built-in virt-up settings.
"""

import os

DATA = [
    # Default values for site-specific settings.
    {
        'filename': 'settings.cfg',
        'verbatim': False,
        'contents': """
[site]
pool = default
username = virt
dns-domain =
address-source = agent
image-format = qcow2
template-playbook =
instance-playbook =
virt-builder-args =
virt-sysprep-args =
virt-install-args =
"""
    },
    # Default template definitions.
    {
        'filename': 'templates.cfg',
        'verbatim': False,
        'contents': """
[generic-centos-8]
desc = CentOS 8.2
os-version = centos-8.2
os-type = linux
os-variant = centos8
arch = x86_64
virt-builder-args = --firstboot-command "systemctl enable serial-getty@ttyS0.service"
                    --firstboot-command "systemctl start serial-getty@ttyS0.service"
                    --install "sudo,python3"
                    --selinux-relabel
virt-sysprep-args = --selinux-relabel

[generic-centos-7]
desc = CentOS 7.8
os-version = centos-7.8
os-type = linux
os-variant = centos7.0
arch = x86_64
virt-builder-args = --firstboot-command "systemctl enable serial-getty@ttyS0.service"
                    --firstboot-command "systemctl start serial-getty@ttyS0.service"
                    --install "sudo,python3"
                    --selinux-relabel
virt-sysprep-args = --selinux-relabel

[generic-fedora-32]
desc = Fedora 32
os-version = fedora-32
os-type = linux
os-variant = fedora32
arch = x86_64
# --install 'qemu-guest-agent' hangs. fall back to arp for now.
address-source = arp
virt-builder-args = --firstboot-command "systemctl enable serial-getty@ttyS0.service"
                    --firstboot-command "systemctl start serial-getty@ttyS0.service"
                    --selinux-relabel
virt-sysprep-args = --selinux-relabel

[generic-debian-10]
desc = Debian 10 (buster)
os-version = debian-10
os-type = linux
os-variant =  debian10
arch = x86_64
virt-builder-args = --install "sudo,qemu-guest-agent"
                    --firstboot "{scripts}/fixup-network-interfaces.sh"
virt-sysprep-args = --run-command "/usr/sbin/dpkg-reconfigure -f noninteractive openssh-server"

[generic-debian-9]
desc = Debian 9 (stretch)
os-version = debian-9
os-type = linux
os-variant =  debian9
arch = x86_64
virt-builder-args = --install "sudo,qemu-guest-agent"
                    --firstboot "{scripts}/fixup-network-interfaces.sh"
virt-sysprep-args = --run-command "/usr/sbin/dpkg-reconfigure -f noninteractive openssh-server"

[generic-ubuntu-18]
desc = Ubuntu 18.04
os-version = ubuntu-18.04
os-type = linux
os-variant =  ubuntu18.04
arch = x86_64
virt-builder-args = --install "sudo,policykit-1,qemu-guest-agent"
                    --firstboot "{scripts}/fixup-netplan-netcfg.sh"
virt-sysprep-args = --run-command "/usr/sbin/dpkg-reconfigure -f noninteractive openssh-server"
virt-install-args = --channel unix,mode=bind,path=/var/lib/libvirt/qemu/guest01.agent,target_type=virtio,name=org.qemu.guest_agent.0

[generic-opensuse-42]
desc = openSUSE Leap 42.1
os-version = opensuse-42.1
os-type = linux
os-variant = opensuse42.1
arch = x86_64
virt-builder-args = --install "sudo,qemu-guest-agent"
virt-sysprep-args =
virt-install-args = --channel unix,mode=bind,path=/var/lib/libvirt/qemu/guest01.agent,target_type=virtio,name=org.qemu.guest_agent.0
"""
    },

    # virt-builder --run/--firstboot scripts
    {
        'filename': 'scripts/fixup-network-interfaces.sh',
        'verbatim': True,
        'contents': r"""#!/bin/sh
old_iface=`awk '/^iface en/ {print $2}' /etc/network/interfaces | tail -1`
new_iface=`ip -o -a link | cut -f2 -d: | tr -d ': ' | grep '^en' | tail -1`

echo "old_iface:$old_iface"
echo "new_iface:$new_iface"

if test "x$new_iface" = "x"; then
    echo "Enable to detect primary interface." >&2
elif test "x$old_iface" != "x$new_iface"; then
    echo "Changing $old_iface to $new_iface in /etc/network/interfaces"
    sed -i -e "s/$old_iface/$new_iface/" /etc/network/interfaces
    echo "Bringing up interface $new_iface"
    ifup "$new_iface"
fi
"""
    },
    {
        'filename': 'scripts/fixup-netplan-netcfg.sh',
        'verbatim': True,
        'contents': r"""#!/bin/sh
new_iface=`ip -o -a link | cut -f2 -d: | tr -d ': ' | grep '^en' | tail -1`
echo "new_iface:$new_iface"
if test "x$new_iface" = "x"; then
    echo "Enable to detect primary interface." >&2
    exit 1
fi
echo "Setting interface name to $new_iface in /etc/netplan/01-netcfg.yaml"
sed -i -e "s/^    en.*:/    $new_iface:/" /etc/netplan/01-netcfg.yaml
echo "Bringing up interface $new_iface"
netplan apply
"""
    },

    # Playbooks
    {
        'filename': 'playbooks/devel-debian.yaml',
        'verbatim': True,
        'contents': """\
---
- name: Development
  hosts: all
  tasks:
    - name: Update kernel
      become: yes
      apt:
        state: latest
        name: 'linux-image*'
        only_upgrade: yes
        update_cache: yes
      register: update_kernel_results

    - name: Reboot
      become: yes
      reboot:
        reboot_timeout: 600
      when: update_kernel_results.changed

    - name: Re-gather facts
      setup:

    - name: Install kernel headers
      become: yes
      apt:
        state: present
        name:
          - linux-headers-{{ ansible_kernel }}

    - name: Install development packages
      become: yes
      apt:
        state: present
        name:
          - autoconf
          - automake
          - bison
          - flex
          - gcc
          - git
          - libfuse-dev
          - libgc-dev
          - libkrb5-dev
          - libncurses5-dev
          - libperl-dev
          - libtool
          - make
          - swig
          - wget
        """
    },
    {
        'filename': 'playbooks/devel-redhat.yaml',
        'verbatim': True,
        'contents': """\
---
- name: Development
  hosts: all
  tasks:
    - name: Update kernel
      become: yes
      yum:
        state: latest
        name:
          - kernel
      register: update_kernel_results

    - name: Reboot
      become: yes
      reboot:
        reboot_timeout: 600
      when: update_kernel_results.changed

    - name: Re-gather facts
      setup:

    - name: Install kernel headers
      become: yes
      yum:
        state: present
        name:
          - "kernel-devel-uname-r == {{ ansible_kernel }}"

    - name: Install development packages
      become: yes
      yum:
        state: present
        name:
          - autoconf
          - automake
          - bison
          - flex
          - fuse-devel
          - gcc
          - git
          - glibc-devel
          - krb5-devel
          - libtool
          - make
          - ncurses-devel
          - pam-devel
          - perl-devel
          - perl-ExtUtils-Embed
          - redhat-rpm-config
          - rpm-build
          - swig
          - wget
        """
    },
]

def create_files(path, force=False):
    """
    Create configuration files.
    """
    wrote = []
    context = {
        'scripts': os.path.join(path, 'scripts'),
        'playbooks': os.path.join(path, 'playbooks'),
    }
    for f in DATA:
        filename = os.path.join(path, f['filename'])
        if force or (not os.path.exists(filename)):
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            with open(filename, 'w') as fp:
                text = f['contents']
                if not f['verbatim']:
                    text = text.format(**context)
                fp.write(text)
                wrote.append(filename)
    return wrote
