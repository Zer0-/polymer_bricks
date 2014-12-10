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
#extra_sources = (
#    "https://github.com/chjj/marked",
#)
extra_sources = ()

requires = [
    'bricks',
]

setup_requires = [
    'lxml',
    'html5lib'
]

links = [
    'git+https://github.com/Zer0-/bricks.git#egg=bricks',
]

def env_check():
    commands = ('git', 'npm', 'node')
    for c in commands:
        if os.system(c + ' --version') != 0:
            raise Exception("Need " + c)
    github_key = os.system("ssh -vT git@github.com")
    if github_key != 256:
        raise Exception("Please add your machine's public key to your gihub account")

def git_clone(repo, target_dir):
    os.system("cd {}; git clone {}".format(target_dir, repo))

env_check()

def run_webcomponents_gulp():
    import shutil
    wc_dir = os.path.join(here, 'tools/bin/components/webcomponentsjs')
    os.system('cd {}; npm install'.format(wc_dir))
    os.system('cd {}; npm install gulp'.format(wc_dir))
    os.system('cd {}; ./node_modules/gulp/bin/gulp.js build'.format(wc_dir))
    shutil.copyfile(os.path.join(wc_dir, 'dist/webcomponents.js'),
                    os.path.join(wc_dir, 'webcomponents.js'))

def build_component_package():
    git_clone(polymer_tools_repo, here)
    #run pull-all.sh
    _tools = os.path.join(here, 'tools/bin')
    os.system('cd {}; bash {}/pull-all.sh'.format(_tools, _tools))
    for extra in extra_sources:
        git_clone(extra, sources_dir)

    run_webcomponents_gulp()
    if not os.path.isdir(package):
        os.mkdir(package)

def with_build(command_subclass):
    orig_run = command_subclass.run

    def modified_run(self):
        import package_builder
        #build_component_package()
        package_builder.build_component_directory(sources_dir, package)
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
