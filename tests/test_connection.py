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
