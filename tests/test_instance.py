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

import os

import pytest

from virt_up.instance import virtup_data_home
from virt_up.instance import query_storage_pool
from virt_up.instance import MacAddresses
from virt_up.instance import Creds
from virt_up.instance import Settings
from virt_up.instance import Instance

def remove(path):
    if os.path.exists(path):
        os.remove(path)

def test_mac_registry():
    name = '__test_virt_up_mac_addrs_1'
    mac = '01:23:45:67:89:ab'
    ma1 = MacAddresses()
    ma1.update(name, mac)

    ma2 = MacAddresses()
    assert(ma2.lookup(name) == mac)
    ma2.erase(name)

    ma3 = MacAddresses()
    assert(ma3.lookup('name') is None)

def test_generate_ssh_keys():
    name = '_test_virt_up'
    ssh_identity = f'{virtup_data_home}/sshkeys/{name}'
    remove(ssh_identity)
    remove(f'{ssh_identity}.pub')
    creds = Creds(name)
    assert(os.path.exists(creds.ssh_identity))
    assert(os.path.exists(f'{creds.ssh_identity}.pub'))
    remove(creds.ssh_identity)
    remove(f'{creds.ssh_identity}.pub')

def test_exists_not_found():
    name = '_test_virt_up_this_does_not_exist'
    assert(not Instance.exists(name))

def test_query_storage_pool_path():
    name = 'default'
    path = query_storage_pool(name)
    assert(path is not None)
    assert(os.path.exists(path)) # Since running locally.

@pytest.mark.parametrize('template', ['generic/centos8', 'generic/debian10'])
def test_build(config_files, template):
    instance = Instance.build(template, prefix='__TEST_BUILD__')
    assert(instance is not None)
    name = instance.name
    assert(instance.mac() is not None)
    assert(instance.domain.isActive())
    assert(instance.address() is not None)
    assert(instance.wait_for_port(22))
    assert(Instance.exists(name))
    instance.delete()
    assert(not Instance.exists(name))

def test_clone(config_files):
    target_name = '_test_virt_up_instance_3'

    source = Instance.build('generic/centos8', prefix='__TEST_CLONE__')
    assert(Instance.exists(source.name))
    source_name = source.name
    address = source.address()
    assert(address is not None)

    target = source.clone(target_name)
    assert(target.name == target_name)
    assert(Instance.exists(target_name))
    address = target.address()
    assert(address is not None)

    ready = target.wait_for_port(22)
    assert(ready)

    target.delete() # Must delete cloned image first.
    assert(not Instance.exists(target_name))

    source.delete()
    assert(not Instance.exists(source_name))

def test_address_source_arp(config_files):
    template = 'generic/centos8'
    settings = Settings(template)
    settings.address_source = 'arp'

    instance = Instance.build(template, prefix='__TEST__SOURCE_ARP__', settings=settings)
    assert(instance is not None)
    try:
        assert(instance.meta['address-source'] == 'arp')
        assert(instance._arp_table())
        instance.meta.pop('address', None) # Flush cached address.
        address = instance.address()
        assert(address)
    finally:
        # cleanup
        instance.delete()
