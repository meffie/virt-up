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

import os
import logging
import pathlib
import pprint
import string

import click
import virt_up

from cookiecutter.main import cookiecutter

# OS names supported in the embedded cookiecutter template.
_template_oses = [
    'centos7',
    'centos8',
    'fedora33',
    'debian9',
    'debian10',
    'ubuntu18',
    'opensuse42',
    'other',
]

@click.group()
@click.version_option(version=virt_up.__version__)
@click.option('-d', '--debug', is_flag=True)
@click.option('-q', '--quiet', is_flag=True)
def main(debug, quiet):
    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format='%(message)s')

@main.command()
@click.argument('names', metavar='<name>', nargs=-1)
@click.option('-t', '--template', help='Template name (default: default).', default='default')
@click.option('--user', help='Username (default: current user).')
@click.option('--password', help='Password (default: random).')
@click.option('--size', help='Disk size and units (example: 10G).')
@click.option('--memory', help='Memory in MB (example: 2028).')
@click.option('--vcpus', help='Number of virtual cpus.')
@click.option('--graphics', help='Graphics type (example: spice).')
@click.option('--dns-domain', help='DNS domain name (example: example.com).')
@click.option('--inventory/--no-inventory', help='Include/exclude from virt-up ansible inventory.', default=True)
def create(names, template, **args):
    """
    Create instances.

    Build a base instance then clone zero or more instances from the
    base instance. Use 'virt-up show templates' to list available templates.
    """
    base = virt_up.Instance.build(template, **args)
    for name in names:
        instance = base.clone(name, **args)
        instance.wait_for_port(22)
        click.echo(f"Instance '{instance.name}' is up.")

@main.command()
@click.argument('names', metavar='<name>', nargs=-1)
def destroy(names):
    """
    Destroy instances.

    Shutdown and delete the instances. Use virt-up list [--all]
    to list instance names.
    """
    for name in names:
        if not virt_up.Instance.exists(name):
            click.echo(f"Instance '{name}' not found.")
        else:
            virt_up.Instance(name).delete()

@main.group()
def init():
    """
    Initialize configuration files.
    """

@init.command(name='config')
@click.option('--pool', 'settings_pool', default='default', help='Libvirt image storage pool name.')
@click.option('--image_format', 'settings_image_format', default='qcow2', help='Image file format.')
@click.option('--user', 'settings_user',  default='', help='Username to create on base instance.')
@click.option('--password-length', 'settings_password_length', default=12, help='Default generated password length.')
@click.option('--arch', 'settings_arch', default='x86_64', help='Default guest architecture.')
@click.option('--memory', 'settings_memory', type=int, default=1024, help='Default guest memory in MB.')
@click.option('--vcpus', 'settings_vcpus', type=int, default=1, help='Default guest virtual cpus.')
@click.option('--graphics', 'settings_graphics', default='none', help='Default graphics mode.')
@click.option('--dns_domain', 'settings_dns_domain', default='', help='DNS domain name')
@click.option('--address_source', 'settings_address_source', default='agent', help='Address source method.')
@click.option('--force', is_flag=True, help='Overwrite existing configuration.')
def init_config(force, **settings):
    """
    Initialize general configuration.
    """
    # Lookup the path to our embedded cookiecutter template.
    basedir = pathlib.Path(__file__).resolve().parent
    template = str(basedir / 'cookiecutter' / 'config')

    # Get configuration destination directory. Users may define
    # VIRTUP_CONFIG_HOME env var to specify an alternate location.
    # Use /etc/virt-up when running as root to set the global config.
    if os.geteuid() == 0:
        config_home = pathlib.Path('/etc/virt-up')
    else:
        config_home = pathlib.Path(virt_up.instance.virtup_config_home).resolve()
    if config_home.exists() and not force:
        click.echo(f"Configuration directory '{config_home}' already exists. " \
                    "(Use --force to overwrite.)", err=True)
        return 1

    context = {
        'config_parent': str(config_home.parent),
        'config_directory': config_home.name,
        **settings,
    }
    cookiecutter(
        template,
        extra_context=context,
        output_dir=context['config_parent'],
        no_input=True,
        overwrite_if_exists=force)
    click.echo(f"Wrote directory '{config_home}'.")

