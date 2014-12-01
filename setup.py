from setuptools import setup
import polymer_bricks
import os
import logging
logging.basicConfig(level=logging.INFO)

here = os.path.abspath(os.path.dirname(__file__))
sources_dir = os.path.join(here, 'tools/bin/components')
package = os.path.join(here, 'polymer_components')
#polymer_tools_repo = "http://github.com/Polymer/tools.git"
polymer_tools_repo = "https://github.com/Zer0-/tools.git"
extra_sources = (
    "https://github.com/chjj/marked",
)

def env_check():
    commands = ('git', 'npm', 'node')
    for c in commands:
        if os.system(c + ' --version') != 0:
            raise Exception("Need " + c)

def git_clone(repo, target_dir):
    os.system("cd {}; git clone {}".format(target_dir, repo))

env_check()
git_clone(polymer_tools_repo, here)
#run pull-all.sh
_tools = os.path.join(here, 'tools/bin')
os.system('cd {}; sh {}/pull-all.sh'.format(_tools, _tools))
for extra in extra_sources:
    git_clone(extra, sources_dir)

if not os.path.isdir(package):
    os.mkdir(package)
polymer_bricks.build_component_directory(sources_dir, package)

requires = [
    'lxml',
    'bricks',
]

links = [
    'git+https://github.com/Zer0-/bricks.git#egg=bricks',
]

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
    packages=['polymer_components'],
    include_package_data=True,
    install_requires=requires,
    dependency_links=links,
)
