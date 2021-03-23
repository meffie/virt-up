.PHONY: help init lint test release sdist wheel rpm deb upload clean distclean

PYTHON3=python3
PYTHON=.venv/bin/python
PIP=.venv/bin/pip
PYFLAKES=.venv/bin/pyflakes
PYTEST=.venv/bin/pytest
TWINE=.venv/bin/twine
T=

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  init       create python virtual env"
	@echo "  lint       run linter"
	@echo "  test       run tests"
	@echo "  release    update version number and create a git tag"
	@echo "  sdist      create source distribution"
	@echo "  wheel      create wheel distribution"
	@echo "  rpm        create rpm package"
	@echo "  deb        create deb package"
	@echo "  upload     upload to pypi.org"
	@echo "  clean      remove generated files"
	@echo "  distclean  remove generated files and virtual env"

init.debian:
	sudo apt-get install -y libvirt-dev

.venv/bin/activate:
	test -d .venv || $(PYTHON3) -m venv .venv
	$(PIP) install -U pip
	$(PIP) install wheel
	$(PIP) install pyflakes pylint pytest collective.checkdocs twine
	$(PIP) install -e .
	touch .venv/bin/activate

init: .venv/bin/activate

lint: init
	$(PYFLAKES) */*.py
	$(PYTHON) setup.py checkdocs

check test: init lint
	$(PYTEST) $(T) tests

release: init
	@if [ "x$(VERSION)" = "x" ]; then echo "usage: make release VERSION=<major>.<minor>.<patch>"; exit 1; fi
	@if git tag --list | grep -q "^v$(VERSION)$$"; then echo "Version $(VERSION) already exists."; exit 1; fi
	sed -i -e "s/__version__ = '.*'/__version__ = '$(VERSION)'/" virt_up/__init__.py
	git add virt_up/__init__.py
	git commit -m "Make version v$(VERSION)"
	git tag -a -m "v$(VERSION)" "v$(VERSION)"

version:
	@dev_version=`git describe | sed -e 's/^v//'`; \
	sed -i -e "s/__version__ = '.*'/__version__ = '$$dev_version'/" virt_up/__init__.py

sdist: init
	$(PYTHON) setup.py sdist

wheel: init
	$(PYTHON) setup.py bdist_wheel

rpm: init
	$(PYTHON) setup.py bdist_rpm

deb: init
	$(PYTHON) setup.py --command-packages=stdeb.command bdist_deb

upload: init sdist wheel
	$(TWINE) upload dist/*

clean:
	rm -rf virt_up/__pycache__
	rm -rf .pytest_cache
	rm -rf build dist .eggs virt_up.egg-info

distclean: clean
	rm -rf .venv