@init.command(name='template')
@click.argument('name')
@click.option('--force', is_flag=True, help='Overwrite existing configuration.')
@click.option('--template-filename')
@click.option('--os', type=click.Choice(_template_oses), default='other')
@click.option('--desc')
@click.option('--os-version')
@click.option('--os-type')
@click.option('--os-variant')
@click.option('--arch')
@click.option('--pool')
@click.option('--user')
@click.option('--image-format')
@click.option('--memory')
@click.option('--vcpus')
@click.option('--graphics')
@click.option('--dns-domain')
@click.option('--address-source')
@click.option('--virt-builder-args')
@click.option('--virt-sysprep-args')
@click.option('--virt-install-args')
@click.option('--cp-args')
@click.option('--template-playbook')
@click.option('--instance-playbook')
def init_template(name, template_filename, force, **args):
    """
    Create a template definition.
    """
    import pprint
    pprint.pprint(args)
    # Lookup the path to our embedded cookiecutter template.
    basedir = pathlib.Path(__file__).resolve().parent
    template = str(basedir / 'cookiecutter' / 'template')

    # Get template configuration destination directory. Users may define
    # VIRTUP_CONFIG_HOME env var to specify an alternate location.
    config_home = pathlib.Path(virt_up.instance.virtup_config_home).resolve()

    # template name -> file name
    if not template_filename:
        safe = set(string.ascii_letters + string.digits + '_-.')
        template_file = ''.join([c if c in safe else '-' for c in name])
    if not template_file.endswith('.cfg'):
        template_file += '.cfg'

    context = {
        'config_path': str(config_home),
        'templates_directory': 'templates.d',
        'template_name': name,
        'template_file': template_file,
        **args,
    }
    pprint.pprint(context)

    target = config_home / context['templates_directory'] / context['template_file']
    if target.exists() and not force:
        click.echo(f"Template file '{target}' already exists. " \
                    "(Use --force to overwrite.)", err=True)
        return 1

    cookiecutter(
        template,
        extra_context=context,
        output_dir=context['config_path'],
        no_input=True,
        overwrite_if_exists=True)
    click.echo(f"Wrote file '{target}'.")

@main.command(name='list')
@click.option('-a', '--all', is_flag=True, help='List base instances too.')
def list_(all):
    """
    List instances.
    """
    for instance in virt_up.Instance.all():
        if all or not instance.is_template():
            click.echo(f'{instance.name}')

@main.group()
def show():
    """
    Show configuration information.
    """
@show.command(name='paths')
def show_paths():
    """
    Show configuration and data paths.
    """
    config_home = pathlib.Path(virt_up.instance.virtup_config_home).resolve()
    data_home = pathlib.Path(virt_up.instance.virtup_data_home).resolve()
    sshkeys = data_home / 'sshkeys'
    playbooks = config_home / 'playbooks'
    inventory = data_home / 'inventory.yaml'
    click.echo(f'VIRTUP_CONFIG_HOME="{config_home}"')
    click.echo(f'VIRTUP_DATA_HOME="{data_home}"')
    click.echo(f'VIRTUP_SSHKEYS="{sshkeys}"')
    click.echo(f'VIRTUP_PLAYBOOKS="{playbooks}"')
    click.echo(f'VIRTUP_INVENTORY="{inventory}"')

@show.command(name='playbooks')
@click.option('--full-path', is_flag=True, help='Show full playbook file path.')
def show_playbooks(full_path):
    """
    Show available playbooks.
    """
    config_home = pathlib.Path(virt_up.instance.virtup_config_home).resolve()
    path = config_home / 'playbooks'
    playbooks = list(path.glob('*.yml')) + list(path.glob('*.yaml'))
    for playbook in sorted(playbooks):
        if full_path:
            click.echo(playbook)
        else:
            click.echo(playbook.name)

@show.command(name='templates')
def show_templates():
    """
    Show available template definitions.
    """
    heading = ('# template', 'description', 'arch')
    click.echo(f"{heading[0]: <24} {heading[1]: <30} {heading[2]}")
    for s in virt_up.instance.Settings.all():
        click.echo(f"{s.template_name: <24} {s.desc: <30} {s.arch}")

@show.command(name='instance')
@click.argument('name')
def show_instance(name):
    """
    Show instance metadata.
    """
    if not virt_up.Instance.exists(name):
        click.echo(f"Instance '{name}' not found.", err=True)
        return 1
    instance = virt_up.Instance(name)
    click.echo(pprint.pformat(instance.meta))

@show.command(name='ssh-config')
@click.argument('name')
def show_ssh_config(name):
    """
    Show instance ssh config.
    """
    if not virt_up.Instance.exists(name):
        click.echo(f"Instance '{name}' not found.", err=True)
        return 1
    instance = virt_up.Instance(name)
    click.echo(f"Host {name}")
    click.echo(f"    Hostname {instance.meta['address']}")
    click.echo(f"    User {instance.meta['user']['username']}")
    click.echo(f"    IdentityFile {instance.meta['user']['ssh_identity']}")
    ssh_options = instance.meta.get('ssh_options', {})
    for k, v in ssh_options.items():
        click.echo(f"    {k} {v}")

@main.command()
@click.argument('name')
@click.option('-p', '--protocol', type=click.Choice(['ssh', 'sftp']), default='ssh')
def login(name, protocol):
    """
    Login to an instance.
    """
    if not virt_up.Instance.exists(name):
        click.echo(f"Instance '{name}' not found.", err=True)
        return 1
    virt_up.Instance(name).login(mode=protocol)

@main.command()
@click.argument('name')
@click.argument('playbook')
def playbook(name, playbook):
    """
    Run an ansible playbook on an instance.
    """
    if not virt_up.Instance.exists(name):
        click.echo(f"Instance '{name}' not found.", err=True)
        return 1
    virt_up.Instance(name).run_playbook(playbook)

if __name__ == '__main__':
    main()
