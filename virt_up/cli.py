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

import sys
import pathlib
import logging
import click
import virt_up


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
@click.argument('name')
@click.option('-t', '--template', help='Template name. See show-templates for available names.', default='default')
@click.option('--prefix', help='Base instance prefix.', default='VIRTUP-')
@click.option('--size', help='Disk size and units, e.g. 10G')
@click.option('--memory', help='Memory in MB.')
@click.option('--vcpus', help='Number of virtual cpus.')
@click.option('--graphics', help='Graphics type.')
@click.option('--dns-domain', help='DNS domain name.')
@click.option('--inventory/--no-inventory', help='Include/exclude from virt-up ansible inventory.', default=True)
def create(name, prefix, template, **args):
    """
    Create a new instance.

    Start the instance when it already exists. Build a base instance from the
    virt-builder template image, if the base instance does not exist. Clone
    the base instance to create the new named instance.
    """
    try:
        if virt_up.Instance.exists(name):
            click.echo(f"Instance '{name}' already exists.")
            instance = virt_up.Instance(name)
        else:
            click.echo(f"Creating base instance from template '{template}'.")
            base = virt_up.Instance.build(template, **args)
            click.echo(f"Cloning instance '{name}' from base instance '{base.name}'.")
            instance = base.clone(name, **args)
        instance.wait_for_port(22)
        click.echo(f"Instance '{instance.name}' is up.")
    except ValueError as e:
        click.echo('Error:' + str(e), err=True)
        sys.exit(1)
    except LookupError as e:
        click.echo('Error: ' + str(e), err=True)
        sys.exit(1)

@main.command()
@click.argument('name')
def destroy(name):
    """
    Destroy the instance.
    """
    if not virt_up.Instance.exists(name):
        click.echo(f"Instance '{name}' not found.")
    else:
        virt_up.Instance(name).delete()

@main.command()
@click.option('--force', is_flag=True)
def init(force):
    """
    Initialize configuration files.
    """
    # TODO: replace with embedded (cookiecutter?) templates
    import os
    import virt_up.config
    import virt_up.instance
    if os.getuid() == 0:
        dest = '/etc/virt-up'
    else:
        dest = virt_up.instance.virtup_config_home
    click.echo(f"Initializing files in {dest}")
    wrote = virt_up.config.create_files(dest, force)
    for w in wrote:
        click.echo(f"Wrote: {w}")

@main.command(name='list')
@click.option('-a', '--all', is_flag=True, help='List base instances too.')
def list_(all):
    """
    List existing instances.
    """
    for instance in virt_up.Instance.all():
        if all or not instance.is_template():
            click.echo(f'{instance.name}')

@main.command()
def show_paths():
    """
    Show configuration and data paths.
    """
    config_home = pathlib.Path(virt_up.instance.virtup_config_home).resolve()
    data_home = pathlib.Path(virt_up.instance.virtup_data_home).resolve()
    playbooks = config_home / 'playbooks'
    inventory = data_home / 'inventory.yaml'
    click.echo(f'VIRTUP_CONFIG_HOME="{config_home}"')
    click.echo(f'VIRTUP_DATA_HOME="{data_home}"')
    click.echo(f'VIRTUP_PLAYBOOKS="{playbooks}"')
    click.echo(f'VIRTUP_INVENTORY="{inventory}"')

@main.command()
def show_templates():
    """
    Show available template definitions.
    """
    heading = ('# template', 'description', 'arch')
    click.echo(f"{heading[0]: <24} {heading[1]: <30} {heading[2]}")
    for s in virt_up.instance.Settings.all():
        click.echo(f"{s.template_name: <24} {s.desc: <30} {s.arch}")

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
