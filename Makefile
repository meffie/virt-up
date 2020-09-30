.PHONY: help init lint test release sdist wheel rpm deb upload clean distclean

PYTHON=.venv/bin/python
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

.init:
	test -d .venv || /usr/bin/python3 -m venv .venv
	. .venv/bin/activate && pip install -U wheel
	. .venv/bin/activate && pip install -U pyflakes pylint pytest collective.checkdocs twine
	. .venv/bin/activate && pip install -U -e .
	touch .init

init: .init

lint: init
	$(PYFLAKES) */*.py
	$(PYTHON) setup.py checkdocs

check test: init lint
	$(PYTEST) $(T) tests

release: init
	@if [ "x$(VERSION)" = "x" ]; then echo "usage: make release VERSION=<version>"; exit 1; fi
	@if git tag --list | grep -q "^v$(VERSION)$$"; then echo "Version $(VERSION) already exists."; exit 1; fi
	sed -i -e "s/__version__ = '.*'/__version__ = '$(VERSION)'/" virt_up/__init__.py
	git add virt_up/__init__.py
	git commit -m "Make version v$(VERSION)"
	git tag -a -m "v$(VERSION)" "v$(VERSION)"

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
	rm -rf dist .eggs virt_up.egg-info

distclean: clean
	rm -rf .init .venv
