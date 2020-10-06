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

#
# Default values for site-specific settings.
#
SETTINGS = """
[site]
pool = default
username = virt
dns-domain =
address-source = agent
image-format = qcow2
virt-builder-args =
virt-sysprep-args =
virt-install-args =
"""

#
# Default template definitions.
#
TEMPLATES = """
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
virt-sysprep-args = --run-command "/usr/sbin/dpkg-reconfigure -f noninteractive openssh-server"

[generic-debian-9]
desc = Debian 9 (stretch)
os-version = debian-9
os-type = linux
os-variant =  debian9
arch = x86_64
virt-builder-args = --install "sudo,qemu-guest-agent"
virt-sysprep-args = --run-command "/usr/sbin/dpkg-reconfigure -f noninteractive openssh-server"

[generic-ubuntu-18]
desc = Ubuntu 18.04
os-version = ubuntu-18.04
os-type = linux
os-variant =  ubuntu18.04
arch = x86_64
virt-builder-args = --install "sudo,policykit-1,qemu-guest-agent"
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
