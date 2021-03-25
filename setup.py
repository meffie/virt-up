from setuptools import setup
import re

name = 'virt_up'
description = 'Create virtual machines quickly with virt-builder.'

def find_version():
    text = open('%s/__init__.py' % name).read()
    return re.search(r"__version__\s*=\s*'(.*)'", text).group(1)

setup(
    name=name,
    version=find_version(),
    description=description,
    long_description=open('README.rst').read(),
    author='Michael Meffie',
    author_email='mmeffie@sinenomine.net',
    license='BSD',
    url='https://github.com/meffie/virt-up',
    packages=[name],
    include_package_data=True,
    setup_requires=['wheel'],
    install_requires=[
        'Click',
        'cookiecutter',
        'libvirt-python',
        'sh',
    ],
    entry_points={
        'console_scripts': [
            'virt-up=%s.cli:main' % name,
            'vu=%s.cli:main' % name,
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
    ],
)
