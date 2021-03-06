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

from virt_up.instance import Connection

def test_ping():
    count = Connection.opens
    assert(Connection.opens == Connection.closes)
    with Connection() as c:
        assert(Connection.opens == (count + 1))
        assert(Connection.closes == count)
        version = c.getVersion()
        assert(version)
    assert(Connection.opens == (count + 1))
    assert(Connection.opens == Connection.closes)

def test_close_on_exception():
    count = Connection.opens
    assert(Connection.opens == Connection.closes)
    try:
        with Connection():
            assert(Connection.opens == (count + 1))
            assert(Connection.closes == count)
            raise ValueError()
    except ValueError:
        pass
    assert(Connection.opens == (count + 1))
    assert(Connection.opens == Connection.closes)
