from distutils.command.build_ext import build_ext
from distutils import sysconfig
#from distutils.core import setup
from setuptools import setup, Extension

import os, sys
from os import chdir, getcwd
from os.path import abspath, dirname, split, samefile
import shlex
from subprocess import check_output

import re

# Check if we're running 64-bit Python
is_64_bit = sys.maxsize > 2**32

# Check if this is a debug build of Python.
if hasattr(sys, 'gettotalrefcount'):
    build_type = 'Debug'
else:
    build_type = 'Release'

class cmake_build_ext(build_ext):
  description = "Build the C-extension for dynd-python with CMake"
  user_options = [('extra-cmake-args=', None, 'extra arguments for CMake')]

  def get_ext_path(self, name):
    # Get the package directory from build_py
    build_py = self.get_finalized_command('build_py')
    package_dir = build_py.get_package_dir('dynd')
    # This is the name of the dynd-python C-extension
    suffix = sysconfig.get_config_var('EXT_SUFFIX')
    if (suffix is None):
      suffix = sysconfig.get_config_var('SO')
    filename = name + suffix
    return os.path.join(package_dir, filename)

  def get_ext_built(self, name):
    suffix = sysconfig.get_config_var('SO')
    return os.path.join('dynd', *os.path.split(name)) + suffix

  def initialize_options(self):
    build_ext.initialize_options(self)
    self.extra_cmake_args = ''

  def run(self):
    global build_type

    # We don't call the origin build_ext, instead ignore that
    # default behavior and call cmake for DyND's one C-extension.

    # The directory containing this setup.py
    source = dirname(abspath(__file__))

    # The staging directory for the module being built
    if self.inplace:
        # In `python setup.py develop` mode, always build C++ code
        # in the 'build-dev' dir.
        build_temp = os.path.join(os.getcwd(), 'build-dev')
    else:
        build_temp = os.path.join(os.getcwd(), self.build_temp)
        build_lib = os.path.join(os.getcwd(), self.build_lib)

    # Change to the build directory
    saved_cwd = getcwd()
    if not os.path.isdir(build_temp):
        self.mkpath(build_temp)
    chdir(build_temp)

    # Detect if we built elsewhere
    if os.path.isfile('CMakeCache.txt'):
        cachefile = open('CMakeCache.txt', 'r')
        cachedir = re.search('CMAKE_CACHEFILE_DIR:INTERNAL=(.*)', cachefile.read()).group(1)
        cachefile.close()

        if not samefile(cachedir, build_temp):
            return

    pyexe_option = '-DPYTHON_EXECUTABLE=%s' % sys.executable
    install_lib_option = '-DDYND_INSTALL_LIB=ON'
    static_lib_option = ''
    build_tests_option = ''
    inplace_build_option = ''

    # If libdynd is checked out into the libdynd subdir,
    # we want to build libdynd as part of dynd-python, not
    # separately like the default does.
    libdynd_in_tree = os.path.isfile(
            os.path.join(source, 'libdynd/include/dynd/array.hpp'))
    if libdynd_in_tree:
        install_lib_option = '-DDYND_INSTALL_LIB=OFF'
        build_tests_option = '-DDYND_BUILD_TESTS=OFF'

    # If the build is done inplace, require libdynd be included in the build
    if self.inplace:
        if not libdynd_in_tree:
            raise RuntimeError('For an in-tree build with'
                               ' "python setup.py develop",'
                               ' libdynd must be checked out in the'
                               ' dynd-python subdirectory')
        # Definitely want the tests in 'develop' mode
        build_tests_option = '-DDYND_BUILD_TESTS=ON'
        # This option causes the cmake config to copy the binaries into the
        # tree every time they are built
        inplace_build_option = '-DDYND_PYTHON_INPLACE_BUILD=ON'
        # Enable debug info
        if build_type == 'Release':
            build_type = 'RelWithDebInfo'


    extra_cmake_args = shlex.split(self.extra_cmake_args)
    cmake_command = ['cmake'] + extra_cmake_args + [pyexe_option,
                     install_lib_option, build_tests_option,
                     inplace_build_option, static_lib_option]
    if sys.platform != 'win32':
        cmake_command.append(source)
        self.spawn(cmake_command)
        self.spawn(['make'])
    else:
        if "-G" not in self.extra_cmake_args:
            cmake_generator = 'Visual Studio 14 2015'
            if is_64_bit:
                cmake_generator += ' Win64'
            cmake_command += ['-G', cmake_generator]
        cmake_command.append(source)
        self.spawn(cmake_command)
        # Do the build
        self.spawn(['cmake', '--build', '.', '--config', build_type])

    import glob, shutil

    if not self.inplace:
        if install_lib_option.split('=')[1] == 'OFF':
            if sys.platform != 'win32':
                names = glob.glob('libdynd/libdy*.*')
            else:
                names = glob.glob('libdynd/%s/libdy*.*' % build_type)
            for name in names:
                short_name = split(name)[1]
                shutil.move(name, os.path.join(build_lib, 'dynd', short_name))

        # Move the built C-extension to the place expected by the Python build
        self._found_names = []
        for name in self.get_expected_names():
            built_path = self.get_ext_built(name)
            print(os.getcwd())
            if os.path.exists(built_path):
                ext_path = os.path.join(build_lib, self.get_ext_path(name))
                if os.path.exists(ext_path):
                    os.remove(ext_path)
                self.mkpath(os.path.dirname(ext_path))
                print('Moving built DyND C-extension', built_path,
                      'to build path', ext_path)
                shutil.move(self.get_ext_built(name), ext_path)
                self._found_names.append(name)
            else:
                raise RuntimeError('DyND C-extension failed to build:',
                                   os.path.abspath(built_path))

    chdir(saved_cwd)

  def get_expected_names(self):
    return ['config', os.path.join('ndt', 'type'), os.path.join('ndt', 'json'), \
        os.path.join('nd', 'array'), os.path.join('nd', 'callable'), \
        os.path.join('nd', 'functional'), os.path.join('nd', 'registry')]

  def get_names(self):
    return self._found_names

  def get_outputs(self):
    # Just the C extensions
    return [self.get_ext_path(name) for name in self.get_names()]


