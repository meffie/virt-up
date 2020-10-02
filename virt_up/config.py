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
virt-sysprep-args = --run-command "restorecon /etc/machine-info"

[generic-debian-10]
desc = Debian 10 (buster)
os-version = debian-10
os-type = linux
os-variant =  debian10
arch = x86_64
virt-builder-args = --install "sudo,qemu-guest-agent"
virt-sysprep-args = --run-command "/usr/sbin/dpkg-reconfigure -f noninteractive openssh-server"
"""
