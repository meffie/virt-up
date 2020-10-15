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

import argparse
import logging
import sys

from virt_up import __version__
from virt_up.instance import Instance, Settings

usage="""\
virt-up [--name] <name> [--template <template>] [options]
               --list [--all] | --list-templates
               --login [--name] <name> [--command "<command>"]
               --delete [--name] <name> | --delete --all
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

def list_instances(args):
    """
    List instances.
    """
    clones_only = (not args.all)
    for name in sorted(Instance.list(clones_only)):
        sys.stdout.write(f'{name}\n')

def list_templates(args):
    """
    List available templates.
    """
    settings = Settings()
    for name in sorted(settings.templates.keys()):
        template = settings.templates[name]
        template['name'] = name
        sys.stdout.write("{name: <24} {desc: <30} {arch}\n".format(**template))

def delete(args):
    """
    Delete the instance.
    """
    if not (bool(args.name) ^ bool(args.all)):
        die(f'<name> or --all is required.\nusage: {usage}')
    if args.name:
        if Instance.exists(args.name):
            instance = Instance(args.name)
            instance.delete()
    else:
        names = list(Instance.list(clones_only=False))
        if names:
            if args.yes:
                answer = 'yes'
            else:
                names_str = ', '.join(names)
                sys.stdout.write(f'About to delete instances: {names_str}\n')
                answer = input('Continue? [y/n] > ').lower()
            if answer in ('y', 'yes'):
                for name in names:
                    if Instance.exists(name):
                        instance = Instance(name)
                        instance.delete()

def login(args):
    """
    Login to an existing instance with ssh.
    """
    if not args.name:
        die(f'<name> is required.\nusage: {usage}')
    if not Instance.exists(args.name):
        log.error(f"Instance '{args.name}' not found.")
    else:
        instance = Instance(args.name)
        instance.login(args.command)

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

    if not name:
        die(f'<name> is required.\nusage: {usage}')

    try:
        template = Instance.build(name=template, template=template, prefix=prefix, **options)
        if args.no_clone:
            return
        instance = template.clone(name, **options)
        instance.wait_for_port(22)
        log.info(f"Instance '{instance.name}' is up.")
    except ValueError as e:
        die(e)
    except LookupError as e:
        die(e)

def main():
    parser = argparse.ArgumentParser(prog='virt-up', usage=usage)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--version', action='version', version='%(prog)s '+ __version__)
    group.add_argument('--list', action='store_true', help='list instances')
    group.add_argument('--list-templates', action='store_true', help='list template names')
    group.add_argument('--delete', action='store_true', help='delete the instance')
    group.add_argument('--login', action='store_true', help=argparse.SUPPRESS)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('name', metavar='<name>', nargs='?', help='instance name')
    group.add_argument('-n', '--name', dest='name_flag', metavar='<name>', help=argparse.SUPPRESS) # Optional --name flag

    parser.add_argument('-t', '--template', metavar='<template>', help='template name (default: <name>)')
    parser.add_argument('--root-password', metavar='<root-password>', help='root password (default: random)')
    parser.add_argument('--user', metavar='<user>', help='username (default: virt)')
    parser.add_argument('--password', metavar='<password>', help='password (default: random)')
    parser.add_argument('--size', metavar='<size>', help='instance disk size (default: image size)')
    parser.add_argument('--memory', metavar='<memory>', help='instance memory (default: 512)', default=512)
    parser.add_argument('--vcpus', metavar='<vcpus>', help='instance vcpus (default: 1)', default=1)
    parser.add_argument('--graphics', metavar='<graphics>', help='instance graphics type (default: none)', default='none')
    parser.add_argument('--dns-domain', metavar='<dns-domain>', help='dns domain name')

    parser.add_argument('--command', metavar='<command>', help='--login ssh command')
    parser.add_argument('--no-clone', action='store_true', help='build template instance only')
    parser.add_argument('--no-inventory', dest='inventory', action='store_false',
                                          help='exclude instance from the virt-up ansible inventory file')
    parser.add_argument('--all', action='store_true', help='include template instances')
    parser.add_argument('--yes', action='store_true', help='answer yes to interactive questions')
    parser.add_argument('--quiet', action='store_true', help='show less output')
    parser.add_argument('--debug', action='store_true', help='show debug tracing')

    args = parser.parse_args()
    if args.name_flag:
        args.name = args.name_flag # Support optional --name flag, i.e. [--name] <name>.

    logging.basicConfig(
        level=get_log_level(args),
        format='%(message)s')

    if args.list:
        list_instances(args)
    elif args.list_templates:
        list_templates(args)
    elif args.delete:
        delete(args)
    elif args.login:
        login(args)
    else:
        create(args)

if __name__ == '__main__':
    main()
