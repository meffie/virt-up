# Copyright (c) 2021 Sine Nomine Associates
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

import pathlib
import pytest
import virt_up.instance
from cookiecutter.main import cookiecutter

@pytest.fixture
def config_files(tmp_path):
    """
    Create config files in a temp directory.
    """
    # Lookup the path to our embedded cookiecutter template.
    basedir = pathlib.Path(__file__).resolve().parent.parent
    template = str(basedir / 'tests' / 'cookiecutter' / 'config')
    cookiecutter(
        template,
        extra_context={'config_parent': str(tmp_path)},
        output_dir=str(tmp_path),
        no_input=True,
        overwrite_if_exists=True,
    )
    # Inject the path to the temp config.
    virt_up.instance.virtup_config_home = str(tmp_path / 'virt-up')
    return tmp_path
