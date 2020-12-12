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

import pytest

from virt_up.instance import Instance

@pytest.mark.parametrize('name', [
    'generic-centos-7',
    'generic-centos-8',
    'generic-debian-9',
    'generic-debian-10',
    'generic-fedora-32',
    'generic-opensuse-42',
    'generic-ubuntu-18',
])
def test_up(name):
    options = {}
    template = None
    instance = None
    try:
        template = Instance.build(name, name, prefix='_TEST_TEMPLATE-', **options)
        assert(template)
        instance = template.clone(name, **options)
        assert(instance)
        address = instance.address()
        assert(address)
        code, out, err = instance.run_command('id', sudo=True)
        assert(code == 0)
        assert('uid=0' in out)
        assert(err == '')
    finally:
        if instance:
            instance.delete()
        if template:
            template.delete()
