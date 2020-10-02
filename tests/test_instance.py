import os

import pytest

from virt_up.instance import xdg_data_home
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
    ssh_identity = f'{xdg_data_home}/virt-up/sshkeys/{name}'
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

@pytest.mark.parametrize('template', ['generic-centos-8', 'generic-debian-10'])
def test_build(template):
    name = f'_test_virt_up_build_instance-{template}'
    assert(not Instance.exists(name))
    instance = Instance.build(name, template)
    assert(Instance.exists(name))
    assert(instance is not None)
    assert(instance.name == name)
    assert(instance.mac() is not None)
    assert(instance.domain.isActive())
    assert(instance.address() is not None)
    assert(instance.wait_for_port(22))
    instance.delete()
    assert(not Instance.exists(name))

def test_clone():
    source_name = '_test_virt_up_instance_2'
    target_name = '_test_virt_up_instance_3'

    source = Instance.build(source_name, 'generic-centos-8')
    assert(Instance.exists(source_name))
    address = source.address()
    assert(address is not None)

    target = source.clone(target_name)
    assert(target.name == target_name)
    assert(Instance.exists(target_name))
    address = target.address()
    assert(address is not None)

    ready = target.wait_for_port(22)
    assert(ready)

    source.delete()
    assert(not Instance.exists(source_name))
    target.delete()
    assert(not Instance.exists(target_name))

@pytest.mark.parametrize('name', ['generic-centos-8', 'generic-debian-10'])
def test_create(name):
    options = {}
    template = Instance.build(name, name, prefix='_TEST_TEMPLATE-', **options)
    assert(template)
    instance = template.clone(name, **options)
    assert(instance)
    address = instance.address()
    assert(address)
    output = instance.login(command='sudo -n id')
    assert('uid=0' in output)
    # cleanup
    template.delete()
    instance.delete()

def test_address_source_arp():
    template = 'generic-centos-8'
    name = f'_test_virt_up_instance_arp-{template}'

    settings = Settings(template)
    settings.address_source = 'arp'

    instance = Instance.build(name, template=template, settings=settings)
    assert(instance)
    assert(instance.meta['address_source'] == 'arp')
    assert(instance._arp_table())
    instance.meta.pop('address', None) # Flush cached address.
    address = instance.address()
    assert(address)
    # cleanup
    instance.delete()