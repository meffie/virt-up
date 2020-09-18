from setuptools import setup
import re

try:
    with open('virt_up/__init__.py') as fp:
        __version__ = re.findall(r"__version__ = '(.*)'", fp.read())[0]
except:
    __version__ = 'unknown'

setup(
    name='virt_up',
    version=__version__,
    description='Create virtual machines quickly with virt-builder',
    long_description=open('README.rst').read(),
    author='Michael Meffie',
    author_email='mmeffie@sinenomine.net',
    license='BSD',
    url='https://github.com/meffie/virt-up',
    packages=['virt_up'],
    requires_python='>=3.6',
    setup_requires=['wheel'],
    install_requires=['sh', 'libvirt-python'],
    entry_points={
        'console_scripts': ['virt-up=virt_up.__main__:main'],
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
