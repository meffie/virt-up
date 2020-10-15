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
Create virtual machines quickly with virt-builder and virt-sysprep on a local
libvirt-based hypervisor.
"""

import crypt
import configparser
import datetime
import json
import logging
import os
import secrets
import shlex
import socket
import string
import time
import xml.etree.ElementTree

import sh
import libvirt

from .config import SETTINGS, TEMPLATES

log = logging.getLogger(__name__)

# Environment variables
libvirt_uri = os.environ.get('LIBVIRT_DEFAULT_URI', 'qemu:///session')
xdg_config_home = os.path.expanduser(os.environ.get('XDG_CONFIG_HOME', '~/.config'))
xdg_data_home = os.path.expanduser(os.environ.get('XDG_DATA_HOME', '~/.local/share'))

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

# The sh debug logging swamps the log file, so back off.
def _adjust_sh_log():
    logger = logging.getLogger(sh.__name__)
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.setLevel(logging.INFO)

# Commands
cp = sh.Command('cp').bake(_out=logout, _err=logerr)
ssh = sh.Command('ssh')
ssh_keygen = sh.Command('ssh-keygen').bake(_out=logout, _err=logerr)
qemu_img = sh.Command('qemu-img').bake(_out=logout, _err=logerr)
virt_builder = sh.Command('virt-builder').bake(_out=logout, _err=logerr)
virt_install = sh.Command('virt-install').bake(_out=logout, _err=logerr)
virt_sysprep = sh.Command('virt-sysprep').bake(_out=logout, _err=logerr)

# Avoid writing "domain not found" errors to the console.
def _libvirt_callback(userdata, err):
    pass

libvirt.registerErrorHandler(f=_libvirt_callback, ctx=None)

class Settings:
    """
    Configuration settings read from the settings (ini) file
    for the local libvirt settings and OS specific settings.
    """
    def __init__(self, template=None):
        # Load local site settings.
        self.settings = self._load('settings', SETTINGS)
        self.site = self.settings.get('site', {})
        self.pool = self.site.get('pool', 'default')
        self.username = self.site.get('username', 'virt')
        self.image_format = self.site.get('image-format', 'qcow2')
        self.dns_domain = self.site.get('dns-domain', '')
        self.address_source = self.site.get('address-source', 'agent')

        # Load template definitions.
        self.templates = self._load('templates', TEMPLATES)
        if template is None:
            self.template = {}
            self.template_name = None
            self.ov_version = None
            self.os_variant = None
        else:
            if not template in self.templates:
                raise LookupError(f"Template '{template}' not found in settings.")
            self.template = self.templates[template]
            self.template_name = template
            self.os_version = self.template.get('os-version')
            self.os_variant = self.template.get('os-variant')
            self.address_source = self.template.get('address-source', self.address_source)

    def _load(self, name, defaults):
        system_file = f'/etc/virt-up/{name}.cfg'
        user_file = f'{xdg_config_home}/virt-up/{name}.cfg'
        parser = configparser.ConfigParser()
        parser.read_string(defaults)
        parser.read([system_file, user_file])

        # Convert to a regular dict and remove newlines.
        settings = {}
        for section in parser.sections():
            settings[section] = {}
            for option, value in parser[section].items():
                settings[section][option] = value.replace('\n', ' ').strip()

        return settings

    def extra_args(self, command, **variables):
        """
        Extra command line arguments for the local hypervisor and the target
        template definition.
        """
        args = []
        for section in ('site', 'template'):
            settings = getattr(self, section, {})
            args_str = settings.get(f'{command}-args', '')
            args_str = args_str.format(**variables)
            args.extend(shlex.split(args_str))
        return args

class Connection:
    """
    A libvirt connection context manager.
    """
    opens = 0
    closes = 0
    def __enter__(self, uri=None):
        if uri is None:
            uri = libvirt_uri
        self.conn = libvirt.open(uri)
        Connection.opens += 1
        return self.conn

    def __exit__(self, *exc):
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

    def generate_password(self, length=24):
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
        ssh_identity = f'{xdg_data_home}/virt-up/sshkeys/{name}'
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
    filename = f'{xdg_data_home}/virt-up/macaddrs.json'

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
        self.metafile = f'{xdg_data_home}/virt-up/instance/{name}.json'
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
                arp[mac] = address
        return arp

    def _address_from_arp(self):
        """
        Attempt to retreive the instance address from the arp cache.
        """
        address = None
        mac = self.mac()
        for retries in range(120, -1, -1):
            arp = self._arp_table()
            address = arp.get(mac)
            if address:
                break
            if retries > 0:
                suffix = 'ies' if retries > 1 else 'y'
                log.debug(f"Waiting for instance '{self.name}' address in arp cache; {retries} retr{suffix} left.")
                time.sleep(2)
        return address

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
                if address:
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
    def list(cls, clones_only=True):
        with Connection() as conn:
            for domain in conn.listAllDomains():
                name = domain.name()
                metafile = f'{xdg_data_home}/virt-up/instance/{name}.json'
                try:
                    with open(metafile, 'r') as fp:
                        meta = json.load(fp)
                    if clones_only:
                        if 'cloned' in meta:
                            yield name
                    else:
                        yield name
                except FileNotFoundError:
                    pass

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
        metafile = f'{xdg_data_home}/virt-up/instance/{name}.json'
        return os.path.exists(metafile) and cls._domain_exists(name)

    @classmethod
    def build(cls,
              name,
              template=None, # defaults to <name>
              prefix='',
              settings=None,
              root_password=None,
              user=None,
              password=None,
              memory=512,
              size=None,
              vcpus=1,
              graphics='none',
              dns_domain=None,
              **kwargs):
        """
        Build an instance with virt-builder and virt-install.
        """
        _adjust_sh_log()
        if name is None:
            raise ValueError('<name> is required.')
        if not template:
            template = name

        name = f'{prefix}{name}'  # Optional instance name prefix.

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
            user = settings.username
        root_creds = Creds('root', password=root_password)
        user_creds = Creds(user, password=password)

        # useradd requires a hashed password.
        salt = crypt.mksalt(crypt.METHOD_SHA512)
        password = crypt.crypt(user_creds.password, salt)

        # Setup virt-builder arguments.
        if dns_domain is None:
            dns_domain = settings.dns_domain
        if dns_domain:
            hostname = f'{name}.{dns_domain}'
        else:
            hostname = name
        extra_args = settings.extra_args('virt-builder')
        if size:
            extra_args.extend(['--size', size])

        log.info(f"Building image file '{image}'.")
        virt_builder(
            settings.os_version,
            '--output', image,
            '--format', settings.image_format,
            '--hostname', hostname,
            '--root-password', f'password:{root_creds.password}',
            '--run-command', 'ssh-keygen -A',
            '--run-command', f"useradd -m -s /bin/bash -p '{password}' {user}",
            '--ssh-inject', f'{user}:file:{user_creds.ssh_identity}.pub',
            '--run-command', 'mkdir -p /etc/sudoers.d',
            '--write',  f'/etc/sudoers.d/99-sna-devlab:{user} ALL=(ALL) NOPASSWD: ALL',
            *extra_args)

        # Setup virt-install options. Reuse the last mac address for this
        # instance so it will (hopefully) be assigned the same address.
        optional_args = []
        mac = maddrs.lookup(name)
        if mac:
            optional_args.extend(['--mac', mac])
        extra_args = settings.extra_args('virt-install')

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
            'memory': memory,
            'vcpus': vcpus,
            'graphics': graphics,
            'root': vars(root_creds),
            'user': vars(user_creds),
            'address-source': settings.address_source,
        }
        if size:
            meta['size'] = size
        instance = Instance(name, meta=meta)
        maddrs.update(name, instance.mac())
        instance.address() # Wait for address to be assigned.

        return instance

    def clone(self,
            target,
            settings=None,
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

        # Clone the image.
        source_image = self.meta['disk']
        target_image = f'{path}/{target}.{settings.image_format}'
        if os.path.exists(target_image):
            raise FileExistsError(f"Image file '{target_image}' already exists.")
        self.stop()  # Ensure we are stopped before cloning.
        log.info(f"Cloning '{source_image}' to '{target_image}'.")
        if settings.image_format == 'qcow2':
            qemu_img.create('-f', 'qcow2', '-F', 'qcow2', '-b', source_image, target_image)
        else:
            extra_args = settings.extra_args('cp')
            cp(*extra_args, source_image, target_image)

        # Setup virt-sysprep args.
        if not hostname:
            if dns_domain is None:
                dns_domain = settings.dns_domain
            if dns_domain:
                hostname = f'{target}.{dns_domain}'
            else:
                hostname = target

        extra_args = settings.extra_args('virt-sysprep')

        log.info(f"Preparing target image '{target_image}'.")
        virt_sysprep(
            '--quiet',
            '--add', target_image,
            '--operations', 'defaults,-ssh-userdir',
            '--hostname', hostname,
            *extra_args)

        # Setup virt-install options. Reuse the last mac address for this
        # instance so it will (hopefully) be assigned the same address.
        if not memory:
            memory = self.meta.get('memory', 512)
        if not vcpus:
            vcpus = self.meta.get('vcpus', 1)
        if not graphics:
            graphics = self.meta.get('graphics', 'none')

        optional_args = []
        mac = maddrs.lookup(target)
        if mac:
            optional_args.extend(['--mac', mac])

        extra_args = settings.extra_args('virt-install')

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
        meta['hostname'] = hostname
        meta['disk'] = target_image
        meta['memory'] = memory
        meta['vcpus'] = vcpus
        meta['graphics'] = graphics
        instance = Instance(target, meta=meta)
        maddrs.update(target, instance.mac())
        instance.address() # Wait for an address to be assigned.
        if inventory:
            Instance.update_inventory()
        return instance

    @classmethod
    def update_inventory(cls, filename=None):
        """
        Create an ansible inventory file for the cloned instances.
        """
        if filename is None:
            filename = f'{xdg_data_home}/virt-up/inventory.yaml'
        hosts = {}
        for name in Instance.list():
            instance = Instance(name)
            hosts[name] = {
                'ansible_user': instance.meta['user']['username'],
                'ansible_host': instance.meta['address'],
                'ansible_private_key_file': instance.meta['user']['ssh_identity'],
                'ansible_connection': 'ssh',
                'ansible_ssh_common_args': \
                    '-o UserKnownHostsFile=/dev/null -o ControlMaster=auto ' \
                    '-o ControlPersist=60s -o ForwardX11=no -o LogLevel=ERROR -o IdentitiesOnly=yes ' \
                    '-o StrictHostKeyChecking=no'
            }
        with open(filename, 'w') as fp:
            fp.writelines([
                '---\n',
                'all:\n',
                '  children:\n',
                '    virt_up_managed:\n',
                '      hosts:\n'])
            for name in hosts.keys():
                fp.write(f'        {name}:\n')
                for key, value in hosts[name].items():
                    fp.write(f'          {key}: "{value}"\n')

    def login(self, command=None):
        """
        ssh login to the instance.
        """
        self.start()
        self.meta.pop('address', None) # Flush our cached address.
        address = self.address()
        user = self.meta['user']['username']
        ssh_identity = self.meta['user']['ssh_identity']
        args = [
            '-i', ssh_identity,
            '-o', 'PasswordAuthentication=no',
            '-o', 'CheckHostIP=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'LogLevel=ERROR',
            f'{user}@{address}',
        ]

        self.wait_for_port(22)  # Wait until ssh port is ready.
        if not command:
            args.insert(0, ssh.__name__) # Required for execv.
            os.execv(ssh.__name__, args) # Drop into interactive shell, never to return.
            assert(False) # unreachable
        else:
            args.append(command)
            output = []
            try:
                for line in ssh(*args, _err=logerr, _iter=True):
                    logout(line)
                    output.append(line.rstrip())
            except sh.ErrorReturnCode as e:
                log.error(e)
            return ''.join(output)
