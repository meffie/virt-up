# Copyright (c) 2020-2021 Sine Nomine Associates
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
Create virtual machines quickly with virt-builder and virt-sysprep on a local
libvirt-based hypervisor.
"""

import configparser
import datetime
import fcntl
import getpass
import glob
import io
import json
import logging
import os
import pprint
import secrets
import shlex
import socket
import string
import time
import xml.etree.ElementTree

import sh
import libvirt

log = logging.getLogger(__name__)

# Environment variables
libvirt_uri = os.environ.get('LIBVIRT_DEFAULT_URI', 'qemu:///session')

virtup_config_home = os.path.expanduser(
    os.environ.get('VIRTUP_CONFIG_HOME',
    os.path.join(os.environ.get('XDG_CONFIG_HOME', '~/.config'), 'virt-up')))

virtup_data_home = os.path.expanduser(
    os.environ.get('VIRTUP_DATA_HOME',
    os.path.join(os.environ.get('XDG_DATA_HOME', '~/.local/share'), 'virt-up')))

# Helpers
def rm_f(path):
    if os.path.exists(path):
        os.remove(path)

def mkdir_p(path):
    if not os.path.exists(path):
        os.makedirs(path)

def logout(line):
    line = line.rstrip()
    if line:
        log.info(line)

def logerr(line):
    line = line.rstrip()
    if line:
        log.error(line)

def valid_name(name):
    """
    Returns true only if name contains a restricted set of characters.
    """
    safe = set(string.ascii_letters + string.digits + '-_.')
    for c in name:
        if c not in safe:
            return False
    return True

# The sh debug logging swamps the log file, so back off.
def _adjust_sh_log():
    logger = logging.getLogger(sh.__name__)
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.setLevel(logging.INFO)

# Commands
cp = sh.Command('cp').bake(_out=logout, _err=logerr)
ssh = sh.Command('ssh')
sftp = sh.Command('sftp')
ssh_keygen = sh.Command('ssh-keygen').bake(_out=logout, _err=logerr)
qemu_img = sh.Command('qemu-img').bake(_out=logout, _err=logerr)
virt_builder = sh.Command('virt-builder').bake(_out=logout, _err=logerr)
virt_install = sh.Command('virt-install').bake(_out=logout, _err=logerr)
virt_sysprep = sh.Command('virt-sysprep').bake(_out=logout, _err=logerr)
try:
    ansible = sh.Command('ansible-playbook').bake(_out=logout, _err=logerr)
except sh.CommandNotFound:
    ansible = None

# Avoid writing "domain not found" errors to the console.
def _libvirt_callback(userdata, err):
    pass

libvirt.registerErrorHandler(f=_libvirt_callback, ctx=None)

class Settings:
    """
    Configuration settings for a given template definition name.
    """
    def __init__(self, name):
        """
        Get template definition settings.
        """
        # Load common settings.
        settings = self._load('settings.cfg')
        common = settings.get('common', {})

        # Load template specific settings.
        templates = self._load('templates.d/*.cfg')
        if not name in templates:
            raise LookupError(f"Template '{name}' not found in settings.")

        template = templates[name]
        def get(option, default):
            return template.get(option, common.get(option, default))

        self.template_name = name
        self.desc = get('desc', '')
        self.os_version = get('os-version', '')
        self.os_variant = get('os-variant', '')
        self.arch = get('arch', '')
        self.pool = get('pool', 'default')
        self.user = get('user', get('username', getpass.getuser()))
        self.password_length = int(get('password-length', 24))
        self.image_format = get('image-format', 'qcow2')
        self.memory = get('memory', 512)
        self.vcpus = get('vcpus', 1)
        self.graphics = get('graphics', 'none')
        self.dns_domain = get('dns-domain', '')
        self.address_source = get('address-source', 'agent')
        self.virt_builder_args = shlex.split(get('virt-builder-args', ''))
        self.virt_sysprep_args = shlex.split(get('virt-sysprep-args', ''))
        self.virt_install_args = shlex.split(get('virt-install-args', ''))
        self.cp_args = shlex.split(get('cp-args', ''))
        self.template_playbook = get('template-playbook', '')
        self.instance_playbook = get('instance-playbook', '')
        log.debug("Settings: %s", pprint.pformat(vars(self)))

    @classmethod
    def _load(self, pattern):
        """
        Load settings from config files.
        """
        system_files = glob.glob(f'/etc/virt-up/{pattern}')
        user_files = glob.glob(f'{virtup_config_home}/{pattern}')
        parser = configparser.ConfigParser()
        filesread = parser.read(system_files + user_files)
        for f in filesread:
            log.debug(f"Read: {f}")

        # Convert to a regular dict and remove newlines.
        settings = {}
        for section in parser.sections():
            settings[section] = {}
            for option, value in parser[section].items():
                settings[section][option] = value.replace('\n', ' ').strip()

        return settings

    @classmethod
    def all(cls):
        """
        Generator to list each template definition.
        """
        for name in cls._load('templates.d/*.cfg'):
            yield Settings(name)

class LockFile:
    """
    Interprocess lock file.
    """
    def _write(self, text):
        self.fp.seek(0)
        self.fp.truncate()
        self.fp.write(text)
        self.fp.flush()
        self.fp.seek(0)

    def __enter__(self):
        if os.path.exists('/var/run/user/%d' % os.getuid()):
            path = '/var/run/user/%d/virt-up.lock' % os.getuid()
        else:
            path = '/tmp/virt-up.lock'
        log.debug("Waiting for lock")
        self.fp = open(path, 'a+')
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
        self._write(str(os.getpid())) # For troubleshooting.
        log.debug("Obtained lock")

    def __exit__(self, *exc):
        log.debug("Releasing lock")
        self._write('')
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
        self.fp.close()
        log.debug("Released lock")

class Connection:
    """
    A libvirt connection context manager.
    """
    opens = 0
    closes = 0
    def __enter__(self, uri=None):
        if uri is None:
            uri = libvirt_uri
        log.debug(f"Opening libvirt connection: uri='{uri}'")
        self.conn = libvirt.open(uri)
        Connection.opens += 1
        return self.conn

    def __exit__(self, *exc):
        log.debug("Closing libvirt connection")
        self.conn.close()
        Connection.closes += 1

class Creds:
    """
    Login information for a given user.
    """
    def __init__(self, username, password=None, ssh_identity=None):
        if password is None:
            password = self.generate_password()
        if not ssh_identity:
            ssh_identity = self.generate_ssh_keys(username)
        self.username = username
        self.password = password
        self.ssh_identity = ssh_identity

    @classmethod
    def generate_password(cls, length=24):
        """
        Generate a random password consisting of letters and digits.
        """
        alphanum = string.ascii_letters + string.digits
        chars = [secrets.choice(alphanum) for _ in range(length)]
        return ''.join(chars)

    def generate_ssh_keys(self, name):
        """
        Generate a ssh key pair for passwordless ssh login.
        """
        ssh_identity = f'{virtup_data_home}/sshkeys/{name}/id_rsa'
        if os.path.exists(ssh_identity):
            log.debug(f"SSH key file '{ssh_identity}' already exists.")
            if not os.path.exists(f'{ssh_identity}.pub'):
                raise FileNotFoundError(f"Missing ssh pub key '{ssh_identity}.pub'.")
        else:
            log.info(f"Generating ssh keys '{ssh_identity}'.")
            rm_f(f'{ssh_identity}.pub')
            mkdir_p(os.path.dirname(ssh_identity))
            ssh_keygen('-t', 'rsa', '-N', '', '-f', ssh_identity)
        return ssh_identity

class MacAddresses:
    filename = f'{virtup_data_home}/macaddrs.json'

    """
    Saved instance mac addresses.

    Domain mac addresses are assigned by libvirt the first time a
    domain is created. The same mac address is then reused on subsequent
    instantiations so the recreated guests have consisent IP addresses.
    """
    def __init__(self):
        self.addrs = {}
        self._read()

    def _read(self):
        try:
            with open(self.filename) as fp:
                self.addrs = json.load(fp)
        except FileNotFoundError:
            pass

    def _write(self):
        mkdir_p(os.path.dirname(self.filename))
        with open(self.filename, 'w') as fp:
            json.dump(self.addrs, fp, indent=4)

    def lookup(self, name):
        return self.addrs.get(name)

    def update(self, name, mac):
        old_mac = self.addrs.get(name)
        if old_mac is None or old_mac != mac:
            self.addrs[name] = mac
            self._write()

    def erase(self, name):
        if self.addrs.pop(name, None):
            self._write()

def query_storage_pool(name):
    """
    Lookup a storage pool path.
    """
    with Connection() as conn:
        pool = conn.storagePoolLookupByName(name)
        root = xml.etree.ElementTree.fromstring(pool.XMLDesc())
        path = root.find('target/path')
        if path is None:
            raise LookupError(f"Path is missing in storage pool '{name}'.")
        path = path.text
        if not path:
            raise LookupError(f"Path is empty in storage pool '{name}'.")
        return path

class Instance:
    """
    A libvirt domain with metadata.
    """
    def __init__(self, name, meta=None):
        self.name = name
        self.metafile = f'{virtup_data_home}/instance/{name}.json'
        self.meta = {}
        self._mac = None
        self._disks = None
        self._attach()
        if meta:
            self._update_meta(meta)

    def _attach(self):
        with Connection() as conn:
            self.domain = conn.lookupByName(self.name)
        self._read_meta()

    def _update_meta(self, meta):
        changed = []
        for key in meta:
            value = meta[key]
            if not key in self.meta or self.meta[key] != value:
                self.meta[key] = value
                changed.append(key)
        if changed:
            changed = ', '.join(changed)
            log.debug(f"Updating metadata fields: {changed}")
            self._write_meta()

    def _read_meta(self):
        try:
            with open(self.metafile, 'r') as fp:
                self.meta = json.load(fp)
        except FileNotFoundError:
            pass

    def _write_meta(self):
        log.debug(f"Writing metafile '{self.metafile}'.")
        mkdir_p(os.path.dirname(self.metafile))
        flags = os.O_CREAT | os.O_TRUNC | os.O_RDWR
        with os.fdopen(os.open(self.metafile, flags, 0o600), 'w') as fp:
            json.dump(self.meta, fp, indent=4)

    def is_clone(self):
        return 'cloned' in self.meta

    def is_template(self):
        return 'cloned' not in self.meta

    def mac(self):
        if self._mac is None:
            root = xml.etree.ElementTree.fromstring(self.domain.XMLDesc())
            for interface in root.findall('devices/interface'):
                self._mac = interface.find('mac').get('address')
        return self._mac

    def disks(self):
        if self._disks is None:
            self._disks = []
            root = xml.etree.ElementTree.fromstring(self.domain.XMLDesc())
            for disk in root.findall('devices/disk'):
                if disk.get('type') == 'file' and disk.get('device') == 'disk':
                    device = disk.find('target').get('dev')
                    source = disk.find('source').get('file')
                    self._disks.append(dict(device=device, source=source))
        return self._disks

    def start(self):
        """
        Start the instance.
        """
        if not self.domain.isActive():
            log.info(f"Starting instance '{self.name}'.")
            for retries in range(120, -1, -1):
                try:
                    self.domain.create()
                except libvirt.libvirtError as e:
                    if e.get_error_code() == libvirt.VIR_ERR_OPERATION_INVALID:
                        pass  # domain is running
                    else:
                        raise e
                if self.domain.isActive():
                    return
                if retries > 0:
                    log.debug(f"Waiting for running state; {retries} left.")
                    time.sleep(2)
            if not self.domain.isActive():
                raise TimeoutError(f"Failed to start instance '{self.name}'.")

    def stop(self):
        """
        Shutdown the instance.
        """
        if self.domain.isActive():
            log.info(f"Stopping instance '{self.name}'.")
            for retries in range(120, -1, -1):
                try:
                    self.domain.shutdown()
                except libvirt.libvirtError as e:
                    if e.get_error_code() == libvirt.VIR_ERR_OPERATION_INVALID:
                        pass  # domain is not running
                    else:
                        raise e
                if not self.domain.isActive():
                    return
                if retries > 0:
                    log.debug(f"Waiting for shutdown state; {retries} left.")
                    time.sleep(2)
            if self.domain.isActive():
                raise TimeoutError(f"Failed to stop instance '{self.name}'.")

    def delete(self):
        """
        Delete the instance, disk images, and instance meta data.
        """
        in_use = []
        for instance in Instance.all():
            from_ = instance.meta.get('from', '')
            format_ = instance.meta.get('image_format', '')
            if from_ == self.name and format_ == 'qcow2':
                in_use.append(instance.name)
        if in_use:
            in_use = ', '.join(["'%s'" %x for x in in_use])
            log.error(f"Unable to delete '{self.name}'; in use by {in_use}.")
            return 1

        log.info(f"Destroying instance '{self.name}'.")
        rm_f(self.metafile)
        self.meta = None
        if self.domain.isActive():
            self.domain.destroy()  # Pull the plug.
        with Connection() as conn:
            for disk in self.disks():
                source = disk['source']
                volume = conn.storageVolLookupByPath(source)
                if volume:
                    log.info(f"Deleting volume '{source}'.")
                    volume.delete()
        log.info(f"Undefining domain '{self.name}'.")
        self.domain.undefine()
        self.domain = None
        self.name = None
        self._disks = None
        self._mac = None
        self._address = None
        Instance.update_inventory()

    def _ia_to_addresses(self, ia):
        """
        Find the non-loopback IPv4 address in the dictionary returned by
        domain.interfaceAddresses().
        """
        in_type = 0 # IPv4 address type
        addresses = []
        for i in ia:
            addrs = ia[i].get('addrs')
            if not addrs:
                continue
            for addr in addrs:
                aip = addr.get('addr')
                atype = addr.get('type')
                if aip is None or atype is None:
                    continue
                if atype == in_type and not aip.startswith('127.'):
                    addresses.append(aip)
        return addresses

    def _ia_to_string(self, ia):
        """
        Format the dictionary returned by domain.interfaceAddresses() into
        a string suitable for display.
        """
        lines = []
        for i in ia:
            mac = ia[i].get('hwaddr')
            addrs = ia[i].get('addrs')
            if mac is None:
                mac = '-'
            if not addrs:
                lines.append(f'    {i:8}  {mac:17}  -')
            else:
                for addr in addrs:
                    aip = addr.get('addr')
                    if aip:
                        lines.append(f'    {i:8}  {mac:17}  {aip}')
        return '\n'.join(lines)

    def _address_from_ia(self, source='agent'):
        """
        Attempt to get the instance address from the domain interface-addresses.
        """
        sources = {
            'agent': libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT,
            'lease': libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE,
        }
        try:
            source = sources[source]
        except KeyError:
            raise ValueError(f"Unsupported interface-address source '{source}.")

        log.info(f"Waiting for instance '{self.name}' address.")
        last_ia_str = None
        addresses = []
        for retries in range(120, -1, -1):
            try:
                ia = self.domain.interfaceAddresses(source)
                addresses = self._ia_to_addresses(ia)
                ia_str = self._ia_to_string(ia)
                if ia_str != last_ia_str:
                    log.debug(f'Interface addresses:\n{ia_str}')
                    last_ia_str = ia_str
            except libvirt.libvirtError as e:
                if e.get_error_code() != libvirt.VIR_ERR_AGENT_UNRESPONSIVE:
                    raise e
            if addresses:
                break
            if retries > 0:
                suffix = 'ies' if retries > 1 else 'y'
                log.debug(f"Waiting for instance '{self.name}' address; {retries} retr{suffix} left.")
                time.sleep(2)

        if not addresses:
            raise LookupError(f"Unable to find address for instance '{self.name}'.")
        return addresses[0] # return the first one found.

    def _arp_table(self):
        """
        Retrieve the arp table.
        """
        arp = {}
        with open('/proc/net/arp') as fp:
            for line in fp:
                if line.startswith('IP address'):
                    continue
                address, _, _, mac, _, _ = line.split()
                if not mac in arp:
                    arp[mac] = []
                arp[mac].append(address)
        return arp

    def _ping(self, address):
        """
        Verify the address is pingable.
        """
        ping = sh.Command('ping')
        try:
            ping('-c', 2, address)
            return True
        except sh.ErrorReturnCode as e:
            log.debug(f"Unable to ping address '{address}'; ping code {e.exit_code}.")
            return False

    def _address_from_arp(self):
        """
        Attempt to retreive the instance address from the arp cache.
        """
        mac = self.mac()
        for retries in range(120, -1, -1):
            arp = self._arp_table()
            addresses = arp.get(mac, [])
            for address in addresses:
                if self._ping(address):
                    return address
            if retries > 0:
                suffix = 'ies' if retries > 1 else 'y'
                log.debug(f"Waiting for instance '{self.name}' address in arp cache; {retries} retr{suffix} left.")
                time.sleep(2)
        return None

    def _address_from_dns(self):
        """
        Attempt to retreive the instance address from dns. Assumes the dns is automatically updated by
        the dhcp server with the hostname configured on the guests.
        """
        address = None
        hostname = self.meta.get('hostname')
        if not hostname:
            raise LookupError(f"hostname is missing in instance '{self.name}' meta file.")
        for retries in range(120, -1, -1):
            try:
                ai = socket.getaddrinfo(hostname, 22, family=socket.AF_INET, proto=socket.IPPROTO_TCP)
                if ai:
                    address = ai[0][4][0]
                if address and self._ping(address):
                    break
            except:
                pass
            if retries > 0:
                suffix = 'ies' if retries > 1 else 'y'
                log.debug(f"Waiting for instance '{self.name}' address from dns lookup; {retries} retr{suffix} left.")
                time.sleep(2)
        return address

    def address(self):
        """
        Get the public IPv4 address for login.
        """
        address = self.meta.get('address')
        if address:
            return address

        if not self.domain.isActive():
            self.start()

        address_source = self.meta.get('address-source', 'agent')
        if address_source == 'agent':
            address = self._address_from_ia(source='agent')
        elif address_source == 'lease':
            address = self._address_from_ia(source='lease')
        elif address_source == 'arp':
            address = self._address_from_arp()
        elif address_source == 'dns':
            address = self._address_from_dns()
        else:
            raise ValueError(f"Invalid address_source '{address_source}' in instance '{self.name}'.")

        self._update_meta({'address': address})
        log.info(f"Instance '{self.name}' has address '{address}'.")
        return address

    def wait_for_port(self, port):
        """
        Wait for open port.
        """
        address = self.address()
        for retries in range(120, -1, -1):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.settimeout(2)
                s.connect((address, int(port)))
                return True
            except:
                pass
            finally:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
                except:
                    pass
            if retries > 0:
                suffix = 'ies' if retries > 1 else 'y'
                log.debug(f"Waiting for open port '{port}' on address '{address}'; {retries} retr{suffix} left.")
                time.sleep(2)

        raise LookupError(f"Unable to connect to '{address}:{port}'.")

    @classmethod
    def all(cls):
        pattern = f'{virtup_data_home}/instance/*.json'
        for path in glob.glob(pattern):
            name = os.path.basename(path).replace('.json', '')
            yield Instance(name)

    @classmethod
    def _domain_exists(cls, name):
        """
        Returns true if the domain already exists.
        """
        assert(name)
        domain = None
        with Connection() as conn:
            try:
                domain = conn.lookupByName(name)
            except libvirt.libvirtError as e:
                if e.get_error_code() != libvirt.VIR_ERR_NO_DOMAIN:
                    raise e
        return (not domain is None)

    @classmethod
    def exists(cls, name):
        """
        Returns true if the instance already exists, that is
        the domain and metadata file both exist.
        """
        metafile = f'{virtup_data_home}/instance/{name}.json'
        return os.path.exists(metafile) and cls._domain_exists(name)

    @classmethod
    def build(cls,
              template,
              target=None,
              prefix='VIRTUP-',
              settings=None,
              root_password=None,
              user=None,
              password=None,
              memory=None,
              size=None,
              vcpus=None,
              graphics=None,
              dns_domain=None,
              **kwargs):
        """
        Build a base instance with virt-builder and virt-install.
        Returns the base instance if it already exists.
        """
        _adjust_sh_log()

        if target:
            name = target
        else:
            # template -> base instance name
            safe = set(string.ascii_letters + string.digits + '_-.')
            suffix = ''.join([c if c in safe else '-' for c in template])
            name = f"{prefix}{suffix}"

        if not valid_name(name):
            raise ValueError(f"Base instance name '{name}' is not valid.")

        if cls.exists(name):
            log.info(f"Instance '{name}' already exists.")
            return Instance(name)

        if settings is None:
            settings = Settings(template)

        maddrs = MacAddresses()
        path = query_storage_pool(settings.pool)
        if not os.access(path, os.R_OK | os.W_OK):
            raise PermissionError(f"Read and write access is required for path '{path}'.")

        image = f'{path}/{name}.{settings.image_format}'

        # Sanity checks.
        if not settings.os_version:
            raise LookupError(f"virt-builder <os_version> is not defined for '{template}'.")
        if not settings.os_variant:
            raise LookupError(f"virt-install <os_variant> is not defined for '{template}'.")
        if cls._domain_exists(name):
            raise FileExistsError(f"Domain '{name}' without metadata already exists.")
        if os.path.exists(image):
            raise FileExistsError(f"Image file '{image}' already exists.")

        # Generate the ssh keys. Generate the passwords if not provided.
        if not user:
            user = settings.user
        if not root_password:
            root_password = Creds.generate_password(settings.password_length)
        if not password:
            password = Creds.generate_password(settings.password_length)
        root_creds = Creds('root', password=root_password)
        user_creds = Creds(user, password=password)

        # Setup virt-builder arguments.
        if memory is None:
            memory = settings.memory
        if vcpus is None:
            vcpus = settings.vcpus
        if graphics is None:
            graphics = settings.graphics
        if dns_domain is None:
            dns_domain = settings.dns_domain
        if dns_domain:
            hostname = f'{name}.{dns_domain}'
        else:
            hostname = name
        extra_args = settings.virt_builder_args
        if size:
            extra_args.extend(['--size', size])

        with LockFile():
            log.info(f"Building image file '{image}'.")
            virt_builder(
                settings.os_version,
                '--output', image,
                '--format', settings.image_format,
                '--hostname', hostname,
                '--run-command', 'ssh-keygen -A',
                '--root-password', f'password:{root_creds.password}',
                '--ssh-inject', f'{root_creds.username}:file:{root_creds.ssh_identity}.pub',
                '--copy-in', f"{root_creds.ssh_identity}:/root/.ssh",
                '--run-command', f"useradd -m -s /bin/bash {user_creds.username}",
                '--password', f"{user_creds.username}:password:{user_creds.password}",
                '--ssh-inject', f'{user_creds.username}:file:{user_creds.ssh_identity}.pub',
                '--copy-in', f"{user_creds.ssh_identity}:/home/{user_creds.username}/.ssh",
                '--run-command', 'mkdir -p /etc/sudoers.d',
                '--write',  f'/etc/sudoers.d/99-virt-up:{user_creds.username} ALL=(ALL) NOPASSWD: ALL',
                *extra_args)

        # Setup virt-install options. Reuse the last mac address for this
        # instance so it will (hopefully) be assigned the same address.
        optional_args = []
        mac = maddrs.lookup(name)
        if mac:
            optional_args.extend(['--mac', mac])
        extra_args = settings.virt_install_args
        with LockFile():
            log.info(f"Importing instance '{name}'.")
            virt_install(
                '--import',
                '--name', name,
                '--disk', image,
                '--memory', memory,
                '--vcpus', vcpus,
                '--graphics', graphics,
                '--os-variant', settings.os_variant,
                '--noautoconsole',
                *optional_args,
                *extra_args)

        # Attach the new domain instance and update the meta data. Save the
        # assigned mac address for next time.
        meta = {
            'template': template,
            'created': str(datetime.datetime.now()),
            'os_version': settings.os_version,
            'os_variant': settings.os_variant,
            'hostname': hostname,
            'disk': image,
            'image_format': settings.image_format,
            'memory': memory,
            'vcpus': vcpus,
            'graphics': graphics,
            'root': vars(root_creds),
            'user': vars(user_creds),
            'address-source': settings.address_source,
            'ssh_options': {
                'CheckHostIP': 'no',
                'ControlMaster': 'auto',
                'ControlPersist': '60s',
                'ForwardX11': 'no',
                'IdentitiesOnly': 'yes',
                'LogLevel': 'ERROR',
                'PasswordAuthentication': 'no',
                'StrictHostKeyChecking': 'no',
                'UserKnownHostsFile': '/dev/null',
            },
        }
        if size:
            meta['size'] = size
        instance = Instance(name, meta=meta)
        maddrs.update(name, instance.mac())
        instance.address() # Wait for address to be assigned.
        Instance.update_inventory()
        if settings.template_playbook:
            instance.run_playbook(settings.template_playbook)

        return instance

    def clone(self,
            target,
            settings=None,
            user=None,
            password=None,
            root_password=None,
            hostname=None,
            memory=None,
            size=None,
            vcpus=None,
            graphics=None,
            dns_domain=None,
            inventory=False,
            **kwargs):
        """
        Clone this instance to a new target instance.

        This instance will be stopped if it is running. The image will
        be cloned and virt-sysprep'd for the new target instance.
        """
        _adjust_sh_log()
        assert(target)
        if not valid_name(target):
            raise ValueError(f"target '{target}' contains invalid characters.")

        if self.exists(target):
            log.info(f"Target instance '{target}' already exists.")
            return Instance(target)

        if Instance._domain_exists(target):
            raise FileExistsError(f"Domain '{target}' without metadata already exists.")

        # Required meta data elements needed to clone.
        for element in ('os_version', 'os_variant', 'disk'):
            if not element in self.meta:
                raise LookupError(f"Element '{element}' is missing in '{self.name}' meta data.")

        if settings is None:
            settings = Settings(self.meta['template'])
        maddrs = MacAddresses()
        path = query_storage_pool(settings.pool)
        if not os.access(path, os.R_OK | os.W_OK):
            raise PermissionError(f"Read and write access is required for path '{path}'.")

        # Get default values from the current template settings.
        if not memory:
            memory = settings.memory
        if not vcpus:
            vcpus = settings.vcpus
        if not graphics:
            graphics = settings.graphics
        if dns_domain is None:
            dns_domain = settings.dns_domain
        if not hostname:
            if dns_domain:
                hostname = f'{target}.{dns_domain}'
            else:
                hostname = target

        # Clone the image.
        source_image = self.meta['disk']
        target_image = f'{path}/{target}.{settings.image_format}'
        if os.path.exists(target_image):
            raise FileExistsError(f"Image file '{target_image}' already exists.")
        self.stop()  # Ensure we are stopped before cloning.

        with LockFile():
            log.info(f"Cloning '{source_image}' to '{target_image}'.")
            if settings.image_format == 'qcow2':
                qemu_img.create('-f', 'qcow2', '-F', 'qcow2', '-b', source_image, target_image)
            else:
                extra_args = settings.cp_args
                cp(*extra_args, source_image, target_image)

        # Setup credentials for new instance.
        if not root_password:
            root_password = Creds.generate_password(settings.password_length)
        root_creds = Creds('root', password=root_password)
        if not user:
            user = settings.user
        if not password:
            password = Creds.generate_password(settings.password_length)
        user_creds = Creds(user, password=password)

        # Args to setup user creds in cloned instance.
        user_args = []
        if user_creds.username != self.meta['user']['username']:
            user_args.extend(['--run-command', f"useradd -m -s /bin/bash {user_creds.username}"])
        user_args.extend([
            '--password', f"{user_creds.username}:password:{user_creds.password}",
            '--ssh-inject', f'{user_creds.username}:file:{user_creds.ssh_identity}.pub',
            '--copy-in', f"{user_creds.ssh_identity}:/home/{user_creds.username}/.ssh"
        ])

        # Setup virt-sysprep args.
        extra_args = settings.virt_sysprep_args

        with LockFile():
            log.info(f"Preparing target image '{target_image}'.")
            virt_sysprep(
                '--quiet',
                '--add', target_image,
                '--operations', 'defaults,-ssh-userdir',
                '--hostname', hostname,
                '--root-password', f"password:{root_creds.password}",
                *user_args,
                *extra_args)

        # Setup virt-install options. Reuse the last mac address for this
        # instance so it will (hopefully) be assigned the same address.
        optional_args = []
        mac = maddrs.lookup(target)
        if mac:
            optional_args.extend(['--mac', mac])

        extra_args = settings.virt_install_args

        with LockFile():
            log.info(f"Importing instance '{target}'.")
            virt_install(
                '--import',
                '--name', target,
                '--disk', target_image,
                '--memory', memory,
                '--vcpus', vcpus,
                '--graphics', graphics,
                '--os-variant', self.meta['os_variant'],
                '--noautoconsole',
                '--autostart',
                *optional_args,
                *extra_args)

        # Attach the new domain instance and update the meta data. Save the
        # assigned mac address for next time.
        meta = self.meta.copy()
        meta.pop('address', None)  # Remove the parent's address.
        meta['cloned'] = str(datetime.datetime.now())
        meta['from'] = self.name
        meta['hostname'] = hostname
        meta['disk'] = target_image
        meta['format'] = settings.image_format
        meta['memory'] = memory
        meta['vcpus'] = vcpus
        meta['graphics'] = graphics
        meta['root'] = vars(root_creds)
        meta['user'] = vars(user_creds)
        instance = Instance(target, meta=meta)
        maddrs.update(target, instance.mac())
        instance.address() # Wait for an address to be assigned.
        if inventory:
            Instance.update_inventory()
            if settings.instance_playbook:
                instance.run_playbook(settings.instance_playbook)

        return instance

    @classmethod
    def update_inventory(cls):
        """
        Create an ansible inventory file for the cloned instances.
        """
        filename = f'{virtup_data_home}/inventory.yaml'
        clones = {}
        templates = {}
        for instance in Instance.all():
            name = instance.name
            address = instance.meta.get('address', None)
            if not address:
                log.warning(f"Skipping inventory entry for instance '{name}'; address is not available.")
                continue
            host = {
                'ansible_user': instance.meta['user']['username'],
                'ansible_host': address,
                'ansible_port': '22',
                'ansible_private_key_file': instance.meta['user']['ssh_identity'],
                'ansible_connection': 'ssh',
                'ansible_ssh_common_args': ' '.join(instance._ssh_option_args()),
            }
            if instance.is_clone():
                clones[name] = host
            else:
                templates[name] = host
        with open(filename, 'w') as fp:
            fp.writelines([
                '---\n',
                'all:\n',
                '  children:\n',
                '    virt_up_managed:\n',
                '      hosts:\n'])
            for name in clones.keys():
                fp.write(f'        {name}:\n')
                for key, value in clones[name].items():
                    fp.write(f'          {key}: "{value}"\n')
            fp.writelines([
                '    virt_up_templates:\n',
                '      hosts:\n'])
            for name in templates.keys():
                fp.write(f'        {name}:\n')
                for key, value in templates[name].items():
                    fp.write(f'          {key}: "{value}"\n')

    def _ssh_option_args(self):
        """
        Get the list of ssh option arguments.
        """
        args = []
        options = self.meta.get('ssh_options', {})
        for k, v in options.items():
            args.append('-o')
            args.append(f'{k}={v}')
        return args

    def login(self, mode='ssh', command=None):
        """
        ssh or stfp login to the instance.
        """
        modes = {'ssh': ssh.__name__, 'sftp': sftp.__name__}
        if mode not in modes:
            raise ValueError(f"Unsupported mode '{mode}'.")
        self.start()
        self.meta.pop('address', None) # Flush our cached address.
        address = self.address()
        user = self.meta['user']['username']
        ssh_identity = self.meta['user']['ssh_identity']
        args = [
            '-i', ssh_identity,
            *self._ssh_option_args(),
            f'{user}@{address}',
        ]
        if command:
            args.append(command)

        self.wait_for_port(22)      # Wait until ssh port is ready.
        args.insert(0, modes[mode]) # Required for execv.
        os.execv(modes[mode], args) # Drop into interactive shell, never to return.
        raise AssertionError('exec failed')

    def run_command(self, *args, sudo=False):
        """
        Run a command via ssh and return the exit code, stdout,
        and stderr as a tuple.
        """
        self.wait_for_port(22)
        address = self.address()
        user = self.meta['user']['username']
        ssh_identity = self.meta['user']['ssh_identity']
        if sudo:
            args = ['sudo', '-n'] + list(args)
        command = shlex.join(args)
        ssh_args = [
            '-i', ssh_identity,
            *self._ssh_option_args(),
            f'{user}@{address}',
            command,
        ]
        code = 0
        out = io.StringIO()
        err = io.StringIO()
        try:
            ssh(ssh_args, _out=out, _err=err)
        except sh.ErrorReturnCode as e:
            code = e.exit_code
        return code, out.getvalue(), err.getvalue()

    def run_playbook(self, playbook):
        """
        Run an ansible playbook on this instance.
        """
        inventory = f'{virtup_data_home}/inventory.yaml'
        if not ansible:
            log.error("Skipping playbook; 'ansible-playbook' command not found.")
            return
        # Search for the playbook.
        searched = []
        found = None
        for p in (playbook,
                  os.path.join(virtup_config_home, 'playbooks', playbook),
                  os.path.join('/etc/virt-up/playbooks', playbook)):
            searched.append(p)
            if os.path.exists(p):
                found = p
                break
        if not found:
            searched = ' '.join(searched)
            log.error(f"Skipping playbook; '{playbook}' file not found. Searched: {searched}.")
            return
        playbook = found
        self.wait_for_port(22)
        address = self.address()
        if not address:
            log.warning(f"Skipping playbook; address for '{self.name}' is not available.")
            return
        log.info(f"Running playbook '{playbook}' on '{self.name}'.")
        ansible('-i', inventory, '--limit', self.name, playbook)
