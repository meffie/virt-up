
from virt_up.instance import Settings

def test_general_settings():
    settings = Settings()
    assert(settings.pool is not None)

def test_template_settings():
    name = 'generic-centos-8'
    settings = Settings(name)
    assert(settings.os_variant is not None)
    assert(settings.os_variant == 'centos8')
    assert(settings.template.get('virt-builder-args') is not None)
    assert(settings.template.get('virt-builder-args') != '')

def test_list_templates():
    settings = Settings()
    names = settings.templates.keys()
    assert(names is not None)
    assert(len(names) > 0)
    assert('generic-centos-8' in names)

def test_extra_args():
    name = 'generic-centos-8'
    settings = Settings(name)
    args = settings.extra_args('virt-builder')
    assert(args)
    assert('--selinux-relabel' in args)
