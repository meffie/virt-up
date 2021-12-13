OS Info database
----------------

Operating system specific information is provided by the OS Info Database
(``osinfo-db``) library. The OS Info Database provided by your package
manager may be out of date and not provide definitions for recent operating
system versions.

If you have already updated your system, and the osinfo-db is still to old,
then you can use the ``osinfo-db-import`` tool with the ``--local`` option to
install an up-to-date database in your home directory which will not conflict
with your package manager installation. The ``osinfo-db-import`` tool is
provided by the package name ``osinfo-db-tools`` on ``yum`` and ``apt``
managed systems.

Example::

    $ wget https://releases.pagure.org/libosinfo/osinfo-db-<VERSION>.tar.xz
    $ sudo osinfo-db-import --local osinfo-db-<VERSION>.tar.xz


See https://libosinfo.org/download for more information.
