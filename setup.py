from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import logging
logging.basicConfig(level=logging.INFO)

here = os.path.abspath(os.path.dirname(__file__))
sources_dir = os.path.join(here, 'tools/bin/components')
package = os.path.join(here, 'polymer_bricks/polymer_components')
#polymer_tools_repo = "http://github.com/Polymer/tools.git"
polymer_tools_repo = "https://github.com/Zer0-/tools.git"
extra_sources = (
    "https://github.com/chjj/marked",
)

requires = [
    'bricks',
]

setup_requires = [
    'lxml',
]

links = [
    'git+https://github.com/Zer0-/bricks.git#egg=bricks',
]

def env_check():
    commands = ('git', 'npm', 'node')
    for c in commands:
        if os.system(c + ' --version') != 0:
            raise Exception("Need " + c)

def git_clone(repo, target_dir):
    os.system("cd {}; git clone {}".format(target_dir, repo))

env_check()

def build_component_package():
    import package_builder
    git_clone(polymer_tools_repo, here)
    #run pull-all.sh
    _tools = os.path.join(here, 'tools/bin')
    os.system('cd {}; sh {}/pull-all.sh'.format(_tools, _tools))
    for extra in extra_sources:
        git_clone(extra, sources_dir)

    if not os.path.isdir(package):
        os.mkdir(package)
    package_builder.build_component_directory(sources_dir, package)

def with_build(command_subclass):
    orig_run = command_subclass.run

    def modified_run(self):
        build_component_package()
        orig_run(self)

    command_subclass.run = modified_run
    return command_subclass

@with_build
class BuildPackageAndInstall(install):
    pass

@with_build
class BuildPackageAndDevelop(develop):
    pass

setup(
    name='polymer_bricks',
    version='0.0',
    description='Polymer components for Bricks',
    classifiers=[
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
    ],
    author='Philipp Volguine',
    author_email='phil.volguine@gmail.com',
    packages=['polymer_bricks'],
    include_package_data=True,
    cmdclass={
        'install': BuildPackageAndInstall,
        'develop': BuildPackageAndDevelop
    },
    install_requires=requires,
    dependency_links=links,
    setup_requires=setup_requires,
)