# Get the version number to use from git
ver = check_output(['git', 'describe', '--dirty',
                    '--always', '--match', 'v*']).decode('ascii').strip('\n')

# Same processing as in __init__.py
if '.' in ver:
    vlst = ver.lstrip('v').split('.')
    vlst = vlst[:-1] + vlst[-1].split('-')

    if len(vlst) > 3:
        # The 4th one may not be, so trap it
        try:
            # Zero pad the dev version #, so it sorts lexicographically
            vlst[3] = 'dev%03d' % int(vlst[3])
            # increment the third version number, so
            # the '.dev##' versioning convention works
            vlst[2] = str(int(vlst[2]) + 1)
        except ValueError:
            pass
        ver = '.'.join(vlst[:4])
        # Can't use the local version on PyPI, so just exclude this part
        # + '+' + '.'.join(vlst[4:])
    else:
        ver = '.'.join(vlst)

setup(
    name = 'dynd',
    description = 'Python exposure of DyND',
    version = ver,
    author = 'DyND Developers',
    author_email = 'libdynd-dev@googlegroups.com',
    license = 'BSD',
    url = 'http://libdynd.org',
    packages = [
        'dynd',
        'dynd.nd',
        'dynd.ndt',
        'dynd.tests',
    ],
    package_data = {'dynd': ['*.pxd', 'nd/*.pxd', 'ndt/*.pxd', 'include/*.hpp',
                             'include/kernels/*.hpp', 'cpp/*.pxd',
                             'cpp/eval/*.pxd', 'cpp/func/*.pxd',
                             'cpp/types/*.pxd']},
    # build_ext is overridden to call cmake, the Extension is just
    # needed so things like bdist_wheel understand what's going on.
    ext_modules = [Extension('config', sources=[])],
    # This includes both build and install requirements. Setuptools' setup_requires
    # option does not actually install things, so isn't actually helpful...
    install_requires=open('dev-requirements.txt').read().strip().split('\n'),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
    ],
    cmdclass = {'build_ext': cmake_build_ext},
)
