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
