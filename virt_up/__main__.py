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

import argparse
import logging
import os
import sys

from virt_up import __version__
from virt_up.instance import Instance, Settings

usage="""virt-up [--name] <name> --template <template> [create-options]
       virt-up [--name] <name> --login [--sftp|--command "<command>"]
       virt-up [--name] <name> --playbook <playbook>
       virt-up [--name] <name> --delete | --delete --all
       virt-up --init [--force]
       virt-up --list [--all]
       virt-up --show-templates | --show-paths
"""

log = logging.getLogger(__name__)

def die(msg):
    """
    Invalid or missing command line argument.
    """
    sys.stderr.write(f'{msg}\n')
    sys.exit(1)

def get_log_level(args):
    """
    Determine the logging level from the verbosity command line options.
    """
    if args.debug:
        return logging.DEBUG
    if args.quiet:
        return logging.WARN
    return logging.INFO

def init(args):
    """
    Initialize configuration files.
    """
    import virt_up.config
    import virt_up.instance
    if os.getuid() == 0:
        dest = '/etc/virt-up'
    else:
        dest = virt_up.instance.virtup_config_home
    sys.stdout.write(f"Initializing files in {dest}\n")
    wrote = virt_up.config.create_files(dest, force=args.force)
    for w in wrote:
        sys.stdout.write(f"Wrote: {w}\n")

def list_instances(args):
    """
    List instances.
    """
    for instance in Instance.all():
        if args.all or not instance.is_template():
            sys.stdout.write(f'{instance.name}\n')

def show_templates(args):
    """
    Show available template definitions.
    """
    for s in Settings.all():
        sys.stdout.write(f"{s.template_name: <24} {s.desc: <30} {s.arch}\n")

def show_paths(args):
    """
    Show configuration and data paths.
    """
    from virt_up.instance import virtup_config_home, virtup_data_home
    virtup_playbooks = os.path.join(virtup_config_home, 'playbooks')
    virtup_inventory = os.path.join(virtup_data_home, 'inventory.yaml')
    sys.stdout.write(f'VIRTUP_CONFIG_HOME="{virtup_config_home}"\n')
    sys.stdout.write(f'VIRTUP_DATA_HOME="{virtup_data_home}"\n')
    sys.stdout.write(f'VIRTUP_PLAYBOOKS="{virtup_playbooks}"\n')
    sys.stdout.write(f'VIRTUP_INVENTORY="{virtup_inventory}"\n')

def delete(args):
    """
    Delete the instance or all of the instances.
    """
    if not (bool(args.name) ^ bool(args.all)):
        die(f'<name> or --all is required.\nusage: {usage}')

    if not args.name:
        delete_all(args)
    elif Instance.exists(args.name):
        instance = Instance(args.name)
        instance.delete()

def delete_all(args):
    # Remove clones first, then templates.
    clones = []
    templates = []
    for instance in Instance.all():
        if instance.is_template():
            templates.append(instance)
        else:
            clones.append(instance)
    if not args.yes:
        names = []
        names.extend([i.name for i in clones])
        names.extend([i.name for i in templates])
        names = ', '.join(names)
        sys.stdout.write(f'About to delete: {names}\n')
        answer = input('Continue? [y/n] > ').lower()
        if answer not in ('y', 'yes'):
            return # bail
    for instance in clones:
        instance.delete()
    for instance in templates:
        instance.delete()

def login(args):
    """
    Login to an existing instance with ssh.
    """
    if not args.name:
        die(f'<name> is required.\nusage: {usage}')
    if not Instance.exists(args.name):
        log.error(f"Instance '{args.name}' not found.")
        return
    options = {}
    if args.sftp:
        options['mode'] = 'sftp'
    if args.command:
        options['command'] = args.command
    instance = Instance(args.name)
    instance.login(**options)

