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
import sys
import logging
import pathlib
import pprint
import string

import sh
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
    # Adjust the sh logger level to avoid printing cmd output
    # unless --debug is given.
    logging.getLogger(sh.__name__).setLevel(level + 10)

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


@main.command(name='list')
@click.option('-a', '--all', is_flag=True, help='List base instances too.')
def list_(all):
    """
    List instances.
    """
    names = []
    for instance in virt_up.Instance.all():
        if all or not instance.is_template():
            names.append(instance.name)
    click.echo('\n'.join(sorted(names)))

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
@click.argument('names', metavar='[<name>]', nargs=-1) # Click does not support 0 or 1 arg.
@click.option('-p', '--protocol', type=click.Choice(['ssh', 'sftp']), default='ssh')
def login(names, protocol):
    """
    Login to an instance.
    """
    if len(names) == 0:
        names = []
        for i in virt_up.Instance.all():
            if not i.is_template():
                names.append(i.name)
        if len(names) == 0:
            click.echo("No instances found.")
            return 1
        if len(names) > 1:
            progname = pathlib.Path(sys.argv[0]).name
            click.echo(f"Select which instance with: {progname} login <name>")
            click.echo("Available instances:")
            click.echo("%s" % "\n".join(sorted(names)))
            return 1
        name = names[0]
    elif len(names) == 1:
        name = names[0]
        if not virt_up.Instance.exists(name):
            click.echo(f"Instance '{name}' not found.", err=True)
            return 1
    if len(names) > 1:
        click.echo("Too many names.")
        return 1
    instance = virt_up.Instance(name)
    instance.login(mode=protocol)

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
