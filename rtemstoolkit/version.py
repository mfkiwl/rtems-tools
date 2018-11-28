#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2018 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

#
# Releasing RTEMS Tools
# ---------------------
#
# Format:
#
#  The format is INI. The file requires a `[version`] section and a `revision`
#  option:
#
#   [version]
#   revision = <version-string>
#
#  The `<version-string>` has the `version` and `revision` delimited by a
#  single `.`. An example file is:
#
#   [version]
#   revision = 5.0.not_released
#
#  where the `version` is `5` and the revision is `0` and the package is not
#  released. The label `not_released` is reversed to mean the package is not
#  released. A revision string can contain extra characters after the
#  `revision` number for example `5.0-rc1` or is deploying a package
#  `5.0-nasa-cfs`
#
#  Packages can optionally add specialised sections to a version configuration
#  files. These can be accessed via the:
#
#   load_release_settings: Return the items in a section
#   load_release_setting: Return an item from a section
#
# User deployment:
#
#  Create a git archive and then add a suitable VERSION file to the top
#  directory of the package. The package assumes your python executable is
#  location in `bin` directory which is one below the top of the package's
#  install prefix.
#
# RTEMS Release:
#
#  Set the values in the `rtems-version.ini` file. This is a shared file so
#  packages and encouraged to add specific settings to other configuration
#  files.
#
# Notes:
#
#  This module uses os.apth for paths and assumes all paths are in the host
#  format.
#

from __future__ import print_function

import itertools
import os
import sys

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from rtemstoolkit import error
from rtemstoolkit import git
from rtemstoolkit import path
from rtemstoolkit import rtems

#
# Default to an internal string.
#
_version = 'undefined'
_revision = 'not_released'
_version_str = '%s.%s' % (_version, _revision)
_released = False
_git = False
_is_loaded = False

def _top():
    top = os.path.dirname(sys.argv[0])
    if len(top) == 0:
        top = '.'
    return top

def _load_released_version_config():
    '''Local worker to load a configuration file.'''
    top = _top()
    for ver in [os.path.join(top, 'VERSION'),
                os.path.join('..', 'VERSION'),
                rtems.configuration_file('rtems-version.ini')]:
        if path.exists(path.join(ver)):
            v = configparser.SafeConfigParser()
            try:
                v.read(path.host(ver))
            except Exception as e:
                raise error.general('Invalid version config format: %s: %s' % (ver,
                                                                               e))
            return ver, v
    return None, None

def _load_released_version():
    '''Load the release data if present. If not found the package is not released.

    A release can be made by adding a file called `VERSION` to the top level
    directory of a package. This is useful for user deploying a package and
    making custom releases.

    The RTEMS project reserves the `rtems-version.ini` file for it's
    releases. This is the base release and should not be touched by users
    deploying a package.

    '''
    global _version
    global _revision
    global _released
    global _version_str
    global _is_loaded

    if not _is_loaded:
        vc, v = _load_released_version_config()
        if v is not None:
            try:
                ver_str = v.get('version', 'revision')
            except Exception as e:
                raise error.general('Invalid version file: %s: %s' % (vc, e))
            ver_split = ver_str.split('.')
            if len(ver_split) < 2:
                raise error.general('Invalid version release value: %s: %s' % (vc,
                                                                               ver_str))
            ver = ver_split[0]
            rev = '.'.join(ver_split[1:])
            try:
                _version = int(ver)
            except:
                raise error.general('Invalid version config value: %s: %s' % (vc,
                                                                              ver))
            try:
                _revision = int(''.join(itertools.takewhile(str.isdigit, str(rev))))
            except Exception as e:
                raise error.general('Invalid revision config value: %s: %s: %s' % (vc,
                                                                                   rev,
                                                                                   e))
            if not 'not_released' in ver:
                _released = True
            _version_str = ver_str
            _is_loaded = True
    return _released

def _load_git_version():
    global _version
    global _revision
    global _git
    global _version_str
    repo = git.repo(_top())
    if repo.valid():
        head = repo.head()
        if repo.dirty():
            modified = 'modified'
            sep = ' '
        else:
            modified = ''
            sep = ''
        _revision = '%s-%s' % (head[0:12], modified)
        _version_str = '%s (%s%s%s)' % (_version, head[0:12], sep, modified)
        _git = True
    return _git

def load_release_settings(section, error = False):
    vc, v = _load_released_version_config()
    items = []
    if v is not None:
        try:
            items = v.items(section)
        except Exception as e:
            if not isinstance(error, bool):
                error(e)
            elif error:
                raise error.general('Invalid config section: %s: %s: %s' % (vc,
                                                                            section,
                                                                            e))
    return items

def load_release_setting(section, option, raw = False, error = False):
    vc, v = _load_released_version_config()
    value = None
    if v is not None:
        try:
            value = v.get(section, option, raw = raw)
        except Exception as e:
            if not isinstance(error, bool):
                error(e)
            elif error:
                raise error.general('Invalid config section: %s: %s: %s.%s' % (vc,
                                                                               section,
                                                                               option,
                                                                               e))
    return value

def released():
    return _load_released_version()

def version_control():
    return _load_git_version()

def string():
    _load_released_version()
    _load_git_version()
    return _version_str

def version():
    _load_released_version()
    _load_git_version()
    return _version

def revision():
    _load_released_version()
    _load_git_version()
    return _revision

if __name__ == '__main__':
    print('Version: %s' % (str(version())))
    print('Revision: %s' % (str(revision())))
    print('String: %s' % (string()))
    if version() == 'undefined':
        raise Exception('version is undefined')