def playbook(args):
    """
    Run an ansible playbook on the instance.
    """
    if not args.name:
        die(f'<name> is required.\nusage: {usage}')
    instance = Instance(args.name)
    instance.run_playbook(args.playbook)

def create(args):
    """
    Build a template with virt-builder if it does not exist, and then clone
    the template to create a new instance. Just start the instance if it
    already exists.
    """
    options = vars(args)
    name = options.pop('name', None)
    template = options.pop('template', name)
    prefix = options.pop('prefix', 'TEMPLATE-')

    if not (name or args.no_clone):
        die(f'<name> is required.\nusage: {usage}')

    try:
        template = Instance.build(name=template, template=template, prefix=prefix, **options)
        if args.no_clone:
            return
        instance = template.clone(name, **options)
        instance.wait_for_port(22)
        log.info(f"Instance '{instance.name}' is up.")
    except KeyError as e:
        raise(e)
    except ValueError as e:
        die('ValueError:' + str(e))
    except LookupError as e:
        die('LookupError: ' + str(e))

def main():
    parser = argparse.ArgumentParser(prog='virt-up', usage=usage)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--version', action='version', version='%(prog)s '+ __version__)
    group.add_argument('--init', action='store_true', help='initialize configuration files')
    group.add_argument('--list', action='store_true', help='list instances')
    group.add_argument('--show-templates', action='store_true', help='show template definitions')
    group.add_argument('--show-paths', action='store_true', help='show configuration and data paths')
    group.add_argument('--delete', action='store_true', help='delete the instance')
    group.add_argument('--login', action='store_true', help='login to a running instance')
    group.add_argument('--playbook', help='run ansible playbook on instance')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('name', metavar='<name>', nargs='?', help='instance name')
    group.add_argument('-n', '--name', dest='name_flag', metavar='<name>', help=argparse.SUPPRESS) # Optional --name flag

    parser.add_argument('-t', '--template', metavar='<template>', help='template name (default: <name>)')
    parser.add_argument('--root-password', metavar='<root-password>', help='root password (default: random)')
    parser.add_argument('--user', metavar='<user>', help='username (default: virt)')
    parser.add_argument('--password', metavar='<password>', help='password (default: random)')
    parser.add_argument('--size', metavar='<size>', help='instance disk size (default: image size)')
    parser.add_argument('--memory', metavar='<memory>', help='instance memory')
    parser.add_argument('--vcpus', metavar='<vcpus>', help='instance vcpus')
    parser.add_argument('--graphics', metavar='<graphics>', help='instance graphics type')
    parser.add_argument('--dns-domain', metavar='<dns-domain>', help='dns domain name')

    parser.add_argument('--sftp', action='store_true', help='--login with sftp')
    parser.add_argument('--command', metavar='<command>', help='--login ssh command')
    parser.add_argument('--no-clone', action='store_true', help='build template instance only')
    parser.add_argument('--no-inventory', dest='inventory', action='store_false',
                                          help='exclude instance from the virt-up ansible inventory file')
    parser.add_argument('--all', action='store_true', help='include template instances')
    parser.add_argument('--yes', action='store_true', help='answer yes to interactive questions')
    parser.add_argument('--quiet', action='store_true', help='show less output')
    parser.add_argument('--debug', action='store_true', help='show debug tracing')
    parser.add_argument('--force', action='store_true', help='overwrite files')

    args = parser.parse_args()
    if args.name_flag:
        args.name = args.name_flag # Support optional --name flag, i.e. [--name] <name>.

    logging.basicConfig(
        level=get_log_level(args),
        format='%(message)s')

    if args.init:
        init(args)
    elif args.list:
        list_instances(args)
    elif args.show_templates:
        show_templates(args)
    elif args.show_paths:
        show_paths(args)
    elif args.delete:
        delete(args)
    elif args.login:
        login(args)
    elif args.playbook:
        playbook(args)
    else:
        create(args)

if __name__ == '__main__':
    main()
